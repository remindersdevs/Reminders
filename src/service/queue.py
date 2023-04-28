# queue.py
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

import os
import json
import requests
import logging

from copy import deepcopy

from remembrance import info
QUEUE_FILE = f'{info.data_dir}/queue.json'

logger = logging.getLogger(info.service_executable)

class Queue():
    def __init__(self, reminders):
        self.get_queue()
        self.reminders = reminders

    def reset(self):
        self.queue = {
            'reminders': {
                'create': [],
                'update': {},
                'delete': [],
                'complete': []
            },
            'lists': {
                'create': [],
                'update': [],
                'delete': []
            }
        }

    def get_queue(self):
        try:
            if os.path.isfile(QUEUE_FILE):
                with open(QUEUE_FILE, 'r') as jsonfile:
                    self.queue = json.load(jsonfile)
            else:
                self.reset()
        except:
            self.reset()

    def write(self):
        with open(QUEUE_FILE, 'w') as jsonfile:
            json.dump(self.queue, jsonfile)

    def get_updated_reminder_ids(self):
        try:
            retval = self.queue['reminders']['create'] + self.queue['reminders']['complete'] + list(self.queue['reminders']['update'].keys())
        except:
            self.queue['reminders']['create'] = []
            self.queue['reminders']['complete'] = []
            self.queue['reminders']['update'] = {}
            retval = []
        return retval

    def get_removed_reminder_ids(self):
        try:
            retval = []
            for value in self.queue['reminders']['delete']:
                retval.append(value[0])
            for value in self.queue['reminders']['update'].values():
                retval.append(value[0])
        except:
            self.queue['reminders']['delete'] = []
            retval = []
        return retval

    def get_updated_list_ids(self):
        try:
            retval = self.queue['lists']['create'] + self.queue['lists']['update']
        except:
            self.queue['lists']['create'] = []
            self.queue['lists']['update'] = []
            retval = []
        return retval

    def get_removed_list_ids(self):
        try:
            retval = []
            for value in self.queue['lists']['delete']:
                retval.append(value[0])
        except:
            self.queue['lists']['delete'] = []
            retval = []
        return retval

    def create_reminder(self, reminder_id, retry = True):
        try:
            if reminder_id not in self.queue['reminders']['create']:
                self.queue['reminders']['create'].append(reminder_id)
                self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.create_reminder(reminder_id, False)
            else:
                raise error

    def update_reminder(self, reminder_id, old_task_id, old_user_id, old_list_id, updating, retry = True):
        try:
            if reminder_id not in self.queue['reminders']['create']:
                if reminder_id not in self.queue['reminders']['update']:
                    self.queue['reminders']['update'][reminder_id] = [old_task_id, old_user_id, old_list_id, updating]
                self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.update_reminder(reminder_id, old_task_id, old_user_id, old_list_id, updating, False)
            else:
                raise error

    def update_completed(self, reminder_id, retry = True):
        try:
            if reminder_id not in self.queue['reminders']['complete']:
                self.queue['reminders']['complete'].append(reminder_id)
                self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.update_completed(reminder_id, False)
            else:
                raise error

    def remove_reminder(self, reminder_id, task_id, user_id, task_list, retry = True):
        try:
            if reminder_id in self.queue['reminders']['update']:
                self.queue['reminders']['update'].pop(reminder_id)

            value = [task_id, user_id, task_list]

            if reminder_id not in self.queue['reminders']['create'] and value not in self.queue['reminders']['delete']:
                self.queue['reminders']['delete'].append(value)
            elif reminder_id in self.queue['reminders']['create']:
                self.queue['reminders']['create'].pop(reminder_id)
            self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.remove_reminder(reminder_id, task_id, user_id, task_list, False)
            else:
                raise error

    def add_list(self, list_id, retry = True):
        try:
            if list_id not in self.queue['lists']['create']:
                self.queue['lists']['create'].append(list_id)
                self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.add_list(list_id, False)
            else:
                raise error

    def update_list(self, list_id, retry = True):
        try:
            if list_id not in self.queue['lists']['create'] and list_id not in self.queue['lists']['update']:
                self.queue['lists']['update'].append(list_id)
                self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.update_list(list_id, False)
            else:
                raise error

    def remove_list(self, list_id, uid, user_id, retry = True):
        try:
            if list_id in self.queue['lists']['update']:
                self.queue['lists']['update'].pop(list_id)

            value = [uid, user_id]

            if list_id not in self.queue['lists']['create'] and value not in self.queue['lists']['delete']:
                self.queue['lists']['delete'].append(value)
            elif list_id in self.queue['lists']['create']:
                self.queue['lists']['create'].pop(list_id)
        except Exception as error:
            if retry:
                self.reset()
                self.remove_list(list_id, uid, user_id, False)
            else:
                raise error

    def load(self):
        queue = deepcopy(self.queue)
        list_ids = self.reminders.list_ids
        reminders = self.reminders.reminders
        lists = self.reminders.lists

        try:
            try:
                for list_id in queue['lists']['create']:
                    try:
                        if list_id in list_ids:
                            user_id = list_ids[list_id]['user-id']
                            if list_id in lists[user_id]:
                                list_name = lists[user_id][list_id]

                                new_uid = self.reminders._remote_create_list(user_id, list_name)

                                if new_uid is not None:
                                    list_ids[list_id]['uid'] = new_uid

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['lists']['create'].remove(list_id)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['lists']['create'] = []

            try:
                for reminder_id in queue['reminders']['create']:
                    try:
                        if reminders[reminder_id]['user-id'] == 'local':
                            location = 'local'
                        elif reminders[reminder_id]['user-id'] in self.reminders.to_do.users.keys():
                            location = 'ms-to-do'
                        elif reminders[reminder_id]['user-id'] in self.reminders.caldav.users.keys():
                            location = 'caldav'
                        else:
                            raise KeyError('Invalid user id')

                        new_task_id = self.reminders._to_remote_task(reminders[reminder_id], location, False)
                        if new_task_id is not None:
                            reminders[reminder_id]['uid'] = new_task_id

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['reminders']['create'].remove(reminder_id)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['reminders']['create'] = []

            try:
                for reminder_id in queue['reminders']['complete']:
                    try:
                        if reminders[reminder_id]['user-id'] in self.reminders.to_do.users.keys():
                            self.reminders._ms_set_completed(reminder_id, reminders[reminder_id])
                        elif reminders[reminder_id]['user-id'] in self.reminders.caldav.users.keys():
                            self.reminders._caldav_set_completed(reminder_id, reminders[reminder_id])
                        else:
                            raise KeyError('Invalid reminder id')

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['reminders']['complete'].remove(reminder_id)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['reminders']['complete'] = []

            try:
                for reminder_id, args in queue['reminders']['update'].items():
                    try:
                        if reminders[reminder_id]['user-id'] == 'local':
                            location = 'local'
                        elif reminders[reminder_id]['user-id'] in self.reminders.to_do.users.keys():
                            location = 'ms-to-do'
                        elif reminders[reminder_id]['user-id'] in self.reminders.caldav.users.keys():
                            location = 'caldav'
                        else:
                            raise KeyError('Invalid user id')

                        old_task_id = args[0]
                        old_user_id = args[1]
                        old_list_id = args[2]
                        updating = args[3]
                        new_task_id = self.reminders._to_remote_task(reminders[reminder_id], location, updating, old_user_id, old_list_id, old_task_id)
                        if new_task_id is not None:
                            reminders[reminder_id]['uid'] = new_task_id

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['reminders']['update'].pop(reminder_id)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['reminders']['update'] = {}

            try:
                for list_id in queue['lists']['update']:
                    try:
                        if list_id in list_ids:
                            uid = list_ids[list_id]['uid']
                            user_id = list_ids[list_id]['user-id']
                            if list_id in lists[user_id]:
                                list_name = lists[user_id][list_id]
                                self.reminders._remote_rename_list(user_id, uid, list_name)

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['lists']['update'].remove(list_id)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['lists']['update'] = []

            try:
                for value in queue['reminders']['delete']:
                    try:
                        task_id = value[0]
                        user_id = value[1]
                        task_list = value[2]

                        self.reminders._remote_remove_task(user_id, task_list, task_id)

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['reminders']['delete'].remove(value)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['reminders']['delete'] = []

            try:
                for value in queue['lists']['delete']:
                    try:
                        uid = value[0]
                        user_id = value[1]

                        self.reminders._remote_delete_list(user_id, uid)

                    except requests.ConnectionError as error:
                        raise error
                    except Exception as error:
                        logger.exception(error)

                    self.queue['lists']['delete'].remove(value)
            except requests.ConnectionError as error:
                raise error
            except:
                self.queue['lists']['delete'] = []
        except requests.ConnectionError as error:
            if queue != self.queue:
                self.write()
            self.reminders._save_reminders()
            self.reminders._save_list_ids()
            raise error

        if queue != self.queue:
            self.write()
        self.reminders._save_reminders()
        self.reminders._save_list_ids()
