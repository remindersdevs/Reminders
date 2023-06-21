# ms_to_do.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import datetime

from gi.repository import GLib

from retainer import info
from retainer.service.reminder import Reminder
from msal import PublicClientApplication, SerializableTokenCache
from requests import request, HTTPError, ConnectionError, Timeout
from logging import getLogger
from atexit import register as atexit_register
from json import dumps, loads
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from threading import Thread
from gettext import gettext as _

GRAPH = 'https://graph.microsoft.com/v1.0'

SCOPES = [
    'Tasks.ReadWrite',
    'User.Read'
]

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

logger = getLogger(info.service_executable)

class Redirect(BaseHTTPRequestHandler):
    def __init__(self, callback, error_callback, *args):
        self.callback = callback
        self.error_callback = error_callback
        super().__init__(*args)

    def do_GET(self):
        results = parse_qs(self.path[2:])
        for key, value in results.items():
            if isinstance(value, list) and len(value) == 1:
                results[key] = value[0]
        if 'error' not in results:
            self.callback(results)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(_('Authentication complete. You can close this window now.'), 'UTF-8'))
        else:
            self.send_response(301)
            redirect = self.error_callback()
            self.send_header('Location', redirect)
            self.end_headers()

class MSToDo():
    def __init__(self, reminders, credentials):
        self.app = None
        self.flow = None
        self.tokens = {}
        self.users = {}
        self.reminders = reminders
        self.credentials = credentials
        self.cache = SerializableTokenCache()
        self.flows = {}

        atexit_register(self.store)
        self.read_cache()

        try:
            self.get_tokens()
        except:
            pass

        server = HTTPServer(('localhost', 0), lambda *args: Redirect(self.login, self.get_login_url, *args))
        self.port = server.server_port
        thread = Thread(target=self.start_server, args=(server,), daemon=True)
        thread.start()

    def start_server(self, server):
        server.serve_forever()

    def do_request(self, method, url, user_id, data = None, retry = True):
        try:
            if data is None:
                results = request(method, f'{GRAPH}/{url}', headers={'Authorization': f'Bearer {self.tokens[user_id]}'}, timeout=5)
            else:
                results = request(method, f'{GRAPH}/{url}', data=dumps(data), headers={'Authorization': f'Bearer {self.tokens[user_id]}', 'Content-Type': 'application/json'}, timeout=5)
            results.raise_for_status()
            return results
        except HTTPError as error:
            if error.response.status_code == 401 and retry:
                self.get_tokens()
                results = self.do_request(method, url, user_id, data, False)
                return results
            elif error.response.status_code == 503:
                if retry:
                    results = self.do_request(method, url, user_id, data, False)
                    return results
                else:
                    raise error
            else:
                logger.exception(error)
                raise error

    def get_tokens(self):
        try:
            if self.app is None:
                self.app = PublicClientApplication(info.client_id, token_cache=self.cache)
            self.tokens = {}
            self.users = {}
            accounts = self.app.get_accounts()

            for account in accounts:
                try:
                    token = self.app.acquire_token_silent(SCOPES, account)['access_token']
                    result = request('GET', f'{GRAPH}/me', headers={'Authorization': f'Bearer {token}'}, timeout=5)
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
                except HTTPError as error:
                    if error.response.status_code == 503:
                        raise error
                    else:
                        logger.exception(error)
                except (ConnectionError, Timeout) as error:
                    raise error
                except Exception as error:
                    logger.exception(error)

            self.store()

        except (ConnectionError, HTTPError, Timeout) as error:
            try:
                self.users = loads(
                    self.credentials.lookup_password('microsoft-users')
                )
                for i, value in self.users.items():
                    for key in ('email', 'local-id'):
                        if key not in value.keys():
                            self.users.pop(i)
                            break
            except:
                self.users = {}
            raise error
        except Exception as error:
            logger.exception(error)
            self.logout_all()

    def store(self):
        if self.app is not None and len(self.users.keys()) > 0:
            self.credentials.add_password('microsoft-cache', self.cache.serialize())
            self.credentials.add_password('microsoft-users', dumps(self.users))

    def read_cache(self):
        try:
            self.cache.deserialize(
                self.credentials.lookup_password('microsoft-cache')
            )
        except:
            self.logout_all()

    def get_login_url(self):
        if self.app is None:
            self.app = PublicClientApplication(info.client_id, token_cache=self.cache)
        self.flow = self.app.initiate_auth_code_flow(scopes=SCOPES, redirect_uri=f'http://localhost:{self.port}')
        return self.flow['auth_uri']

    def login(self, results):
        try:
            result = self.app.acquire_token_by_auth_code_flow(self.flow, results)
            token = result['access_token']
            local_id = result['id_token_claims']['oid']
            result = request('GET', f'{GRAPH}/me', headers={'Authorization': f'Bearer {token}'}, timeout=5)
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
            self.reminders.emit_login(user_id)
        except Exception as error:
            logger.exception(error)
            raise error

    def logout_all(self):
        try:
            try:
                if self.app is None:
                    self.app = PublicClientApplication(info.client_id, token_cache=self.cache)
                accounts = self.app.get_accounts()
                for account in accounts:
                    self.app.remove_account(account)
            except:
                pass
            self.tokens = {}
            self.users = {}
            try:
                self.credentials.remove_password('microsoft-cache')
            except:
                pass
            try:
                self.credentials.remove_password('microsoft-users')
            except:
                pass

        except Exception as error:
            logger.exception(error)
            raise error

    def logout(self, user_id):
        try:
            try:
                if self.app is None:
                    self.app = PublicClientApplication(info.client_id, token_cache=self.cache)
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
                try:
                    self.credentials.remove_password('microsoft-cache')
                except:
                    pass
                try:
                    self.credentials.remove_password('microsoft-users')
                except:
                    pass
            else:
                self.store()

        except Exception as error:
            logger.exception(error)
            raise error

    def create_task(self, user_id, task_list, task):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                results = self.do_request('POST', f'me/todo/lists/{task_list}/tasks', user_id, data=task).json()
                return results['id']
        except HTTPError as error:
            if error.response.status_code == 503:
                if user_id in self.tokens.keys():
                    self.tokens.pop(user_id)
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def update_task(self, user_id, task_list, task_id, task):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                results = self.do_request('PATCH', f'me/todo/lists/{task_list}/tasks/{task_id}', user_id, data=task).json()
                return results
        except HTTPError as error:
            if error.response.status_code == 503:
                if user_id in self.tokens.keys():
                    self.tokens.pop(user_id)
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def remove_task(self, user_id, task_list, task_id):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                self.do_request('DELETE', f'me/todo/lists/{task_list}/tasks/{task_id}', user_id)
        except HTTPError as error:
            if error.response.status_code == 503:
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def create_list(self, user_id, list_name):
        content = {'displayName': list_name}
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                results = self.do_request('POST', 'me/todo/lists', user_id, content).json()
                return results['id']
        except HTTPError as error:
            if error.response.status_code == 503:
                if user_id in self.tokens.keys():
                    self.tokens.pop(user_id)
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def update_list(self, user_id, ms_id, list_name):
        content = {'displayName': list_name}
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                self.do_request('PATCH', f'me/todo/lists/{ms_id}', user_id, content)
        except HTTPError as error:
            if error.response.status_code == 503:
                if user_id in self.tokens.keys():
                    self.tokens.pop(user_id)
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def delete_list(self, user_id, ms_id):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                self.do_request('DELETE', f'me/todo/lists/{ms_id}', user_id)
        except HTTPError as error:
            if error.response.status_code == 503:
                if user_id in self.tokens.keys():
                    self.tokens.pop(user_id)
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def get_lists(self, removed_list_ids, old_lists, synced_ids):
        task_lists = {}
        not_synced = []

        try:
            if self.users.keys() != self.tokens.keys():
                self.get_tokens()
        except:
            pass

        for user_id in self.users.keys():
            if user_id not in self.tokens.keys():
                not_synced.append(user_id)
                continue

            try:
                email = self.do_request('GET', 'me', user_id).json()['userPrincipalName']
                if email != self.users[user_id]['email']:
                    self.reminders.do_emit('UsernameUpdated', GLib.Variant('(ss)', (user_id, email)))

                lists = self.do_request('GET', 'me/todo/lists', user_id).json()['value']

                task_lists[user_id] = []

                for task_list in lists:
                    list_uid = task_list['id']

                    if list_uid in removed_list_ids:
                        continue

                    list_id = None
                    if task_list['wellknownListName'] == 'defaultList':
                        list_id = user_id
                    else:
                        try:
                            for task_list_id, value in old_lists.items():
                                if value['uid'] == list_uid and value['user-id'] == user_id:
                                    list_id = task_list_id
                        except:
                            pass

                    if list_id is None:
                        list_id = self.reminders._do_generate_id()

                    if user_id not in synced_ids and list_id not in synced_ids:
                        tasks = []
                    else:
                        tasks = self.do_request('GET', f'me/todo/lists/{list_uid}/tasks', user_id).json()['value']

                    task_lists[user_id].append({
                        'id': list_id,
                        'uid': list_uid,
                        'name': task_list['displayName'],
                        'tasks': tasks
                    })
            except HTTPError as error:
                if error.response.status_code == 503:
                    not_synced.append(user_id)
                    self.tokens.pop(user_id)
                else:
                    logger.exception(error)
                    not_synced.append(user_id)
            except (ConnectionError, Timeout):
                not_synced.append(user_id)
                self.tokens.pop(user_id)
            except Exception as error:
                logger.exception(error)
                not_synced.append(user_id)

        return task_lists, not_synced

    def get_tasks(self, list_id, user_id):
        try:
            if user_id not in self.tokens.keys():
                self.get_tokens()

            if user_id in self.tokens.keys():
                tasks = self.do_request('GET', f'me/todo/lists/{list_id}/tasks', user_id).json()['value']

            return tasks
        except HTTPError as error:
            if error.response.status_code == 503:
                if user_id in self.tokens.keys():
                    self.tokens.pop(user_id)
                raise error
            else:
                logger.exception(error)
                raise error
        except (ConnectionError, Timeout) as error:
            if user_id in self.tokens.keys():
                self.tokens.pop(user_id)
            raise error
        except Exception as error:
            logger.exception(error)
            raise error

    def rfc_to_timestamp(self, rfc):
        return GLib.DateTime.new_from_iso8601(rfc, GLib.TimeZone.new_utc()).to_unix()

    def timestamp_to_rfc(self, timestamp):
        return GLib.DateTime.new_from_unix_utc(timestamp).format_iso8601()

    def reminder_to_task(self, reminder, completed = None, completed_date = None):
        reminder_json = {}
        reminder_json['title'] = reminder['title']
        reminder_json['body'] = {}
        reminder_json['body']['content'] = reminder['description']
        reminder_json['body']['contentType'] = 'text'

        reminder_json['importance'] = 'high' if reminder['important'] else 'normal'

        if completed is not None:
            reminder_json['status'] = 'completed' if completed else 'notStarted'

        if completed_date is not None:
            if completed_date != 0:
                reminder_json['completedDateTime'] = {}
                reminder_json['completedDateTime']['dateTime'] = self.reminders._timestamp_to_rfc(completed_date)
                reminder_json['completedDateTime']['timeZone'] = 'UTC'
            else:
                reminder_json['completedDateTime'] = None

        if reminder['due-date'] != 0:
            reminder_json['dueDateTime'] = {}
            reminder_json['dueDateTime']['dateTime'] = self.reminders._timestamp_to_rfc(reminder['due-date'])
            reminder_json['dueDateTime']['timeZone'] = 'UTC'
        else:
            reminder_json['dueDateTime'] = None

        reminder_json['createdDateTime'] = self.reminders._timestamp_to_rfc(reminder['created-timestamp'])
        reminder_json['lastModifiedDateTime'] = self.reminders._timestamp_to_rfc(reminder['updated-timestamp'])

        if reminder['timestamp'] != 0:
            reminder_json['isReminderOn'] = True
            reminder_json['reminderDateTime'] = {}
            reminder_json['reminderDateTime']['dateTime'] = self.reminders._timestamp_to_rfc(reminder['timestamp'])
            reminder_json['reminderDateTime']['timeZone'] = 'UTC'
        else:
            reminder_json['isReminderOn'] = False
            reminder_json['reminderDateTime'] = None

        if reminder['repeat-type'] != 0:
            reminder_json['recurrence'] = {}
            reminder_json['recurrence']['pattern'] = {}
            if reminder['repeat-type'] == info.RepeatType.DAY:
                reminder_json['recurrence']['pattern']['type'] = 'daily'
            elif reminder['repeat-type'] == info.RepeatType.WEEK:
                reminder_json['recurrence']['pattern']['type'] = 'weekly'
            elif reminder['repeat-type'] == info.RepeatType.MONTH:
                reminder_json['recurrence']['pattern']['type'] = 'absoluteMonthly'
            elif reminder['repeat-type'] == info.RepeatType.YEAR:
                reminder_json['recurrence']['pattern']['type'] = 'absoluteYearly'

            reminder_json['recurrence']['pattern']['interval'] = reminder['repeat-frequency']

            reminder_json['recurrence']['pattern']['daysOfWeek'] = []
            if reminder['repeat-days'] == 0:
                if reminder['timestamp'] != 0:
                    reminder_json['recurrence']['pattern']['daysOfWeek'].append(DAYS[datetime.datetime.fromtimestamp(reminder['timestamp'], tz=datetime.timezone.utc).date().weekday()])
                else:
                    reminder_json['recurrence']['pattern']['daysOfWeek'].append(DAYS[datetime.datetime.fromtimestamp(reminder['due-date'], tz=datetime.timezone.utc).date().weekday()])
            else:
                repeat_days_flag = info.RepeatDays(reminder['repeat-days'])
                for num, flag in (
                    (0, info.RepeatDays.MON),
                    (1, info.RepeatDays.TUE),
                    (2, info.RepeatDays.WED),
                    (3, info.RepeatDays.THU),
                    (4, info.RepeatDays.FRI),
                    (5, info.RepeatDays.SAT),
                    (6, info.RepeatDays.SUN)
                ):
                    if flag in repeat_days_flag:
                        reminder_json['recurrence']['pattern']['daysOfWeek'].append(DAYS[num])
            reminder_json['recurrence']['pattern']['firstDayOfWeek'] = 'sunday' if self.reminders.app.settings.get_boolean('week-starts-sunday') else 'monday'
        else:
            reminder_json['recurrence'] = None

        return reminder_json

    def task_to_reminder(self, task, list_id, reminder = None, timestamp = None):
        if reminder is None:
            reminder = Reminder()
        if timestamp is None:
            timestamp = self.reminders._rfc_to_timestamp(task['reminderDateTime']['dateTime']) if 'reminderDateTime' in task else 0
        reminder['uid'] = task['id']
        reminder['title'] = task['title'].strip()
        reminder['description'] = task['body']['content'].strip() if task['body']['contentType'] == 'text' else ''
        reminder['completed'] = 'status' in task and task['status'] == 'completed'
        reminder['important'] = task['importance'] == 'high'
        reminder['timestamp'] = timestamp
        if timestamp == 0:
            reminder['due-date'] = self.reminders._rfc_to_timestamp(task['dueDateTime']['dateTime']) if 'dueDateTime' in task else 0
        else:
            notif_date = datetime.date.fromtimestamp(reminder['timestamp'])
            reminder['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())

        if reminder['created-timestamp'] == 0:
            reminder['created-timestamp'] = self.reminders._rfc_to_timestamp(task['createdDateTime'])
        reminder['updated-timestamp'] = self.reminders._rfc_to_timestamp(task['lastModifiedDateTime'])
        reminder['completed-timestamp'] = 0
        reminder['completed-date'] = self.reminders._rfc_to_timestamp(task['completedDateTime']['dateTime']) if 'completedDateTime' in task else 0

        reminder['list-id'] = list_id

        if 'recurrence' in task:
            if len(task['recurrence'].keys()) > 0:
                reminder['repeat-until'] = 0
                reminder['repeat-times'] = -1
                if task['recurrence']['pattern']['type'] == 'daily':
                    reminder['repeat-type'] = int(info.RepeatType.DAY)
                elif task['recurrence']['pattern']['type'] == 'weekly':
                    reminder['repeat-type'] = int(info.RepeatType.WEEK)
                elif task['recurrence']['pattern']['type'] == 'absoluteMonthly':
                    reminder['repeat-type'] = int(info.RepeatType.MONTH)
                elif task['recurrence']['pattern']['type'] == 'absoluteYearly':
                    reminder['repeat-type'] = int(info.RepeatType.YEAR)

                reminder['repeat-frequency'] = task['recurrence']['pattern']['interval']

                if 'daysOfWeek' in task['recurrence']['pattern']:
                    reminder['repeat-days'] = 0
                    flags = list(info.RepeatDays.__members__.values())
                    for day in task['recurrence']['pattern']['daysOfWeek']:
                        index = DAYS.index(day)
                        reminder['repeat-days'] += int(flags[index])

        return reminder
