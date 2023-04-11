# ms_to_do.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import requests
import msal
import atexit
import gi
import os
import csv
import traceback

gi.require_version('Secret', '1')
from gi.repository import Secret, GLib

from remembrance import info

GRAPH = 'https://graph.microsoft.com/v1.0'

SCOPES = [
    'Tasks.ReadWrite',
    'User.Read'
]

logger = logging.getLogger(info.service_executable)

class MSToDo():
    def __init__(self, reminders):
        self.app = None
        self.tokens = {}
        self.users = {}
        self.reminders = reminders
        self.cache = msal.SerializableTokenCache()
        self.schema = Secret.Schema.new(
            info.app_id,
            Secret.SchemaFlags.NONE,
            { 'name': Secret.SchemaAttributeType.STRING }
        )

        atexit.register(self.store)
        self.read_cache()

        try:
            self.get_tokens()
        except:
            pass

    def do_request(self, method, url, user_id, data = None, retry = True):
        try:
            if data is None:
                results = requests.request(method, f'{GRAPH}/{url}', headers={'Authorization': f'Bearer {self.tokens[user_id]}'})
            else:
                results = requests.request(method, f'{GRAPH}/{url}', data=json.dumps(data), headers={'Authorization': f'Bearer {self.tokens[user_id]}', 'Content-Type': 'application/json'})
            results.raise_for_status()
            return results
        except requests.HTTPError as error:
            if error.response.status_code == 401 and retry:
                self.get_tokens()
                results = self.do_request(method, url, user_id, data, False)
                return results
            else:
                traceback.print_exception(error)
                raise error

    def get_tokens(self):
        try:
            if self.app is None:
                self.app = msal.PublicClientApplication(info.client_id, token_cache=self.cache)
            self.tokens = {}
            self.users = {}
            accounts = self.app.get_accounts()

            for account in accounts:
                try:
                    token = self.app.acquire_token_silent(SCOPES, account)['access_token']
                    result = requests.request('GET', f'{GRAPH}/me', headers={'Authorization': f'Bearer {token}'})
                    result.raise_for_status()
                    result = result.json()
                    user_id = result['id']
                    email = result['userPrincipalName']
                    local_id = account['local_account_id']

                    self.tokens[user_id] = token
                    self.users[user_id] = {
                        'email': email,
                        'local-id': local_id
                    }
                except requests.ConnectionError as error:
                    raise error
                except Exception as error:
                    traceback.print_exception(error)

            self.store()

        except requests.ConnectionError as error:
            self.users = json.loads(
                Secret.password_lookup_sync(
                    self.schema,
                    { 'name': 'microsoft-users' },
                    None
                )
            )
            raise error
        except Exception as error:
            traceback.print_exception(error)
            self.logout_all()

    def store(self):
        if self.app is not None and len(self.users.keys()) > 0:
            Secret.password_store_sync(
                self.schema,
                { 'name': 'microsoft-cache' },
                None,
                'cache',
                self.cache.serialize(),
                None
            )
            Secret.password_store_sync(
                self.schema,
                { 'name': 'microsoft-users' },
                None,
                'users',
                json.dumps(self.users),
                None
            )

    def read_cache(self):
        try:
            self.cache.deserialize(
                Secret.password_lookup_sync(
                    self.schema,
                    { 'name': 'microsoft-cache' },
                    None
                )
            )
        except:
            self.logout_all()

    def login(self):
        try:
            if self.app is None:
                self.app = msal.PublicClientApplication(info.client_id, token_cache=self.cache)
            response = self.app.acquire_token_interactive(scopes=SCOPES, timeout=300)
            token = response['access_token']
            local_id = response['id_token_claims']['oid']
            result = requests.request('GET', f'{GRAPH}/me', headers={'Authorization': f'Bearer {token}'})
            result.raise_for_status()
            result = result.json()
            user_id = result['id']
            email = result['userPrincipalName']

            self.tokens[user_id] = token
            self.users[user_id] = {
                'email': email,
                'local-id': local_id
            }
            self.store()
            return result['id']
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def logout_all(self):
        try:
            try:
                if self.app is None:
                    self.app = msal.PublicClientApplication(info.client_id, token_cache=self.cache)
                accounts = self.app.get_accounts()
                for account in accounts:
                    self.app.remove_account(account)
            except:
                pass
            self.tokens = {}
            self.users = {}
            Secret.password_clear_sync(
                self.schema,
                { 'name': 'microsoft-cache' },
                None
            )
            Secret.password_clear_sync(
                self.schema,
                { 'name': 'microsoft-users' },
                None
            )

        except Exception as error:
            traceback.print_exception(error)
            raise error

    def logout(self, user_id):
        try:
            try:
                if self.app is None:
                    self.app = msal.PublicClientApplication(info.client_id, token_cache=self.cache)
                accounts = self.app.get_accounts()
                for account in accounts:
                    if account['local_account_id'] == self.users[user_id]['local-id']:
                        self.app.remove_account(account)
            except:
                pass
            if user_id in self.tokens:
                self.tokens.pop(user_id)
            if user_id in self.users:
                self.users.pop(user_id)
            if self.users == {}:
                Secret.password_clear_sync(
                    self.schema,
                    { 'name': 'microsoft-cache' },
                    None
                )
                Secret.password_clear_sync(
                    self.schema,
                    { 'name': 'microsoft-users' },
                    None
                )
            else:
                self.store()

        except Exception as error:
            traceback.print_exception(error)
            raise error

    def create_task(self, user_id, task_list, task):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                results = self.do_request('POST', f'me/todo/lists/{task_list}/tasks', user_id, data=task).json()
                return results['id']
        except requests.ConnectionError as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def update_task(self, user_id, task_list, task_id, task):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                results = self.do_request('PATCH', f'me/todo/lists/{task_list}/tasks/{task_id}', user_id, data=task).json()
                return results['id']
        except requests.ConnectionError as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def remove_task(self, user_id, task_list, task_id):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                self.do_request('DELETE', f'me/todo/lists/{task_list}/tasks/{task_id}', user_id)
        except requests.ConnectionError as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def create_list(self, user_id, list_name, list_id):
        content = {'displayName': list_name}
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                results = self.do_request('POST', 'me/todo/lists', user_id, content).json()
                return results['id']
        except requests.ConnectionError as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def update_list(self, user_id, ms_id, list_name, list_id):
        content = {'displayName': list_name}
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                self.do_request('PATCH', f'me/todo/lists/{ms_id}', user_id, content)
        except requests.ConnectionError as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def delete_list(self, user_id, ms_id, list_id):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                self.do_request('DELETE', f'me/todo/lists/{ms_id}', user_id)
        except requests.ConnectionError as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            traceback.print_exception(error)
            raise error

    def get_lists(self):
        task_lists = {}

        if self.users.keys() != self.tokens.keys():
            self.get_tokens()

        for user_id in self.tokens.keys():
            try:
                lists = self.do_request('GET', 'me/todo/lists', user_id).json()['value']

                task_lists[user_id] = []

                for task_list in lists:
                    list_id = task_list['id']
                    list_name = task_list['displayName']
                    is_default = task_list['wellknownListName'] == 'defaultList'

                    tasks = self.do_request('GET', f'me/todo/lists/{list_id}/tasks', user_id).json()['value']

                    task_lists[user_id].append({
                        'id': list_id,
                        'default': is_default,
                        'name': list_name,
                        'tasks': tasks
                    })
            except Exception as error:
                traceback.print_exception(error)
                self.tokens.pop(user_id)
                raise error

        return task_lists