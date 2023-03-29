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

REFRESH_TIME = 600000 # 10 min

REMINDERS_FILE = f'{info.data_dir}/reminders.csv'
MS_REMINDERS_FILE = f'{info.data_dir}/ms_reminders.csv'
TASK_LISTS_FILE = f'{info.data_dir}/task_lists.json'
TASK_LIST_IDS_FILE = f'{info.data_dir}/task_list_ids.csv'

FIELDNAMES = [
    'id',
    'title',
    'description',
    'timestamp',
    'completed',
    'repeat-type',
    'repeat-frequency',
    'repeat-days',
    'repeat-until',
    'repeat-times',
    'old-timestamp'
]

MS_FIELDNAMES = [
    'id',
    'title',
    'description',
    'timestamp',
    'completed',
    'repeat-times',
    'old-timestamp',
    'list',
    'user-id',
    'ms-id'
]

REMINDER_DEFAULTS = {
    'title': '',
    'description': '',
    'timestamp': 0,
    'completed': False,
    'repeat-type': 0,
    'repeat-frequency': 1,
    'repeat-days': 0,
    'repeat-until': 0,
    'repeat-times': 1,
    'old-timestamp': 0,
    'list': 'local',
    'user-id': 'local',
    'ms-id': ''
}

VERSION = info.service_version
PID = os.getpid()

logger = logging.getLogger(info.service_executable)

XML = f'''<node name="/">
<interface name="{info.service_interface}">
    <method name='AddReminder'>
        <arg name='app-id' type='s'/>
        <arg name='args' type='a{{sv}}'/>
        <arg name='reminder-id' direction='out' type='s'/>
    </method>
    <method name='UpdateReminder'>
        <arg name='app-id' type='s'/>
        <arg name='args' type='a{{sv}}'/>
    </method>
    <method name='UpdateCompleted'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-id' type='s'/>
        <arg name='completed' type='b'/>
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
    </signal>
    <signal name='ReminderDeleted'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder-id' direction='out' type='s'/>
    </signal>
    <signal name='ReminderUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder' direction='out' type='a{{sv}}'/>
    </signal>
    <signal name='RepeatUpdated'>
        <arg name='reminder-id' direction='out' type='s'/>
        <arg name='timestamp' direction='out' type='u'/>
        <arg name='old-timestamp' direction='out' type='u'/>
        <arg name='repeat-times' direction='out' type='n'/>
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
</interface>
</node>'''

class Reminders():
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        if not os.path.isdir(info.data_dir):
            os.mkdir(info.data_dir)
        self.list_names = {}
        self.list_ids = {}
        self.local = {}
        self.ms = {}
        self.to_do = MSToDo(self)
        self.queue = Queue(self)
        self._regid = None
        self.app = app
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.sound = GSound.Context()
        self.sound.init()
        self.countdowns = Countdowns()
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.app.settings.connect('changed::synced-task-lists', lambda *args: self._synced_task_list_changed())
        self.local, self.ms, self.list_names, self.list_ids = self._get_reminders()
        try:
            self.queue.load()
        except:
            pass
        self._save_reminders()
        self._save_lists()
        self._save_list_ids()
        self._methods = {
            'UpdateCompleted': self.set_completed,
            'AddReminder': self.add_reminder,
            'UpdateReminder': self.update_reminder,
            'RemoveReminder': self.remove_reminder,
            'ReturnReminders': self.return_reminders,
            'GetVersion': self.get_version,
            'MSGetEmails': self.get_emails,
            'ReturnLists': self.return_lists,
            'Refresh': (self.refresh, True),
            'MSLogout': (self.logout_todo, True),
            'MSGetSyncedLists': self.get_enabled_lists,
            'MSSetSyncedLists': self.set_enabled_lists,
            'CreateList': self.create_list,
            'RenameList': self.rename_list,
            'RemoveList': self.delete_list
        }
        self._register()

    def update_reminder_ids(self, local, ms, list_ids):
        if local != self.local:
            self.local = local
            self._save_reminders(self.local)
        if ms != self.ms:
            self.ms = ms
            self._save_reminders(self.ms)
        if list_ids != self.list_ids:
            self.list_ids = list_ids
            self._save_list_ids()

    def emit_login(self, user_id):
        email = self.to_do.users[user_id]['email']
        self.synced_ids[user_id] = ['all']
        self.set_enabled_lists(self.synced_ids)
        self.do_emit('MSSignedIn', GLib.Variant('(ss)', (user_id, email)))
        self.refresh()
        logger.info('Logged into Microsoft account')

    def start_countdowns(self):
        self.start_local_countdowns()
        self.start_ms_countdowns()

    def start_local_countdowns(self):
        for reminder_id in self.local.keys():
            self._set_countdown(reminder_id)

    def start_ms_countdowns(self):
        for reminder_id in self.ms.keys():
            self._set_countdown(reminder_id)

        self.countdowns.add_timeout(REFRESH_TIME, self.refresh, -1)

    def do_emit(self, signal_name, parameters):
        self.connection.emit_signal(
            None,
            info.service_object,
            info.service_interface,
            signal_name,
            parameters
        )

    def _synced_task_list_changed(self):
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.do_emit('MSSyncedListsChanged', self.get_enabled_lists())

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
            'repeat-type': GLib.Variant('q', reminder['repeat-type']),
            'repeat-frequency': GLib.Variant('q', reminder['repeat-frequency']),
            'repeat-days': GLib.Variant('q', reminder['repeat-days']),
            'repeat-times': GLib.Variant('n', reminder['repeat-times']),
            'repeat-until': GLib.Variant('u', reminder['repeat-until']),
            'list': GLib.Variant('s', reminder['list']),
            'user-id': GLib.Variant('s', reminder['user-id'])
        }
        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, variant)))

    def _sync_ms(self, old_ms, old_lists, old_list_ids):
        try:
            lists = self.to_do.get_lists(self.synced_ids)
        except:
            return old_ms, old_lists, old_list_ids
        if lists is None:
            return {}, {}, {}

        ms_reminders = {}
        list_names = {}
        list_ids = {}

        for user_id in lists.keys():
            list_names[user_id] = {}
            for task_list in lists[user_id]:
                list_id = None

                if not task_list['default']:
                    try:
                        for task_list_id, value in old_list_ids.items():
                            if value['ms-id'] == task_list['id'] and value['user-id'] == user_id:
                                list_id = task_list_id
                                list_ids[list_id] = old_list_ids[task_list_id]
                    except:
                        pass
                if list_id is None:
                    list_id = 'ms-tasks' if task_list['default'] else self._do_generate_id()
                    list_ids[list_id] = {
                        'ms-id': task_list['id'],
                        'user-id': user_id
                    }

                list_names[user_id][list_id] = task_list['name']

                for task in task_list['tasks']:
                    task_id = task['id']
                    reminder_id = None
                    for old_reminder_id, old_reminder in self.ms.items():
                        if old_reminder['ms-id'] == task_id:
                            reminder_id = old_reminder_id
                            break

                    if reminder_id is None:
                        reminder_id = self._do_generate_id()

                    timestamp = self._rfc_to_timestamp(task['reminderDateTime']['dateTime']) if 'reminderDateTime' in task else 0

                    if reminder_id in self.ms:
                        reminder = old_ms[reminder_id].copy()
                    else:
                        is_future = timestamp > floor(time.time())
                        reminder = {}
                        if old_ms == {}:
                            reminder['repeat-times'] = 0
                        else:
                            reminder['repeat-times'] = 1 if is_future else 0

                        reminder['old-timestamp'] = 0 if is_future else timestamp

                    reminder['ms-id'] = task_id
                    reminder['title'] = task['title'].strip()
                    reminder['description'] = task['body']['content'].strip() if task['body']['contentType'] == 'text' else ''
                    reminder['completed'] = True if 'status' in task and task['status'] == 'completed' else False
                    reminder['timestamp'] = timestamp
                    reminder['repeat-type'] = 0
                    reminder['repeat-frequency'] = 1
                    reminder['repeat-days'] = 0
                    reminder['repeat-until'] = 0
                    if timestamp < floor(time.time()):
                        reminder['old-timestamp'] = timestamp
                    reminder['list'] = list_id
                    reminder['user-id'] = user_id

                    ms_reminders[reminder_id] = reminder

        for reminder_id in self.queue.get_updated_reminder_ids():
            if reminder_id in old_ms:
                ms_reminders[reminder_id] = old_ms[reminder_id]

        for reminder_id in self.queue.get_removed_reminder_ids():
            if reminder_id in ms_reminders:
                ms_reminders.pop(reminder_id)

        for list_id in self.queue.get_updated_list_ids():
            if list_id in old_list_ids:
                user_id = old_list_ids[list_id]['user-id']
                if user_id in old_lists and list_id in old_lists[user_id]:
                    list_ids[list_id] = old_list_ids[list_id]
                    if user_id not in list_names:
                        list_names[user_id] = {}
                    list_names[user_id][list_id] = old_lists[user_id][list_id]

        for list_id in self.queue.get_removed_list_ids():
            if list_id in list_ids:
                user_id = list_ids[list_id]['user-id']
                if user_id in list_names and list_id in list_names[user_id]:
                    list_names[user_id].pop(list_id)
                list_ids.pop(list_id)

        return ms_reminders, list_names, list_ids

    def _to_ms_task(self, reminder_id, reminder = None, old_user_id = None, old_task_list = None, updating = None, only_completed = False):
        if reminder is None:
            reminder = self.ms[reminder_id] if reminder_id in self.ms else self.local[reminder_id]

        user_id = reminder['user-id']
        task_list = reminder['list']
        moving = old_task_list not in (None, task_list)

        if updating is None:
            updating = reminder_id in self.ms and (old_task_list is None or task_list == old_task_list)

        reminder_json = {}
        new_task_id = None
        if task_list != 'local' and user_id != 'local':
            if reminder['completed']:
                reminder_json['status'] = 'completed'

            if not only_completed:
                reminder_json['title'] = reminder['title']
                reminder_json['body'] = {}
                reminder_json['body']['content'] = reminder['description']
                reminder_json['body']['contentType'] = 'text'

                if reminder['timestamp'] != 0:
                    reminder_json['isReminderOn'] = True
                    reminder_json['reminderDateTime'] = {}
                    reminder_json['reminderDateTime']['dateTime'] = self._timestamp_to_rfc(reminder['timestamp'])
                    reminder_json['reminderDateTime']['timeZone'] = 'UTC'
                else:
                    reminder_json['isReminderOn'] = False
            if updating:
                new_task_id = self.to_do.update_task(user_id, self.list_ids[task_list]['ms-id'], self.ms[reminder_id]['ms-id'], reminder_json)
            else:
                new_task_id = self.to_do.create_task(user_id, self.list_ids[task_list]['ms-id'], reminder_json)

        if moving:
            if old_task_list != 'local' and old_user_id != 'local':
                if old_user_id is None:
                    old_user_id = user_id
                self.to_do.remove_task(old_user_id, self.list_ids[old_task_list]['ms-id'], self.ms[reminder_id]['ms-id'])

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

            return_first = False
            method = self._methods[method]
            if isinstance(method, tuple):
                return_first = method[1]
                method = method[0]

            if return_first:
                invocation.return_value(None)

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
            if not return_first:
                invocation.return_value(retval)
        except Exception as error:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed', f'{error} - Method {method} failed to execute\n{"".join(traceback.format_exception(error))}')

    def _generate_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def _do_generate_id(self):
        new_id = self._generate_id()
        # if for some reason it isn't unique
        while new_id in self.local or new_id in self.ms or \
        ('local' in self.list_names and new_id in self.list_names['local'].keys()):
            new_id = self._generate_id()

        return new_id

    def _remove_countdown(self, reminder_id):
        self.countdowns.remove_countdown(reminder_id)

    def _set_countdown(self, reminder_id):
        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary:
                reminder = dictionary[reminder_id]
                if reminder['timestamp'] == 0:
                    return

                if reminder['repeat-times'] == 0:
                    reminder['old-timestamp'] = reminder['timestamp']
                    self.do_emit('RepeatUpdated', GLib.Variant('(suun)', (reminder_id, reminder['timestamp'], reminder['old-timestamp'], reminder['repeat-times'])))
                    return

                if reminder['completed']:
                    return

                notification = Gio.Notification.new(dictionary[reminder_id]['title'])
                notification.set_body(dictionary[reminder_id]['description'])
                notification.add_button_with_target(_('Mark as completed'), 'app.reminder-completed', GLib.Variant('s', reminder_id))
                notification.set_default_action('app.notification-clicked')

                def do_send_notification():
                    self.app.send_notification(reminder_id, notification)
                    if self.app.settings.get_boolean('notification-sound'):
                        try:
                            self.sound.play_simple({GSound.ATTR_EVENT_ID: 'bell'})
                        except Exception as error:
                            logger.error(f"{error} Couldn't play notification sound")
                    self._shown(reminder_id)
                    self.countdowns.dict[reminder_id]['id'] = 0
                    self._update_repeat(reminder_id)
                    return False

                self.countdowns.add_countdown(reminder['timestamp'], do_send_notification, reminder_id)

    def _update_repeat(self, reminder_id):
        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary:
                dictionary[reminder_id]['old-timestamp'] = dictionary[reminder_id]['timestamp']
                # ms reminders shouldn't repeat
                if dictionary == self.local:
                    if self.local[reminder_id]['repeat-type'] != 0:
                        self._repeat(reminder_id)
                retval = GLib.Variant('(suun)', (reminder_id, dictionary[reminder_id]['timestamp'], dictionary[reminder_id]['old-timestamp'], dictionary[reminder_id]['repeat-times']))

        self.do_emit('RepeatUpdated', retval)

    def _repeat(self, reminder_id):
        delta = None
        repeat_times = self.local[reminder_id]['repeat-times']
        if repeat_times == 0:
            return
        timestamp = self.local[reminder_id]['timestamp']
        old_timestamp = self.local[reminder_id]['old-timestamp']
        repeat_until = self.local[reminder_id]['repeat-until']
        if repeat_until > 0 and repeat_until < timestamp:
            return

        repeat_type = self.local[reminder_id]['repeat-type']
        frequency = self.local[reminder_id]['repeat-frequency']
        repeat_days = self.local[reminder_id]['repeat-days']
        timedate = datetime.datetime.fromtimestamp(timestamp)

        if repeat_type == info.RepeatType.MINUTE:
            delta = datetime.timedelta(minutes=frequency)
        elif repeat_type == info.RepeatType.HOUR:
            delta = datetime.timedelta(hours=frequency)
        elif repeat_type == info.RepeatType.DAY:
            delta = datetime.timedelta(days=frequency)

        if delta is not None:
            timedate += delta
            timestamp = timedate.timestamp()
            while timestamp < floor(time.time()):
                old_timestamp = timestamp
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                timedate += delta
                timestamp = timedate.timestamp()

        if repeat_type == info.RepeatType.WEEK:
            week_frequency = 0
            weekday = timedate.date().weekday()
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

            timedate += datetime.timedelta(days=(((days[index] - weekday) % 7) + 7 * week_frequency))
            timestamp = timedate.timestamp()

            while timestamp < floor(time.time()):
                week_frequency = 0
                old_timestamp = timestamp
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                weekday = timedate.date().weekday()
                index += 1
                if index > len(days) - 1:
                    index = 0
                    week_frequency = frequency - 1

                timedate += datetime.timedelta(days=(((days[index] - weekday) % 7) + 7 * week_frequency))
                timestamp = timedate.timestamp()


        if repeat_until > 0 and repeat_until < floor(timestamp):
            return

        self.local[reminder_id]['repeat-times'] = repeat_times
        self.local[reminder_id]['timestamp'] = floor(timestamp)
        self.local[reminder_id]['old-timestamp'] = int(old_timestamp)

        self._save_reminders(self.local)

        if repeat_times != 0:
            self._set_countdown(reminder_id)

    def _shown(self, reminder_id):
        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary:
                if dictionary[reminder_id]['repeat-times'] > 0:
                    dictionary[reminder_id]['repeat-times'] -= 1
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
                        'timestamp': self.local[reminder]['timestamp'],
                        'completed': self.local[reminder]['completed'],
                        'repeat-type': self.local[reminder]['repeat-type'],
                        'repeat-frequency': self.local[reminder]['repeat-frequency'],
                        'repeat-days': self.local[reminder]['repeat-days'],
                        'repeat-times': self.local[reminder]['repeat-times'],
                        'repeat-until': self.local[reminder]['repeat-until'],
                        'old-timestamp': self.local[reminder]['old-timestamp']
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
                        'timestamp': self.ms[reminder]['timestamp'],
                        'completed': self.ms[reminder]['completed'],
                        'repeat-times': self.ms[reminder]['repeat-times'],
                        'old-timestamp': self.ms[reminder]['old-timestamp'],
                        'list': self.ms[reminder]['list'],
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

    def _get_boolean(self, row, key):
        return (key in row.keys() and row[key] == 'True')

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
                        list_id = self._get_str(row, 'list')
                        if user_id not in self.synced_ids.keys() or ('all' not in self.synced_ids[user_id] and list_id not in self.synced_ids[user_id]):
                            continue

                        timestamp = self._get_int(row, 'timestamp')

                        reminder_id = row['id']

                        old_ms[reminder_id] = REMINDER_DEFAULTS.copy()
                        old_ms[reminder_id]['ms-id'] = self._get_str(row, 'ms-id')
                        old_ms[reminder_id]['title'] = self._get_str(row, 'title')
                        old_ms[reminder_id]['description'] = self._get_str(row, 'description')
                        old_ms[reminder_id]['timestamp'] = timestamp
                        old_ms[reminder_id]['completed'] = self._get_boolean(row, 'completed')
                        old_ms[reminder_id]['repeat-times'] = self._get_int(row, 'repeat-times')
                        old_ms[reminder_id]['old-timestamp'] = timestamp if timestamp < floor(time.time()) else self._get_int(row, 'old-timestamp')
                        old_ms[reminder_id]['user-id'] = user_id
                        old_ms[reminder_id]['list'] = list_id

        return old_ms

    def _get_reminders(self):
        local = {}
        ms = {}
        list_ids = {}
        ms_list_names = {}
        list_names = {}
        if os.path.isfile(REMINDERS_FILE):
            with open(REMINDERS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    reminder_id = row['id']
                    timestamp = self._get_int(row, 'timestamp')
                    repeat_type = self._get_int(row, 'repeat-type')

                    local[reminder_id] = REMINDER_DEFAULTS.copy()
                    local[reminder_id]['ms-id'] = self._get_str(row, 'ms-id')
                    local[reminder_id]['title'] = self._get_str(row, 'title')
                    local[reminder_id]['description'] = self._get_str(row, 'description')
                    local[reminder_id]['timestamp'] = timestamp
                    local[reminder_id]['completed'] = self._get_boolean(row, 'completed')
                    local[reminder_id]['repeat-type'] = repeat_type
                    if repeat_type != 0:
                        local[reminder_id]['repeat-frequency'] = self._get_int(row, 'repeat-frequency')
                        local[reminder_id]['repeat-days'] = self._get_int(row, 'repeat-days')
                        local[reminder_id]['repeat-until'] = self._get_int(row, 'repeat-until')
                    local[reminder_id]['repeat-times'] = self._get_int(row, 'repeat-times')
                    local[reminder_id]['old-timestamp'] = timestamp if timestamp < floor(time.time()) else self._get_int(row, 'old-timestamp')
                    local[reminder_id]['user-id'] = self._get_str(row, 'user-id')
                    local[reminder_id]['list'] = self._get_str(row, 'list')

        if os.path.isfile(TASK_LIST_IDS_FILE):
            with open(TASK_LIST_IDS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    list_ids[row['list-id']] = {
                        'ms-id': row['ms-id'],
                        'user-id': row['user-id']
                    }

        if os.path.isfile(TASK_LISTS_FILE):
            with open(TASK_LISTS_FILE, newline='') as jsonfile:
                all_list_names = json.load(jsonfile)
                ms_list_names = all_list_names.copy()
                if 'local' in ms_list_names.keys():
                    ms_list_names.pop('local')
                list_names['local'] = all_list_names['local'] if 'local' in all_list_names.keys() else {}

        if 'local' not in list_names['local'].keys():
            list_names['local']['local'] = _('Local Reminders')

        old_ms = self._get_saved_ms_reminders()
        ms, ms_list_names, list_ids = self._sync_ms(old_ms, ms_list_names, list_ids)
        list_names.update(ms_list_names)

        return local, ms, list_names, list_ids

    # Below methods can be accessed by other apps over dbus
    def set_completed(self, app_id: str, reminder_id: str, completed: bool):
        task_list = 'local'
        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary.keys():
                user_id = dictionary[reminder_id]['user-id']
                task_list = dictionary[reminder_id]['list']
                dictionary[reminder_id]['completed'] = completed
                self._save_reminders(dictionary)
                try:
                    self.queue.load()
                    self._to_ms_task(reminder_id, dictionary[reminder_id], only_completed=True)
                except requests.ConnectionError:
                    self.queue.update_completed(reminder_id)
                if completed:
                    self._remove_countdown(reminder_id)
                else:
                    self._set_countdown(reminder_id)

                self.do_emit('CompletedUpdated', GLib.Variant('(ssb)', (app_id, reminder_id, completed)))
                break

    def remove_reminder(self, app_id: str, reminder_id: str):
        self.app.withdraw_notification(reminder_id)
        self._remove_countdown(reminder_id)

        for dictionary in (self.local, self.ms):
            if reminder_id in dictionary:
                if dictionary == self.ms:
                    task_id = self.ms[reminder_id]['ms-id']
                    user_id = dictionary[reminder_id]['user-id']
                    task_list = dictionary[reminder_id]['list']
                    try:
                        self.queue.load()
                        self.to_do.remove_task(user_id, task_list, task_id)
                    except requests.ConnectionError as error:
                        self.queue.remove_reminder(reminder_id)
                dictionary.pop(reminder_id)
                self._save_reminders(dictionary)
                break

        self.do_emit('ReminderDeleted', GLib.Variant('(ss)', (app_id, reminder_id)))

    def add_reminder(self, app_id: str, **kwargs):
        reminder_id = self._do_generate_id()

        reminder_dict = REMINDER_DEFAULTS.copy()

        for i in ('title', 'description', 'list', 'user-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'repeat-type', 'repeat-frequency', 'repeat-days', 'repeat-times', 'repeat-until'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        dictionary = self.local if reminder_dict['user-id'] == 'local' else self.ms

        try:
            self.queue.load()
            ms_id = self._to_ms_task(reminder_id, reminder_dict)
        except requests.ConnectionError:
            ms_id = None
            self.queue.add_reminder(reminder_id)

        reminder_dict['ms-id'] = ms_id if ms_id is not None else ''

        dictionary[reminder_id] = reminder_dict
        self._set_countdown(reminder_id)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders()

        return GLib.Variant('(s)', (reminder_id,))

    def update_reminder(self, app_id: str, **kwargs):
        reminder_id = str(kwargs['id'])

        old_dict = self.ms if reminder_id in self.ms else self.local

        reminder_dict = old_dict[reminder_id].copy()

        for i in ('title', 'description', 'list', 'user-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'repeat-type', 'repeat-frequency', 'repeat-days', 'repeat-times', 'repeat-until'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        dictionary = self.local if reminder_dict['user-id'] == 'local' else self.ms
        old_task_list = old_dict[reminder_id]['list'] if old_dict[reminder_id]['list'] != reminder_dict['list'] else None
        old_user_id = old_dict[reminder_id]['user-id'] if old_dict[reminder_id]['user-id'] != reminder_dict['user-id'] else None

        try:
            self.queue.load()
            ms_id = self._to_ms_task(reminder_id, reminder_dict, old_user_id, old_task_list)
        except requests.ConnectionError:
            ms_id = None
            args = [old_user_id, old_task_list]
            self.queue.update_reminder(reminder_id, args)

        reminder_dict['ms-id'] = ms_id if ms_id is not None else ''

        if dictionary != old_dict:
            old_dict.pop(reminder_id)

        dictionary[reminder_id] = reminder_dict

        self._set_countdown(reminder_id)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders(dictionary if dictionary == old_dict else None)

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
                    'timestamp': GLib.Variant('u', dictionary[reminder]['timestamp']),
                    'completed': GLib.Variant('b', dictionary[reminder]['completed']),
                    'repeat-type': GLib.Variant('q', dictionary[reminder]['repeat-type']),
                    'repeat-frequency': GLib.Variant('q', dictionary[reminder]['repeat-frequency']),
                    'repeat-days': GLib.Variant('q', dictionary[reminder]['repeat-days']),
                    'repeat-times': GLib.Variant('n', dictionary[reminder]['repeat-times']),
                    'repeat-until': GLib.Variant('u', dictionary[reminder]['repeat-until']),
                    'old-timestamp': GLib.Variant('u', dictionary[reminder]['old-timestamp']),
                    'list': GLib.Variant('s', dictionary[reminder]['list']),
                    'user-id': GLib.Variant('s', dictionary[reminder]['user-id'])
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
                self.synced_ids[user_id].append(list_id)
                self.set_enabled_lists(self.synced_ids)
                try:
                    self.queue.load()
                    ms_id = self.to_do.create_list(user_id, list_name, list_id)
                    self.list_ids[list_id] = {
                        'ms-id': '' if ms_id is None else ms_id,
                        'user-id': user_id
                    }
                    self._save_list_ids()
                except requests.ConnectionError:
                    self.list_ids[list_id] = {
                        'ms-id': '',
                        'user-id': user_id
                    }
                    self._save_list_ids()
                    self.queue.add_list(list_id)

            self.list_names[user_id][list_id] = list_name
            self._save_lists()
            self.do_emit('ListUpdated', GLib.Variant('(ssss)', (app_id, user_id, list_id, list_name)))
            return GLib.Variant('(s)', (list_id,))

    def rename_list(self, app_id, user_id, list_id, new_name):
        if user_id in self.list_names and list_id in self.list_names[user_id]:
            if user_id != 'local':
                try:
                    self.queue.load()
                    ms_id = self.list_ids[list_id]['ms-id']
                    self.to_do.update_list(user_id, ms_id, list_name, list_id)
                except requests.ConnectionError:
                    self.queue.update_list(list_id)
            self.list_names[user_id][list_id] = new_name
            self._save_lists()
            self.do_emit('ListUpdated', GLib.Variant('(ssss)', (app_id, user_id, list_id, new_name)))

    def delete_list(self, app_id, user_id, list_id):
        if user_id in self.list_names and list_id in self.list_names[user_id]:
            if user_id != 'local':
                try:
                    self.queue.load()
                    ms_id = self.list_ids[list_id]['ms-id']
                    self.to_do.delete_list(user_id, ms_id, list_id)
                except requests.ConnectionError:
                    self.queue.remove_list(list_id)
                self.list_ids.pop(list_id)
                self._save_list_ids()
            self.list_names[user_id].pop(list_id)
            self._save_lists()
            self.do_emit('ListRemoved', GLib.Variant('(sss)', (app_id, user_id, list_id)))

    def login_todo(self):
        user_id = self.to_do.login()
        if user_id:
            self.emit_login(user_id)

    def logout_todo(self, user_id: str):
        self.to_do.logout(user_id)
        if user_id in self.synced_ids:
            self.synced_ids.pop(user_id)
            self.set_enabled_lists(self.synced_ids)
        self.do_emit('MSSignedOut', GLib.Variant('(s)', (user_id,)))
        self.refresh()
        logger.info('Logged out of Microsoft account')

    def refresh(self):
        try:
            self.countdowns.add_timeout(REFRESH_TIME, self.refresh, -1)

            local, ms, list_names, list_ids = self._get_reminders()

            new_ids = []
            removed_ids = []
            for new, old in (local, self.local), (ms, self.ms):
                logger.info(new)
                logger.info(old)
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

            new_reminders = self.return_reminders(ids=new_ids, return_variant=False)

            self.do_emit('Refreshed', GLib.Variant('(aa{sv}as)', (new_reminders, removed_ids)))

            for reminder_id in new_ids:
                self._set_countdown(reminder_id)

            for reminder_id in removed_ids:
                self._remove_countdown(reminder_id)

        except Exception as error:
            # The refreshed signal should always be emitted
            self.do_emit('Refreshed', GLib.Variant('(aa{sv}as)', ([{}], [])))
            traceback.print_exception(error)

    def return_lists(self):
        return GLib.Variant('(a{sa{ss}})', (self.list_names,))

    def set_enabled_lists(self, lists: dict):
        variant = GLib.Variant('a{sas}', lists)
        self.app.settings.set_value('synced-task-lists', variant)

    def get_enabled_lists(self):
        lists = self.app.settings.get_value('synced-task-lists').unpack()
        return GLib.Variant('(a{sas})', (lists,))

    def get_emails(self):
        emails = {}
        for user_id in self.to_do.users:
            emails[user_id] = self.to_do.users[user_id]['email']
        return GLib.Variant('(a{ss})', (emails,))
