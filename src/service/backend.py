# backend.py
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
import csv
import json
import time
import logging
import random
import string
import datetime
import gi
import traceback
import requests

gi.require_version('GSound', '1.0')
from gi.repository import GLib, Gio, GSound
from remembrance import info
from remembrance.service.ms_to_do import MSToDo
from remembrance.service.queue import Queue
from remembrance.service.countdowns import Countdowns
from gettext import gettext as _
from math import floor
from threading import Thread
from calendar import monthrange

REMINDERS_FILE = f'{info.data_dir}/reminders.csv'
MS_REMINDERS_FILE = f'{info.data_dir}/ms_reminders.csv'
TASK_LISTS_FILE = f'{info.data_dir}/task_lists.json'
TASK_LIST_IDS_FILE = f'{info.data_dir}/task_list_ids.csv'

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

FIELDNAMES = [
    'id',
    'title',
    'description',
    'due-date',
    'timestamp',
    'shown',
    'completed',
    'important',
    'repeat-type',
    'repeat-frequency',
    'repeat-days',
    'repeat-until',
    'repeat-times',
    'created-timestamp',
    'updated-timestamp',
    'list-id'
]

MS_FIELDNAMES = [
    'id',
    'title',
    'description',
    'due-date',
    'timestamp',
    'shown',
    'completed',
    'important',
    'repeat-type',
    'repeat-frequency',
    'repeat-days',
    'created-timestamp',
    'updated-timestamp',
    'list-id',
    'user-id',
    'ms-id'
]

REMINDER_DEFAULTS = {
    'title': '',
    'description': '',
    'due-date': 0,
    'timestamp': 0,
    'shown': False,
    'completed': False,
    'important': False,
    'repeat-type': 0,
    'repeat-frequency': 1,
    'repeat-days': 0,
    'repeat-until': 0,
    'repeat-times': -1,
    'created-timestamp': 0,
    'updated-timestamp': 0,
    'list-id': 'local',
    'user-id': 'local',
    'ms-id': ''
}

VERSION = info.service_version
PID = os.getpid()

logger = logging.getLogger(info.service_executable)

XML = f'''<node name="/">
<interface name="{info.service_interface}">
    <method name='CreateReminder'>
        <arg name='app-id' type='s'/>
        <arg name='args' type='a{{sv}}'/>
        <arg name='reminder-id' direction='out' type='s'/>
        <arg name='created-timestamp' direction='out' type='u'/>
    </method>
    <method name='UpdateReminder'>
        <arg name='app-id' type='s'/>
        <arg name='args' type='a{{sv}}'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
    </method>
    <method name='UpdateCompleted'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-id' type='s'/>
        <arg name='completed' type='b'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
    </method>
    <method name='RemoveReminder'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-id' type='s'/>
    </method>
    <method name='ReturnReminders'>
        <arg name='reminders' direction='out' type='aa{{sv}}'/>
    </method>
    <method name='Quit'/>
    <method name='Refresh'/>
    <method name='GetVersion'>
        <arg name='version' direction='out' type='d'/>
    </method>
    <method name='ReturnLists'>
        <arg name='lists' direction='out' type='a{{sa{{ss}}}}'/>
    </method>
    <method name='MSGetEmails'>
        <arg name='emails' direction='out' type='a{{ss}}'/>
    </method>
    <method name='MSGetSyncedLists'>
        <arg name='list-ids' direction='out' type='a{{sas}}'/>
    </method>
    <method name='MSSetSyncedLists'>
        <arg name='synced-lists' type='a{{sas}}'/>
    </method>
    <method name='MSLogin'/>
    <method name='MSLogout'>
        <arg name='user-id' type='s'/>
    </method>
    <method name='CreateList'>
        <arg name='app-id' type='s'/>
        <arg name='user-id' type='s'/>
        <arg name='list-name' type='s'/>
        <arg name='list-id' direction='out' type='s'/>
    </method>
    <method name='RenameList'>
        <arg name='app-id' type='s'/>
        <arg name='user-id' type='s'/>
        <arg name='list-id' type='s'/>
        <arg name='new-name' type='s'/>
    </method>
    <method name='RemoveList'>
        <arg name='app-id' type='s'/>
        <arg name='user-id' type='s'/>
        <arg name='list-id' type='s'/>
    </method>
    <signal name='Refreshed'>
        <arg name='updated_reminders' direction='out' type='aa{{sv}}'/>
        <arg name='removed_reminders' direction='out' type='as'/>
    </signal>
    <signal name='CompletedUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder-id' direction='out' type='s'/>
        <arg name='completed' direction='out' type='b'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
    </signal>
    <signal name='ReminderRemoved'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder-id' direction='out' type='s'/>
    </signal>
    <signal name='ReminderUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder' direction='out' type='a{{sv}}'/>
    </signal>
    <signal name='ReminderShown'>
        <arg name='reminder-id' direction='out' type='s'/>
    </signal>
    <signal name='ListUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='list-id' direction='out' type='s'/>
        <arg name='list-name' direction='out' type='s'/>
    </signal>
    <signal name='ListRemoved'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='list-id' direction='out' type='s'/>
    </signal>
    <signal name='MSSignedIn'>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='email' direction='out' type='s'/>
    </signal>
    <signal name='MSSyncedListsChanged'>
        <arg name='lists' direction='out' type='a{{sas}}'/>
    </signal>
    <signal name='MSSignedOut'>
        <arg name='user-id' direction='out' type='s'/>
    </signal>
    <signal name='MSError'>
        <arg name='error' direction='out' type='s'/>
    </signal>
</interface>
</node>'''

class Reminders():
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        if not os.path.isdir(info.data_dir):
            os.mkdir(info.data_dir)
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.app = app
        self.local = self.ms = self.list_names = self.list_ids = {}
        self._regid = None
        self.playing_sound = False
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.to_do = MSToDo(self)
        self.queue = Queue(self)
        self.local, self.ms, self.list_names, self.list_ids = self._get_reminders()
        self.sound = GSound.Context()
        self.sound.init()
        self.countdowns = Countdowns()
        self.refresh_time = int(self.app.settings.get_string('refresh-frequency').strip('m'))
        self.synced_changed = self.app.settings.connect('changed::synced-task-lists', lambda *args: self._synced_task_list_changed())
        self.app.settings.connect('changed::refresh-frequency', lambda *args: self._refresh_time_changed())
        try:
            self.queue.load()
        except:
            pass
        self._save_reminders()
        self._save_lists()
        self._save_list_ids()
        self._methods = {
            'UpdateCompleted': self.set_completed,
            'CreateReminder': self.add_reminder,
            'UpdateReminder': self.update_reminder,
            'RemoveReminder': self.remove_reminder,
            'ReturnReminders': self.return_reminders,
            'GetVersion': self.get_version,
            'MSGetEmails': self.get_emails,
            'ReturnLists': self.return_lists,
            'Refresh': self.refresh,
            'MSLogout': self.logout_todo,
            'MSGetSyncedLists': self.get_enabled_lists,
            'MSSetSyncedLists': self.set_enabled_lists,
            'CreateList': self.create_list,
            'RenameList': self.rename_list,
            'RemoveList': self.delete_list
        }
        self._register()

    def emit_error(self, error):
        logger.exception(error)
        self.do_emit('MSError', GLib.Variant('(s)', ("".join(traceback.format_exception(error)),)))

    def emit_login(self, user_id):
        email = self.to_do.users[user_id]['email']
        self.synced_ids[user_id] = ['all']
        self.set_enabled_lists(self.synced_ids, False)
        self.do_emit('MSSignedIn', GLib.Variant('(ss)', (user_id, email)))
        self.refresh(False)
        logger.info('Logged into Microsoft account')

    def start_countdowns(self):
        self.start_local_countdowns()
        self.start_ms_countdowns()

    def start_local_countdowns(self):
        for reminder_id in self.local.keys():
            self._set_countdown(reminder_id, self.local)

    def start_ms_countdowns(self):
        for reminder_id in self.ms.keys():
            self._set_countdown(reminder_id, self.ms)

        self.countdowns.add_timeout(self.refresh_time, self._refresh_cb, 'refresh')

    def do_emit(self, signal_name, parameters):
        self.connection.emit_signal(
            None,
            info.service_object,
            info.service_interface,
            signal_name,
            parameters
        )

    def _refresh_cb(self):
        self.countdowns.dict['refresh']['id'] = 0
        self.refresh()
        return False

    def _refresh_time_changed(self):
        self.refresh_time = int(self.app.settings.get_string('refresh-frequency').strip('m'))
        self.countdowns.add_timeout(self.refresh_time, self._refresh_cb, 'refresh')

    def _synced_task_list_changed(self):
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.do_emit('MSSyncedListsChanged', self.get_enabled_lists())
        self.refresh(False)

    def _rfc_to_timestamp(self, rfc):
        return GLib.DateTime.new_from_iso8601(rfc, GLib.TimeZone.new_utc()).to_unix()

    def _timestamp_to_rfc(self, timestamp):
        return GLib.DateTime.new_from_unix_utc(timestamp).format_iso8601()

    def _reminder_updated(self, app_id, reminder_id, reminder):
        variant = {
            'id': GLib.Variant('s', reminder_id),
            'title': GLib.Variant('s', reminder['title']),
            'description': GLib.Variant('s', reminder['description']),
            'timestamp': GLib.Variant('u', reminder['timestamp']),
            'due-date': GLib.Variant('u', reminder['due-date']),
            'important': GLib.Variant('b', reminder['important']),
            'repeat-type': GLib.Variant('q', reminder['repeat-type']),
            'repeat-frequency': GLib.Variant('q', reminder['repeat-frequency']),
            'repeat-days': GLib.Variant('q', reminder['repeat-days']),
            'repeat-times': GLib.Variant('n', reminder['repeat-times']),
            'repeat-until': GLib.Variant('u', reminder['repeat-until']),
            'created-timestamp': GLib.Variant('u', reminder['created-timestamp']),
            'updated-timestamp': GLib.Variant('u', reminder['updated-timestamp']),
            'list-id': GLib.Variant('s', reminder['list-id']),
            'user-id': GLib.Variant('s', reminder['user-id'])
        }

        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, variant)))

    def _sync_ms(self, old_ms, old_lists, old_list_ids, notify_past):
        try:
            lists = self.to_do.get_lists()
        except:
            return old_ms, old_lists, old_list_ids

        if lists is None:
            return {}, {}, {}

        ms_reminders = {}
        list_names = {}
        list_ids = {}

        updated_reminder_ids = self.queue.get_updated_reminder_ids()
        removed_reminder_ids = self.queue.get_removed_reminder_ids()

        updated_list_ids = self.queue.get_updated_list_ids()
        removed_list_ids = self.queue.get_removed_list_ids()

        for user_id in lists.keys():
            list_names[user_id] = {}
            for task_list in lists[user_id]:
                list_id = None

                if task_list['id'] in removed_list_ids:
                    continue

                if task_list['default']:
                    list_id = user_id
                else:
                    try:
                        for task_list_id, value in old_list_ids.items():
                            if value['ms-id'] == task_list['id'] and value['user-id'] == user_id:
                                list_id = task_list_id
                    except:
                        pass

                if list_id is None:
                    list_id = self._do_generate_id()

                list_ids[list_id] = {
                    'ms-id': task_list['id'],
                    'user-id': user_id
                }

                list_names[user_id][list_id] = task_list['name']

                if user_id not in self.synced_ids or ('all' not in self.synced_ids[user_id] and list_id not in self.synced_ids[user_id]):
                    continue

                for task in task_list['tasks']:
                    if task['id'] in removed_reminder_ids:
                        continue

                    reminder_id = None
                    for old_reminder_id, old_reminder in old_ms.items():
                        if old_reminder['ms-id'] == task['id']:
                            reminder_id = old_reminder_id
                            break

                    if reminder_id is None:
                        reminder_id = self._do_generate_id()

                    timestamp = self._rfc_to_timestamp(task['reminderDateTime']['dateTime']) if 'reminderDateTime' in task else 0
                    is_future = timestamp > floor(time.time())

                    if reminder_id in old_ms:
                        if reminder_id in updated_reminder_ids:
                            continue
                        reminder = old_ms[reminder_id].copy()
                    else:
                        reminder = REMINDER_DEFAULTS.copy()
                        reminder['shown'] = not (is_future or notify_past)

                    ms_reminders[reminder_id] = self._task_to_reminder(task, list_id, user_id, reminder, timestamp)

        for reminder_id in updated_reminder_ids:
            if reminder_id in old_ms.keys():
                ms_reminders[reminder_id] = old_ms[reminder_id].copy()

        for list_id in updated_list_ids:
            if list_id in old_list_ids.keys():
                user_id = old_list_ids[list_id]['user-id']
                if user_id in old_lists and list_id in old_lists[user_id]:
                    list_ids[list_id] = old_list_ids[list_id]
                    if user_id not in list_names:
                        list_names[user_id] = {}
                    list_names[user_id][list_id] = old_lists[user_id][list_id]

        return ms_reminders, list_names, list_ids

    def _task_to_reminder(self, task, list_id, user_id, reminder = None, timestamp = None):
        if reminder is None:
            reminder = REMINDER_DEFAULTS.copy()
        if timestamp is None:
            timestamp = self._rfc_to_timestamp(task['reminderDateTime']['dateTime']) if 'reminderDateTime' in task else 0
        reminder['ms-id'] = task['id']
        reminder['title'] = task['title'].strip()
        reminder['description'] = task['body']['content'].strip() if task['body']['contentType'] == 'text' else ''
        reminder['completed'] = True if 'status' in task and task['status'] == 'completed' else False
        reminder['important'] = task['importance'] == 'high'
        reminder['timestamp'] = timestamp
        if timestamp == 0:
            reminder['due-date'] = self._rfc_to_timestamp(task['dueDateTime']['dateTime']) if 'dueDateTime' in task else 0
        else:
            notif_date = datetime.date.fromtimestamp(reminder['timestamp'])
            reminder['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())
        reminder['list-id'] = list_id
        reminder['user-id'] = user_id
        if reminder['created-timestamp'] == 0:
            reminder['created-timestamp'] = self._rfc_to_timestamp(task['createdDateTime'])
        if reminder['updated-timestamp'] == 0:
            reminder['updated-timestamp'] = self._rfc_to_timestamp(task['lastModifiedDateTime'])

        if 'recurrence' in task:
            if len(task['recurrence'].keys()) > 0:
                reminder['repeat-until'] = 0
                reminder['repeat-times'] = -1
                if task['recurrence']['pattern']['type'] == 'daily':
                    reminder['repeat-type'] = info.RepeatType.DAY
                elif task['recurrence']['pattern']['type'] == 'weekly':
                    reminder['repeat-type'] = info.RepeatType.WEEK
                elif task['recurrence']['pattern']['type'] == 'absoluteMonthly':
                    reminder['repeat-type'] = info.RepeatType.MONTH
                elif task['recurrence']['pattern']['type'] == 'absoluteYearly':
                    reminder['repeat-type'] = info.RepeatType.YEAR

                reminder['repeat-frequency'] = task['recurrence']['pattern']['interval']

                if 'daysOfWeek' in task['recurrence']['pattern']:
                    reminder['repeat-days'] = 0
                    flags = list(info.RepeatDays.__members__.values())
                    for day in task['recurrence']['pattern']['daysOfWeek']:
                        index = DAYS.index(day)
                        reminder['repeat-days'] += flags[index]

        return reminder

    def _ms_create_reminder(self, reminder_id, reminder_dict, dictionary):
        try:
            try:
                self.queue.load()
                ms_id = self._to_ms_task(reminder_id, reminder_dict, updating=False)
            except requests.ConnectionError:
                ms_id = None
                self.queue.add_reminder(reminder_id)

            if ms_id is not None:
                reminder_dict['ms-id'] = ms_id
                dictionary[reminder_id] = reminder_dict
                self._save_reminders()
        except Exception as error:
            self.emit_error(error)

    def _ms_update_reminder(self, reminder_id, reminder_dict, old_user_id, old_list_id, old_task_id, updating, dictionary):
        try:
            try:
                self.queue.load()
                ms_id = self._to_ms_task(reminder_id, reminder_dict, old_user_id, old_list_id, old_task_id, updating)
            except requests.ConnectionError:
                ms_id = None
                self.queue.update_reminder(reminder_id, old_task_id, old_user_id, old_list_id, updating)

            if ms_id is not None:
                reminder_dict['ms-id'] = ms_id
                dictionary[reminder_id] = reminder_dict
                self._save_reminders(dictionary)
        except Exception as error:
            self.emit_error(error)

    def _ms_update_completed(self, reminder_id, reminder_dict):
        try:
            try:
                self.queue.load()
                self._ms_set_completed(reminder_id, reminder_dict)
            except requests.ConnectionError:
                self.queue.update_completed(reminder_id)
        except Exception as error:
            self.emit_error(error)

    def _ms_remove_reminder(self, reminder_id, task_id, user_id, task_list):
        try:
            try:
                self.queue.load()
                self.to_do.remove_task(user_id, task_list, task_id)
            except requests.ConnectionError as error:
                self.queue.remove_reminder(reminder_id, task_id, user_id, task_list)
        except Exception as error:
            self.emit_error(error)

    def _ms_create_list(self, user_id, list_name, list_id):
        try:
            ms_id = None
            try:
                self.queue.load()
                ms_id = self.to_do.create_list(user_id, list_name)
            except requests.ConnectionError:
                self.queue.add_list(list_id)

            self.list_ids[list_id] = {
                'ms-id': '' if ms_id is None else ms_id,
                'user-id': user_id
            }
            self._save_list_ids()
        except Exception as error:
            self.emit_error(error)

    def _ms_rename_list(self, user_id, new_name, list_id):
        try:
            try:
                self.queue.load()
                ms_id = self.list_ids[list_id]['ms-id']
                self.to_do.update_list(user_id, ms_id, new_name)
            except requests.ConnectionError:
                self.queue.update_list(list_id)
        except Exception as error:
            self.emit_error(error)

    def _ms_delete_list(self, user_id, list_id):
        try:
            ms_id = self.list_ids[list_id]['ms-id']
            try:
                self.queue.load()
                self.to_do.delete_list(user_id, ms_id)
            except requests.ConnectionError:
                self.queue.remove_list(list_id, ms_id, user_id)
            self.list_ids.pop(list_id)
            self._save_list_ids()
        except Exception as error:
            self.emit_error(error)

    def _ms_set_completed(self, reminder_id, reminder):
        reminder_json = {}
        reminder_json['status'] = 'completed' if reminder['completed'] else 'notStarted'
        list_id = reminder['list-id']
        user_id = reminder['user-id']
        list_ms_id = self.list_ids[list_id]['ms-id']
        results = self.to_do.update_task(user_id, list_ms_id, reminder['ms-id'], reminder_json)

        try:
            if reminder_json['status'] == 'completed' and results['status'] != 'completed':
                # this sucks but microsofts api is goofy and this is the only way I can get the new ms-id of the reminder that was completed
                updated_timestamp = self._rfc_to_timestamp(results['lastModifiedDateTime'])
                match_diff = None
                new_ms_id = ''
                for task in self.to_do.get_tasks(list_ms_id, user_id):
                    if task['id'] == results['id']:
                        continue
                    timestamp = self._rfc_to_timestamp(task['lastModifiedDateTime'])
                    diff = abs(updated_timestamp - timestamp)
                    if match_diff is None or diff < match_diff:
                        match_diff = diff
                        new_ms_id = task['id']

                reminder = self._task_to_reminder(results, list_id, user_id)
                new_id = self._do_generate_id()
                self.ms[reminder_id]['ms-id'] = new_ms_id
                self.ms[new_id] = reminder
                self._set_countdown(new_id, self.ms)
                self._reminder_updated(info.service_id, new_id, reminder)
                self._save_reminders(self.ms)
        except:
            pass

    def _to_ms_task(self, reminder_id, reminder, old_user_id = None, old_list_id = None, old_task_id = None, updating = None, only_completed = False):
        user_id = reminder['user-id']
        task_list = reminder['list-id']
        list_id = self.list_ids[reminder['list-id']]['ms-id'] if reminder['list-id'] in self.list_ids.keys() else None
        task_id = reminder['ms-id']
        moving = old_list_id not in (None, list_id) or old_task_id not in (None, task_id)
        if updating is None:
            updating = reminder_id in self.ms and not moving and task_id != ''

        reminder_json = {}
        new_task_id = None
        if task_list != 'local' and user_id != 'local':
            reminder_json['title'] = reminder['title']
            reminder_json['body'] = {}
            reminder_json['body']['content'] = reminder['description']
            reminder_json['body']['contentType'] = 'text'

            reminder_json['importance'] = 'high' if reminder['important'] else 'normal'

            if reminder['due-date'] != 0:
                reminder_json['dueDateTime'] = {}
                reminder_json['dueDateTime']['dateTime'] = self._timestamp_to_rfc(reminder['due-date'])
                reminder_json['dueDateTime']['timeZone'] = 'UTC'
            else:
                reminder_json['dueDateTime'] = None

            if reminder['timestamp'] != 0:
                reminder_json['isReminderOn'] = True
                reminder_json['reminderDateTime'] = {}
                reminder_json['reminderDateTime']['dateTime'] = self._timestamp_to_rfc(reminder['timestamp'])
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
                    reminder_json['recurrence']['pattern']['daysOfWeek'].append(DAYS[datetime.date.today().weekday()])
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
                reminder_json['recurrence']['pattern']['firstDayOfWeek'] = 'monday'
            else:
                reminder_json['recurrence'] = None

            if updating or only_completed:
                results = self.to_do.update_task(user_id, list_id, task_id, reminder_json)
            else:
                results = self.to_do.create_task(user_id, list_id, reminder_json)

            new_task_id = results['id']

        if moving:
            if old_user_id is None:
                old_user_id = user_id
            self.to_do.remove_task(old_user_id, old_list_id, old_task_id)

        return new_task_id

    def _register(self):
        if self._regid is not None:
            self.connection.unregister_object(self._regid)

        node_info = Gio.DBusNodeInfo.new_for_xml(XML)
        self._regid = self.connection.register_object(
            info.service_object,
            node_info.interfaces[0],
            self._on_method_call,
            None,
            None
        )

    def _on_method_call(self, connection, sender, path, interface, method, parameters, invocation):
        try:
            # These methods need special code to function properly
            if method == 'Quit':
                if self._regid is not None:
                    self.connection.unregister_object(self._regid)
                invocation.return_value(None)
                self.app.quit()
                return
            elif method == 'MSLogin':
                invocation.return_value(None)
                thread = Thread(target=self.login_todo, daemon=True)
                thread.start()
                return

            method = self._methods[method]

            if parameters is not None:
                parameters = list(parameters.unpack())
                args = []
                kwargs = {}
                for arg in parameters:
                    if isinstance(arg, dict):
                        kwargs.update(arg)
                    else:
                        args.append(arg)
                retval = method(*args, **kwargs)
            else:
                retval = method()

            invocation.return_value(retval)
        except Exception as error:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed', f'{error} - Method {method} failed to execute\n{"".join(traceback.format_exception(error))}')

    def _generate_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def _do_generate_id(self):
        new_id = self._generate_id()

        # if for some reason it isn't unique
        while new_id in self.local.keys() or new_id in self.ms.keys():
            new_id = self._generate_id()

        for user_id in self.list_names.keys():
            if new_id in self.list_names[user_id].keys():
                new_id = self._generate_id()

        return new_id

    def _remove_countdown(self, reminder_id):
        self.countdowns.remove_countdown(reminder_id)

    def _set_countdown(self, reminder_id, dictionary):
        self.countdowns.remove_countdown(reminder_id)

        reminder = dictionary[reminder_id]
        if reminder['timestamp'] == 0:
            return

        if reminder['completed'] or reminder['shown']:
            return

        def do_show_notification():
            self.show_notification(reminder_id, dictionary)
            return False

        self.countdowns.add_countdown(reminder['timestamp'], do_show_notification, reminder_id)

    def show_notification(self, reminder_id, dictionary):
        notification = Gio.Notification.new(dictionary[reminder_id]['title'])
        notification.set_body(dictionary[reminder_id]['description'])
        notification.add_button_with_target(_('Mark as completed'), 'app.reminder-completed', GLib.Variant('s', reminder_id))
        notification.set_default_action('app.notification-clicked')

        self.app.send_notification(reminder_id, notification)
        if self.app.settings.get_boolean('notification-sound') and not self.playing_sound:
            self.playing_sound = True
            if self.app.settings.get_boolean('included-notification-sound'):
                self.sound.play_full({GSound.ATTR_MEDIA_FILENAME: f'{GLib.get_system_data_dirs()[0]}/sounds/{info.app_executable}/notification.ogg'}, None, self._sound_cb)
            else:
                self.sound.play_full({GSound.ATTR_EVENT_ID: 'bell'}, None, self._sound_cb)
        self._shown(reminder_id, dictionary)
        self.countdowns.dict[reminder_id]['id'] = 0

    def _sound_cb(self, context, result):
        try:
            self.sound.play_full_finish(result)
        except Exception as error:
            logger.exception(f"{error} Couldn't play notification sound")
        self.playing_sound = False

    def _repeat(self, reminder_dict):
        delta = None
        repeat_times = reminder_dict['repeat-times']

        if repeat_times != -1:
            repeat_times -= 1

        if repeat_times == 0:
            return

        timestamp = reminder_dict['timestamp']
        repeat_until = reminder_dict['repeat-until']

        notify = timestamp != 0
        if notify:
            reminder_datetime = datetime.datetime.fromtimestamp(timestamp)
        else:
            timestamp = reminder_dict['due-date']
            reminder_datetime = datetime.datetime.fromtimestamp(timestamp).astimezone(tz=datetime.timezone.utc)

        repeat_until_date = datetime.datetime.fromtimestamp(repeat_until).astimezone(tz=datetime.timezone.utc).date()

        if repeat_until > 0 and reminder_datetime.date() > repeat_until_date:
            return

        repeat_type = reminder_dict['repeat-type']
        frequency = reminder_dict['repeat-frequency']
        repeat_days = reminder_dict['repeat-days']

        if repeat_type == info.RepeatType.MINUTE:
            delta = datetime.timedelta(minutes=frequency)
        elif repeat_type == info.RepeatType.HOUR:
            delta = datetime.timedelta(hours=frequency)
        elif repeat_type == info.RepeatType.DAY:
            delta = datetime.timedelta(days=frequency)

        if delta is not None:
            reminder_datetime += delta
            timestamp = reminder_datetime.timestamp()
            while ((timestamp < floor(time.time())) if notify else (reminder_datetime.date() < datetime.date.today())):
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                reminder_datetime += delta
                timestamp = reminder_datetime.timestamp()

        if repeat_type == info.RepeatType.WEEK:
            week_frequency = 0
            weekday = reminder_datetime.date().weekday()
            if repeat_days == 0:
                repeat_days = weekday
            repeat_days_flag = info.RepeatDays(repeat_days)
            index = 0
            days = []
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
                    days.append(num)

            if len(days) == 0:
                return

            for i, value in enumerate(days):
                if value == weekday:
                    index = i + 1
                    if index > len(days) - 1:
                        index = 0
                        week_frequency = frequency - 1
                    break
                if value > weekday:
                    index = i
                    break
                if i == len(days) - 1:
                    index = 0
                    week_frequency = frequency - 1
                    break

            reminder_datetime += datetime.timedelta(days=(((days[index] - weekday - 1) % 7 + 1) + 7 * week_frequency))
            timestamp = reminder_datetime.timestamp()
            while ((timestamp < floor(time.time())) if notify else (reminder_datetime.date() < datetime.date.today())):
                week_frequency = 0
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                weekday = reminder_datetime.date().weekday()
                index += 1
                if index > len(days) - 1:
                    index = 0
                    week_frequency = frequency - 1

                reminder_datetime += datetime.timedelta(days=(((days[index] - weekday - 1) % 7 + 1) + 7 * week_frequency))
                timestamp = reminder_datetime.timestamp()

        elif repeat_type == info.RepeatType.MONTH:
            reminder_datetime = self._month_repeat(reminder_datetime, frequency)
            timestamp = reminder_datetime.timestamp()
            while ((timestamp < floor(time.time())) if notify else (reminder_datetime.date() < datetime.date.today())):
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                reminder_datetime = self._month_repeat(reminder_datetime, frequency)
                timestamp = reminder_datetime.timestamp()

        elif repeat_type == info.RepeatType.YEAR:
            reminder_datetime = self._year_repeat(reminder_datetime, frequency)
            timestamp = reminder_datetime.timestamp()
            while ((timestamp < floor(time.time())) if notify else (reminder_datetime.date() < datetime.date.today())):
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                reminder_datetime = self._year_repeat(reminder_datetime, frequency)
                timestamp = reminder_datetime.timestamp()

        if repeat_until > 0 and reminder_datetime.date() > repeat_until_date:
            return

        timestamp = floor(reminder_datetime.timestamp()) if notify else 0
        due_date = floor(reminder_datetime.timestamp()) if not notify else 0

        return timestamp, due_date, repeat_times

    def _month_repeat(self, reminder_datetime, frequency):
        date = reminder_datetime.date()
        time = reminder_datetime.time()
        tz = reminder_datetime.tzinfo
        months = date.month + frequency - 1

        year = date.year + months // 12

        month = months % 12 + 1

        days = monthrange(year, month)[1]
        day = date.day
        if day > days:
            day = days

        return datetime.datetime.combine(datetime.date(year, month, day), time, tzinfo=tz)

    def _year_repeat(self, reminder_datetime, frequency):
        date = reminder_datetime.date()
        time = reminder_datetime.time()
        tz = reminder_datetime.tzinfo

        year = date.year + frequency

        days = monthrange(year, date.month)[1]
        day = date.day
        if day > days:
            day = days

        return datetime.datetime.combine(datetime.date(year, date.month, day), time, tzinfo=tz)

    def _shown(self, reminder_id, dictionary):
        if not dictionary[reminder_id]['shown'] > 0:
            dictionary[reminder_id]['shown'] = True
            self._save_reminders(dictionary)

    def _save_reminders(self, dictionary = None):
        if dictionary == self.local or dictionary is None:
            with open(REMINDERS_FILE, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                writer.writeheader()

                for reminder in self.local:
                    writer.writerow({
                        'id': reminder,
                        'title': self.local[reminder]['title'],
                        'description': self.local[reminder]['description'],
                        'due-date': self.local[reminder]['due-date'],
                        'timestamp': self.local[reminder]['timestamp'],
                        'shown': self.local[reminder]['shown'],
                        'completed': self.local[reminder]['completed'],
                        'important': self.local[reminder]['important'],
                        'repeat-type': self.local[reminder]['repeat-type'],
                        'repeat-frequency': self.local[reminder]['repeat-frequency'],
                        'repeat-days': self.local[reminder]['repeat-days'],
                        'repeat-times': self.local[reminder]['repeat-times'],
                        'repeat-until': self.local[reminder]['repeat-until'],
                        'created-timestamp': self.local[reminder]['created-timestamp'],
                        'updated-timestamp': self.local[reminder]['updated-timestamp'],
                        'list-id': self.local[reminder]['list-id']
                    })

        if dictionary == self.ms or dictionary is None:
            with open(MS_REMINDERS_FILE, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=MS_FIELDNAMES)
                writer.writeheader()

                for reminder in self.ms:
                    writer.writerow({
                        'id': reminder,
                        'title': self.ms[reminder]['title'],
                        'description': self.ms[reminder]['description'],
                        'due-date': self.ms[reminder]['due-date'],
                        'timestamp': self.ms[reminder]['timestamp'],
                        'shown': self.ms[reminder]['shown'],
                        'completed': self.ms[reminder]['completed'],
                        'important': self.ms[reminder]['important'],
                        'repeat-type': self.ms[reminder]['repeat-type'],
                        'repeat-frequency': self.ms[reminder]['repeat-frequency'],
                        'repeat-days': self.ms[reminder]['repeat-days'],
                        'created-timestamp': self.ms[reminder]['created-timestamp'],
                        'updated-timestamp': self.ms[reminder]['updated-timestamp'],
                        'list-id': self.ms[reminder]['list-id'],
                        'user-id': self.ms[reminder]['user-id'],
                        'ms-id': self.ms[reminder]['ms-id']
                    })

    def _save_lists(self):
        with open(TASK_LISTS_FILE, 'w', newline='') as jsonfile:
            json.dump(self.list_names, jsonfile)

    def _save_list_ids(self):
        with open(TASK_LIST_IDS_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['list-id', 'ms-id', 'user-id'])
            writer.writeheader()

            for list_id in self.list_ids.keys():
                writer.writerow({
                    'list-id': list_id,
                    'ms-id': self.list_ids[list_id]['ms-id'],
                    'user-id': self.list_ids[list_id]['user-id']
                })

    def _get_boolean(self, row, key, default = False):
        if key in row.keys():
            return row[key] == 'True'
        else:
            return default

    def _get_int(self, row, key):
        try:
            retval = int(row[key])
        except:
            retval = REMINDER_DEFAULTS[key] if key in REMINDER_DEFAULTS.keys() else 0
        return retval

    def _get_str(self, row, key):
        try:
            retval = str(row[key])
        except:
            retval = REMINDER_DEFAULTS[key] if key in REMINDER_DEFAULTS.keys() else ''
        return retval

    def _get_saved_ms_reminders(self):
        old_ms = self.ms.copy()
        if old_ms == {}:
            if os.path.isfile(MS_REMINDERS_FILE):
                with open(MS_REMINDERS_FILE, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        user_id = self._get_str(row, 'user-id')
                        list_id = self._get_str(row, 'list-id')
                        if user_id not in self.synced_ids.keys() or ('all' not in self.synced_ids[user_id] and list_id not in self.synced_ids[user_id]):
                            continue

                        timestamp = self._get_int(row, 'timestamp')
                        repeat_type = self._get_int(row, 'repeat-type')
                        repeat_times = self._get_int(row, 'repeat-times')
                        reminder_id = row['id']

                        old_shown = repeat_times == 0

                        old_ms[reminder_id] = REMINDER_DEFAULTS.copy()
                        old_ms[reminder_id]['title'] = self._get_str(row, 'title')
                        old_ms[reminder_id]['description'] = self._get_str(row, 'description')
                        old_ms[reminder_id]['due-date'] = self._get_int(row, 'due-date')
                        old_ms[reminder_id]['timestamp'] = timestamp
                        old_ms[reminder_id]['shown'] = self._get_boolean(row, 'shown', old_shown)
                        old_ms[reminder_id]['completed'] = self._get_boolean(row, 'completed')
                        old_ms[reminder_id]['important'] = self._get_boolean(row, 'important')
                        old_ms[reminder_id]['repeat-type'] = repeat_type
                        old_ms[reminder_id]['created-timestamp'] = self._get_int(row, 'created-timestamp')
                        old_ms[reminder_id]['updated-timestamp'] = self._get_int(row, 'updated-timestamp')
                        old_ms[reminder_id]['user-id'] = user_id
                        old_ms[reminder_id]['list-id'] = list_id
                        old_ms[reminder_id]['ms-id'] = self._get_str(row, 'ms-id')

                        if repeat_type != 0:
                            old_ms[reminder_id]['repeat-frequency'] = self._get_int(row, 'repeat-frequency')
                            old_ms[reminder_id]['repeat-days'] = self._get_int(row, 'repeat-days')

        return old_ms

    def _get_reminders(self, notify_past = True):
        local = {}
        ms = {}
        list_ids = {}
        ms_list_names = {}
        list_names = {}

        try:
            if os.path.isfile(TASK_LISTS_FILE):
                with open(TASK_LISTS_FILE, newline='') as jsonfile:
                    all_list_names = json.load(jsonfile)
                    ms_list_names = all_list_names.copy()
                    if 'local' in ms_list_names.keys():
                        ms_list_names.pop('local')
                    list_names['local'] = all_list_names['local'] if 'local' in all_list_names.keys() else {}
        except:
            pass

        if 'local' not in list_names.keys():
            list_names['local'] = {}
        if 'local' not in list_names['local'].keys():
            list_names['local']['local'] = _('Local Reminders')

        if os.path.isfile(REMINDERS_FILE):
            with open(REMINDERS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    list_id = self._get_str(row, 'list-id')
                    if list_id not in list_names['local'].keys():
                        continue
                    reminder_id = row['id']
                    timestamp = self._get_int(row, 'timestamp')
                    repeat_type = self._get_int(row, 'repeat-type')
                    repeat_times = self._get_int(row, 'repeat-times')

                    old_shown = repeat_times == 0

                    local[reminder_id] = REMINDER_DEFAULTS.copy()
                    local[reminder_id]['title'] = self._get_str(row, 'title')
                    local[reminder_id]['description'] = self._get_str(row, 'description')
                    local[reminder_id]['due-date'] = self._get_int(row, 'due-date')
                    local[reminder_id]['timestamp'] = timestamp
                    local[reminder_id]['shown'] = self._get_boolean(row, 'shown', old_shown)
                    local[reminder_id]['completed'] = self._get_boolean(row, 'completed')
                    local[reminder_id]['important'] = self._get_boolean(row, 'important')
                    local[reminder_id]['repeat-type'] = repeat_type
                    local[reminder_id]['created-timestamp'] = self._get_int(row, 'created-timestamp')
                    local[reminder_id]['updated-timestamp'] = self._get_int(row, 'updated-timestamp')
                    local[reminder_id]['list-id'] = list_id

                    if repeat_type != 0:
                        local[reminder_id]['repeat-frequency'] = self._get_int(row, 'repeat-frequency')
                        local[reminder_id]['repeat-days'] = self._get_int(row, 'repeat-days')
                        local[reminder_id]['repeat-until'] = self._get_int(row, 'repeat-until')
                        local[reminder_id]['repeat-times'] = repeat_times

        if os.path.isfile(TASK_LIST_IDS_FILE):
            with open(TASK_LIST_IDS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    list_ids[row['list-id']] = {
                        'ms-id': row['ms-id'],
                        'user-id': row['user-id']
                    }

        old_ms = self._get_saved_ms_reminders()
        ms, ms_list_names, list_ids = self._sync_ms(old_ms, ms_list_names, list_ids, notify_past)
        list_names.update(ms_list_names)

        return local, ms, list_names, list_ids

    # Below methods can be accessed by other apps over dbus
    def set_completed(self, app_id: str, reminder_id: str, completed: bool):
        now = floor(time.time())
        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary.keys():
                dictionary[reminder_id]['completed'] = completed
                dictionary[reminder_id]['updated-timestamp'] = now
                self._save_reminders(dictionary)

                reminder_dict = dictionary[reminder_id]

                if dictionary == self.ms:
                    GLib.idle_add(lambda *args: self._ms_update_completed(reminder_id, reminder_dict))

                if completed:
                    self.app.withdraw_notification(reminder_id)
                    self._remove_countdown(reminder_id)
                    if dictionary == self.local and reminder_dict['repeat-type'] != 0 and reminder_dict['repeat-times'] != 0:
                        try:
                            new_dict = reminder_dict.copy()
                            new_dict['timestamp'], new_dict['due-date'], new_dict['repeat-times'] = self._repeat(reminder_dict)
                            new_dict['completed'] = False
                            new_id = self._do_generate_id()
                            dictionary[new_id] = new_dict
                            self._set_countdown(new_id, dictionary)
                            self._reminder_updated(info.service_id, new_id, new_dict)
                            self._save_reminders(dictionary)
                        except:
                            pass
                else:
                    self._set_countdown(reminder_id, dictionary)

                self.do_emit('CompletedUpdated', GLib.Variant('(ssbu)', (app_id, reminder_id, completed, now)))
                break

        return GLib.Variant('(u)', (now,))

    def remove_reminder(self, app_id: str, reminder_id: str):
        self.app.withdraw_notification(reminder_id)
        self._remove_countdown(reminder_id)

        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary:
                if dictionary == self.ms:
                    task_id = self.ms[reminder_id]['ms-id']
                    user_id = self.ms[reminder_id]['user-id']
                    task_list = self.ms[reminder_id]['list-id']
                    GLib.idle_add(lambda *args: self._ms_remove_reminder(reminder_id, task_id, user_id, task_list))
                dictionary.pop(reminder_id)
                self._save_reminders(dictionary)
                break

        self.do_emit('ReminderRemoved', GLib.Variant('(ss)', (app_id, reminder_id)))

    def add_reminder(self, app_id: str, **kwargs):
        reminder_id = self._do_generate_id()

        reminder_dict = REMINDER_DEFAULTS.copy()

        for i in ('title', 'description', 'list-id', 'user-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'due-date'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        if 'repeat-type' in kwargs.keys():
            repeat_type = int(kwargs['repeat-type'])
            if reminder_dict['user-id'] == 'local' or repeat_type not in (1, 2):
                reminder_dict['repeat-type'] = repeat_type

        for i in ('repeat-frequency', 'repeat-days'):
            if reminder_dict['repeat-type'] != 0 and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        for i in ('repeat-times', 'repeat-until'):
            if reminder_dict['repeat-type'] != 0 and reminder_dict['user-id'] == 'local' and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        if 'important' in kwargs.keys():
            reminder_dict['important'] = bool(kwargs['important'])

        if reminder_dict['timestamp'] != 0:
            notif_date = datetime.date.fromtimestamp(reminder_dict['timestamp'])
            due_date = datetime.datetime.fromtimestamp(reminder_dict['due-date']).astimezone(tz=datetime.timezone.utc).date()
            if notif_date != due_date:
                # due date has to be the same day as the reminder date
                # this honestly doesn't make sense and probably should be changed in the future
                # but right now it is necessary because of how the UI of the Reminders app is set up
                reminder_dict['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())

        now = floor(time.time())
        reminder_dict['created-timestamp'] = now
        reminder_dict['updated-timestamp'] = now

        dictionary = self.local if reminder_dict['user-id'] == 'local' else self.ms

        dictionary[reminder_id] = reminder_dict
        self._set_countdown(reminder_id, dictionary)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders(dictionary)

        GLib.idle_add(lambda *args: self._ms_create_reminder(reminder_id, dictionary[reminder_id], dictionary))

        return GLib.Variant('(su)', (reminder_id, now))

    def update_reminder(self, app_id: str, **kwargs):
        reminder_id = str(kwargs['id'])

        old_dict = self.ms if reminder_id in self.ms else self.local

        reminder_dict = old_dict[reminder_id].copy()

        for i in ('title', 'description', 'list-id', 'user-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'due-date'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        if 'repeat-type' in kwargs.keys():
            repeat_type = int(kwargs['repeat-type'])
            reminder_dict['repeat-type'] = 0 if reminder_dict['user-id'] != 'local' and repeat_type in (1, 2) else repeat_type

        for i in ('repeat-frequency', 'repeat-days'):
            if reminder_dict['repeat-type'] != 0 and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])
            else:
                reminder_dict[i] = REMINDER_DEFAULTS[i]

        for i in ('repeat-times', 'repeat-until'):
            if reminder_dict['repeat-type'] != 0 and reminder_dict['user-id'] == 'local' and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])
            else:
                reminder_dict[i] = REMINDER_DEFAULTS[i]

        if 'important' in kwargs.keys():
            reminder_dict['important'] = bool(kwargs['important'])

        now = floor(time.time())
        reminder_dict['updated-timestamp'] = now

        if reminder_dict['timestamp'] > floor(time.time()):
            reminder_dict['shown'] = False

        if reminder_dict['timestamp'] != 0:
            notif_date = datetime.date.fromtimestamp(reminder_dict['timestamp'])
            due_date = datetime.datetime.fromtimestamp(reminder_dict['due-date']).astimezone(tz=datetime.timezone.utc).date()
            if notif_date != due_date:
                # due date has to be the same day as the reminder date
                # this honestly doesn't make sense and probably should be changed in the future
                # but right now it is necessary because of how the UI of the Reminders app is set up
                reminder_dict['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())

        dictionary = self.local if reminder_dict['user-id'] == 'local' else self.ms
        if reminder_dict['user-id'] == 'local':
            reminder_dict['ms-id'] = ''

        old_list_id = None
        old_task_id = None
        old_user_id = None
        updating = True
        if old_dict[reminder_id]['list-id'] != reminder_dict['list-id'] or old_dict[reminder_id]['user-id'] != reminder_dict['user-id']:
            updating = False
            if old_dict[reminder_id]['user-id'] != 'local':
                old_list_id = self.list_ids[old_dict[reminder_id]['list-id']]['ms-id'] if old_dict[reminder_id]['list-id'] in self.list_ids.keys() else None
                old_task_id = old_dict[reminder_id]['ms-id']
                old_user_id = old_dict[reminder_id]['user-id']

        if dictionary != old_dict:
            old_dict.pop(reminder_id)

        dictionary[reminder_id] = reminder_dict

        self._set_countdown(reminder_id, dictionary)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders(dictionary if dictionary == old_dict else None)

        GLib.idle_add(lambda *args: self._ms_update_reminder(reminder_id, dictionary[reminder_id], old_user_id, old_list_id, old_task_id, updating, dictionary))

        return GLib.Variant('(u)', (now,))

    def return_reminders(self, dictionary = None, ids = None, return_variant = True):
        array = []
        if dictionary is None:
            dictionaries = [self.local, self.ms]
        else:
            dictionaries = [dictionary]
        for dictionary in dictionaries:
            for reminder in dictionary:
                if ids is not None and reminder not in ids:
                    continue
                array.append({
                    'id': GLib.Variant('s', reminder),
                    'title': GLib.Variant('s', dictionary[reminder]['title']),
                    'description': GLib.Variant('s', dictionary[reminder]['description']),
                    'due-date': GLib.Variant('u', dictionary[reminder]['due-date']),
                    'timestamp': GLib.Variant('u', dictionary[reminder]['timestamp']),
                    'shown': GLib.Variant('b', dictionary[reminder]['shown']),
                    'completed': GLib.Variant('b', dictionary[reminder]['completed']),
                    'important': GLib.Variant('b', dictionary[reminder]['important']),
                    'repeat-type': GLib.Variant('q', dictionary[reminder]['repeat-type']),
                    'repeat-frequency': GLib.Variant('q', dictionary[reminder]['repeat-frequency']),
                    'repeat-days': GLib.Variant('q', dictionary[reminder]['repeat-days']),
                    'repeat-times': GLib.Variant('n', dictionary[reminder]['repeat-times']),
                    'repeat-until': GLib.Variant('u', dictionary[reminder]['repeat-until']),
                    'created-timestamp': GLib.Variant('u', dictionary[reminder]['created-timestamp']),
                    'updated-timestamp': GLib.Variant('u', dictionary[reminder]['updated-timestamp']),
                    'list-id': GLib.Variant('s', dictionary[reminder]['list-id']),
                    'user-id': GLib.Variant('s', dictionary[reminder]['user-id']),
                })

        if not return_variant:
            return array
        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))
        return GLib.Variant('(aa{sv})', ([{}]))

    def get_version(self):
        return GLib.Variant('(d)', (VERSION,))

    def create_list(self, app_id, user_id, list_name):
        if user_id in self.list_names:
            list_id = self._do_generate_id()
            if user_id != 'local':
                if user_id not in self.synced_ids:
                    self.synced_ids[user_id] = []
                if 'all' not in self.synced_ids[user_id]:
                    self.synced_ids[user_id].append(list_id)
                    self.set_enabled_lists(self.synced_ids, False)
                GLib.idle_add(lambda *args: self._ms_create_list(user_id, list_name, list_id))

            self.list_names[user_id][list_id] = list_name
            self._save_lists()
            self.do_emit('ListUpdated', GLib.Variant('(ssss)', (app_id, user_id, list_id, list_name)))
            return GLib.Variant('(s)', (list_id,))

    def rename_list(self, app_id, user_id, list_id, new_name):
        if user_id in self.list_names and list_id in self.list_names[user_id]:
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._ms_rename_list(user_id, new_name, list_id))
            self.list_names[user_id][list_id] = new_name
            self._save_lists()
            self.do_emit('ListUpdated', GLib.Variant('(ssss)', (app_id, user_id, list_id, new_name)))

    def delete_list(self, app_id, user_id, list_id):
        if list_id == user_id:
            raise Exception('Tried to remove default list')
        if user_id in self.list_names and list_id in self.list_names[user_id]:
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._ms_delete_list(user_id, list_id))
            self.list_names[user_id].pop(list_id)
            self._save_lists()
            self.do_emit('ListRemoved', GLib.Variant('(sss)', (app_id, user_id, list_id)))
            GLib.idle_add(self.refresh)

    def login_todo(self):
        user_id = self.to_do.login()
        if user_id:
            self.emit_login(user_id)

    def logout_todo(self, user_id: str):
        self.to_do.logout(user_id)
        if user_id in self.synced_ids:
            self.synced_ids.pop(user_id)
            self.set_enabled_lists(self.synced_ids, False)
        self.do_emit('MSSignedOut', GLib.Variant('(s)', (user_id,)))
        self.refresh()
        logger.info('Logged out of Microsoft account')

    def refresh(self, notify_past = True):
        try:
            self.countdowns.add_timeout(self.refresh_time, self._refresh_cb, 'refresh')

            local, ms, list_names, list_ids = self._get_reminders(notify_past)

            new_ids = []
            removed_ids = []
            for new, old in (local, self.local), (ms, self.ms):
                for reminder_id, reminder in new.items():
                    if reminder_id not in old.keys() or reminder != old[reminder_id]:
                        new_ids.append(reminder_id)
                for reminder_id in old.keys():
                    if reminder_id not in new.keys():
                        removed_ids.append(reminder_id)

            for user_id, value in list_names.items():
                for list_id, list_name in value.items():
                    if user_id not in self.list_names or list_id not in self.list_names[user_id] or self.list_names[user_id][list_id] != list_names[user_id][list_id]:
                        self.do_emit('ListUpdated', GLib.Variant('(ssss)', (info.service_id, user_id, list_id, list_name)))

            for user_id, value in self.list_names.items():
                for list_id in value.keys():
                    if user_id not in list_names or list_id not in list_names[user_id]:
                        self.do_emit('ListRemoved', GLib.Variant('(sss)', (info.service_id, user_id, list_id)))

            if list_names != self.list_names:
                self.list_names = list_names
                self._save_lists()

            if list_ids != self.list_ids:
                self.list_ids = list_ids
                self._save_list_ids()

            if self.local != local:
                self.local = local
                self._save_reminders(self.local)

            if self.ms != ms:
                self.ms = ms
                self._save_reminders(self.ms)

            try:
                self.queue.load()
            except:
                pass

            if len(new_ids) > 0 or len(removed_ids) > 0:
                new_reminders = self.return_reminders(ids=new_ids, return_variant=False)

                self.do_emit('Refreshed', GLib.Variant('(aa{sv}as)', (new_reminders, removed_ids)))

                for reminder_id in new_ids:
                    if reminder_id in self.ms:
                        self._set_countdown(reminder_id, self.ms)
                    if reminder_id in self.local:
                        self._set_countdown(reminder_id, self.local)
                for reminder_id in removed_ids:
                    self._remove_countdown(reminder_id)

        except Exception as error:
            logger.exception(error)

    def return_lists(self):
        return GLib.Variant('(a{sa{ss}})', (self.list_names,))

    def set_enabled_lists(self, lists: dict, refresh = True):
        variant = GLib.Variant('a{sas}', lists)

        if not refresh:
            self.app.settings.disconnect(self.synced_changed)

        self.app.settings.set_value('synced-task-lists', variant)

        if not refresh:
            self.synced_changed = self.app.settings.connect('changed::synced-task-lists', lambda *args: self._synced_task_list_changed())

    def get_enabled_lists(self):
        lists = self.app.settings.get_value('synced-task-lists').unpack()
        return GLib.Variant('(a{sas})', (lists,))

    def get_emails(self):
        emails = {}
        for user_id in self.to_do.users:
            emails[user_id] = self.to_do.users[user_id]['email']
        return GLib.Variant('(a{ss})', (emails,))
