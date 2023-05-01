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

from remembrance import info
from logging import getLogger
from queue import Queue
from copy import deepcopy
from requests import Timeout, HTTPError, ConnectionError
from threading import Thread
from json import load, dump
from os.path import isfile

logger = getLogger(info.service_executable)

QUEUE_FILE = f'{info.data_dir}/queue.json'

DEFAULT = {
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

class ReminderQueue():
    def __init__(self, reminders):
        self.get_queue()
        self.reminders = reminders

    def reset(self):
        self.queue = DEFAULT

    def get_queue(self):
        try:
            if isfile(QUEUE_FILE):
                with open(QUEUE_FILE, 'r') as jsonfile:
                    self.queue = load(jsonfile)
            else:
                self.reset()
        except:
            self.reset()

    def write(self):
        with open(QUEUE_FILE, 'w') as jsonfile:
            dump(self.queue, jsonfile)

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

    def update_reminder(self, reminder_id, old_uid, old_user_id, old_list_uid, old_list_id, updating, completed, completed_timestamp, completed_date, retry = True):
        try:
            if reminder_id not in self.queue['reminders']['create'] and reminder_id not in self.queue['reminders']['update']:
                self.queue['reminders']['update'][reminder_id] = [old_uid, old_user_id, old_list_uid, old_list_id, updating, completed, completed_timestamp, completed_date]
                self.write()
        except Exception as error:
            if retry:
                self.reset()
                self.update_reminder(reminder_id, old_uid, old_user_id, old_list_uid, old_list_id, updating, completed, completed_timestamp, completed_date, False)
            else:
                raise error

    def update_completed(self, reminder_id, retry = True):
        try:
            if reminder_id not in self.queue['reminders']['complete']:
                self.queue['reminders']['complete'].append(reminder_id)
                self.write()
            else:
                self.queue['reminders']['complete'].pop(reminder_id)
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

    def do_create_list(self, list_id):
        if list_id in self.reminders.lists:
            user_id = self.reminders.lists[list_id]['user-id']
            list_name = self.reminders.lists[list_id]['name']

            new_uid = self.reminders._remote_create_list(user_id, list_name)

            if new_uid is not None:
                self.reminders.lists[list_id]['uid'] = new_uid

    def do_update_list(self, list_id):
        if list_id in self.reminders.lists:
            uid = self.reminders.lists[list_id]['uid']
            user_id = self.reminders.lists[list_id]['user-id']
            list_name = self.reminders.lists[list_id]['name']
            self.reminders._remote_rename_list(user_id, uid, list_name)

    def do_remove_list(self, value):
        uid = value[0]
        user_id = value[1]

        self.reminders._remote_delete_list(user_id, uid)

    def do_create_reminder(self, reminder_id):
        user_id = self.reminders.lists[self.reminders.reminders[reminder_id]['list-id']]['user-id']
        if user_id == 'local':
            location = 'local'
        elif user_id in self.reminders.to_do.users.keys():
            location = 'ms-to-do'
        elif user_id in self.reminders.caldav.users.keys():
            location = 'caldav'
        else:
            raise KeyError('Invalid user id')

        new_task_id = self.reminders._to_remote_task(self.reminders.reminders[reminder_id], location, False)
        if new_task_id is not None:
            self.reminders.reminders[reminder_id]['uid'] = new_task_id

    def do_update_reminder(self, reminder_id, args):
        user_id = self.reminders.lists[self.reminders.reminders[reminder_id]['list-id']]['user-id']

        if user_id == 'local':
            location = 'local'
        elif user_id in self.reminders.to_do.users.keys():
            location = 'ms-to-do'
        elif user_id in self.reminders.caldav.users.keys():
            location = 'caldav'
        else:
            raise KeyError('Invalid user id')

        old_uid = args[0]
        old_user_id = args[1]
        old_list_uid = args[2]
        updating = args[4]
        completed = args[5]
        completed_timestamp = args[6]
        completed_date = args[7]
        new_task_id = self.reminders._to_remote_task(self.reminders.reminders[reminder_id], location, updating, old_user_id, old_list_uid, old_uid, completed, completed_timestamp)
        if new_task_id is not None:
            self.reminders.reminders[reminder_id]['uid'] = new_task_id

    def do_complete_reminder(self, reminder_id):
        user_id = self.reminders.lists[self.reminders.reminders[reminder_id]['list-id']]['user-id']

        if user_id in self.reminders.to_do.users.keys():
            self.reminders._ms_set_completed(reminder_id, self.reminders.reminders[reminder_id])
        elif user_id in self.reminders.caldav.users.keys():
            self.reminders._caldav_set_completed(reminder_id, self.reminders.reminders[reminder_id])
        else:
            raise KeyError('Invalid reminder id')

    def do_remove_reminder(self, value):
        task_id = value[0]
        user_id = value[1]
        task_list = value[2]

        self.reminders._remote_remove_task(user_id, task_list, task_id)

    def load(self):
        old_queue = deepcopy(self.queue)
        if old_queue == DEFAULT:
            return

        try:
            error = None
            try:
                threads = []
                queue = Queue()
                for list_id in old_queue['lists']['create']:
                    thread = QueueThread(queue, list_id, target = self.do_create_list, args = (list_id,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['lists']['create']:
                            self.queue['lists']['create'].remove(value)
            except:
                self.queue['lists']['create'] = []

            if error is not None:
                raise error

            try:
                threads = []
                queue = Queue()
                for reminder_id in old_queue['reminders']['create']:
                    thread = QueueThread(queue, reminder_id, target = self.do_create_reminder, args = (reminder_id,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['reminders']['create']:
                            self.queue['reminders']['create'].remove(value)
            except:
                self.queue['reminders']['create'] = []

            if error is not None:
                raise error

            try:
                threads = []
                queue = Queue()
                for reminder_id, value in old_queue['reminders']['update'].items():
                    def cb():
                        self.reminders.reminders[reminder_id]['uid'] = value[0]
                        self.reminders.reminders[reminder_id]['list-id'] = value[3]
                    thread = QueueThread(queue, reminder_id, except_cb = cb, target = self.do_update_reminder, args = (reminder_id, value))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['reminders']['update']:
                            self.queue['reminders']['update'].pop(value)
            except:
                self.queue['reminders']['update'] = {}

            if error is not None:
                raise error

            try:
                threads = []
                queue = Queue()
                for reminder_id in old_queue['reminders']['complete']:
                    thread = QueueThread(queue, reminder_id, target = self.do_complete_reminder, args = (reminder_id,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['reminders']['complete']:
                            self.queue['reminders']['complete'].remove(value)
            except:
                self.queue['reminders']['complete'] = []

            if error is not None:
                raise error

            try:
                threads = []
                queue = Queue()
                for list_id in old_queue['lists']['update']:
                    thread = QueueThread(queue, list_id, target = self.do_update_list, args = (list_id,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['lists']['update']:
                            self.queue['lists']['update'].remove(value)
            except:
                self.queue['lists']['update'] = []

            if error is not None:
                raise error

            try:
                threads = []
                queue = Queue()
                for value in old_queue['reminders']['delete']:
                    thread = QueueThread(queue, value, target = self.do_remove_reminder, args = (value,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['reminders']['delete']:
                            self.queue['reminders']['delete'].remove(value)
            except:
                self.queue['reminders']['delete'] = []

            if error is not None:
                raise error

            try:
                threads = []
                queue = Queue()
                for value in old_queue['lists']['delete']:
                    thread = QueueThread(queue, value, target = self.do_remove_list, args = (value,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                while not queue.empty():
                    value = queue.get()
                    if isinstance(value, Exception):
                        error = value
                    else:
                        if value in self.queue['lists']['delete']:
                            self.queue['lists']['delete'].remove(value)
            except:
                self.queue['lists']['delete'] = []

            if error is not None:
                raise error

        except Exception as error:
            if old_queue != self.queue:
                self.write()
            self.reminders._save_reminders()
            self.reminders._save_lists()
            raise error

        if old_queue != self.queue:
            self.write()
        self.reminders._save_reminders()
        self.reminders._save_lists()

class QueueThread(Thread):
    def __init__(self, queue, value, except_cb = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue
        self.val = value
        self.except_cb = except_cb

    def run(self):
        try:
            if self._target is not None:
                self._target(*self._args, **self._kwargs)
                self.queue.put(self.val)
        except (ConnectionError, Timeout) as error:
            self.queue.put(error)
        except HTTPError as error:
            if error.response.status_code == 503:
                self.queue.put(error)
            else:
                logger.exception(error)
                self.queue.put(self.val)
        except Exception as error:
            logger.exception(error)
            self.queue.put(self.val)
            if except_cb is not None:
                self.except_cb()
