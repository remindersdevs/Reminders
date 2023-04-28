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
import datetime
import gi
import traceback
import requests
import uuid

gi.require_version('GSound', '1.0')
gi.require_version('Secret', '1')
from gi.repository import GLib, Gio, GSound, Secret
from remembrance import info
from remembrance.service.ms_to_do import MSToDo
from remembrance.service.caldav import CalDAV
from remembrance.service.queue import Queue
from remembrance.service.countdowns import Countdowns
from remembrance.service.icalendar import iCalendar
from remembrance.service.reminder import Reminder

from gettext import gettext as _
from math import floor
from calendar import monthrange

REMINDERS_FILE = f'{info.data_dir}/reminders.csv'
TASK_LISTS_FILE = f'{info.data_dir}/task_lists.json'
TASK_LIST_IDS_FILE = f'{info.data_dir}/task_list_ids.csv'

VERSION = info.service_version
PID = os.getpid()

logger = logging.getLogger(info.service_executable)

XML = f'''<node name="/">
<interface name="{info.service_interface}">
    <method name='GetUsers'>
        <arg name='usernames' direction='out' type='a{{sa{{ss}}}}'/>
    </method>
    <method name='GetLists'>
        <arg name='lists' direction='out' type='a{{sa{{ss}}}}'/>
    </method>
    <method name='GetReminders'>
        <arg name='reminders' direction='out' type='aa{{sv}}'/>
    </method>
    <method name='GetRemindersInList'>
        <arg name='user-id' type='s'/>
        <arg name='list-id' type='s'/>
        <arg name='reminders' direction='out' type='aa{{sv}}'/>
    </method>
    <method name='GetSyncedLists'>
        <arg name='list-ids' direction='out' type='a{{sas}}'/>
    </method>
    <method name='SetSyncedLists'>
        <arg name='synced-lists' type='a{{sas}}'/>
    </method>
    <method name='GetWeekStart'>
        <arg name='week-start-sunday' direction='out' type='b'/>
    </method>
    <method name='SetWeekStart'>
        <arg name='week-start-sunday' type='b'/>
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
    <method name='MSGetLoginURL'>
        <arg name='url' direction='out' type='s'/>
    </method>
    <method name='CalDAVLogin'>
        <arg name='display-name' type='s'/>
        <arg name='url' type='s'/>
        <arg name='username' type='s'/>
        <arg name='password' type='s'/>
    </method>
    <method name='CalDAVUpdateDisplayName'>
        <arg name='user-id' type='s'/>
        <arg name='display-name' type='s'/>
    </method>
    <method name='Logout'>
        <arg name='user-id' type='s'/>
    </method>
    <method name='ExportLists'>
        <arg name='lists' type='a(ss)'/>
        <arg name='folder' direction='out' type='s'/>
    </method>
    <method name='ImportLists'>
        <arg name='ical-files' type='as'/>
        <arg name='user-id' type='s'/>
        <arg name='list-id' type='s'/>
    </method>
    <method name='Refresh'/>
    <method name='RefreshUser'>
        <arg name='user-id' type='s'/>
    </method>
    <method name='GetVersion'>
        <arg name='version' direction='out' type='s'/>
    </method>
    <method name='Quit'/>
    <signal name='SyncedListsChanged'>
        <arg name='lists' direction='out' type='a{{sas}}'/>
    </signal>
    <signal name='WeekStartChanged'>
        <arg name='week-start-sunday' direction='out' type='b'/>
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
    <signal name='ReminderShown'>
        <arg name='reminder-id' direction='out' type='s'/>
    </signal>
    <signal name='ReminderUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder' direction='out' type='a{{sv}}'/>
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
    <signal name='Refreshed'>
        <arg name='updated-reminders' direction='out' type='aa{{sv}}'/>
        <arg name='removed-reminders' direction='out' type='as'/>
    </signal>
    <signal name='MSSignedIn'>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='username' direction='out' type='s'/>
    </signal>
    <signal name='CalDAVSignedIn'>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='name' direction='out' type='s'/>
    </signal>
    <signal name='UsernameUpdated'>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='username' direction='out' type='s'/>
    </signal>
    <signal name='SignedOut'>
        <arg name='user-id' direction='out' type='s'/>
    </signal>
    <signal name='Error'>
        <arg name='stack-trace' direction='out' type='s'/>
    </signal>
</interface>
</node>'''

class Reminders():
    def __init__(self, app):
        if not os.path.isdir(info.data_dir):
            os.mkdir(info.data_dir)
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.app = app
        self.reminders = self.lists = self.list_ids = {}
        self.schema = Secret.Schema.new(
            info.app_id,
            Secret.SchemaFlags.NONE,
            { 'name': Secret.SchemaAttributeType.STRING }
        )
        self.refreshing = False
        self._regid = None
        self.playing_sound = False
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.to_do = MSToDo(self)
        self.caldav = CalDAV(self)
        self.ical = iCalendar(self)
        self.queue = Queue(self)
        self.reminders, self.lists, self.list_ids = self._get_reminders()
        self.sound = GSound.Context()
        self.sound.init()
        self.countdowns = Countdowns()
        self.refresh_time = int(self.app.settings.get_string('refresh-frequency').strip('m'))
        self.synced_changed = self.app.settings.connect('changed::synced-task-lists', lambda *args: self._synced_task_list_changed())
        self.app.settings.connect('changed::refresh-frequency', lambda *args: self._refresh_time_changed())
        self.app.settings.connect('changed::week-starts-sunday', lambda *args: self._week_start_changed())
        try:
            self.queue.load()
        except:
            pass
        self._save_reminders()
        self._save_lists()
        self._save_list_ids()
        self._methods = {
            'GetUsers': self.get_users,
            'GetLists': self.get_lists,
            'GetReminders': self.get_reminders,
            'GetRemindersInList': self.get_reminders_in_list,
            'GetSyncedLists': self.get_synced_lists,
            'SetSyncedLists': self.set_synced_lists,
            'GetWeekStart': self.get_week_start,
            'SetWeekStart': self.set_week_start,
            'CreateList': self.create_list,
            'RenameList': self.rename_list,
            'RemoveList': self.delete_list,
            'CreateReminder': self.create_reminder,
            'UpdateReminder': self.update_reminder,
            'UpdateCompleted': self.update_completed,
            'RemoveReminder': self.remove_reminder,
            'MSGetLoginURL': self.get_todo_login_url,
            'CalDAVLogin': self.login_caldav,
            'CalDAVUpdateDisplayName': self.caldav_update_username,
            'Logout': self.logout,
            'ExportLists': self.export_lists,
            'ImportLists': self.import_lists,
            'Refresh': self.refresh,
            'RefreshUser': self.refresh_user,
            'GetVersion': self.get_version
        }
        self._register()

    def emit_error(self, error):
        logger.exception(error)
        self.do_emit('Error', GLib.Variant('(s)', ("".join(traceback.format_exception(error)),)))

    def emit_login(self, user_id):
        username = self.to_do.users[user_id]['email']
        self.synced_ids[user_id] = ['all']
        self._set_synced_lists_no_refresh(self.synced_ids)
        self.do_emit('MSSignedIn', GLib.Variant('(ss)', (user_id, username)))
        self.refresh(False, user_id)

    def start_countdowns(self):
        for reminder_id in self.reminders.keys():
            self._set_countdown(reminder_id)
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

    def _week_start_changed(self):
        starts_sunday = self.app.settings.get_boolean('week-starts-sunday')
        self.do_emit('WeekStartChanged', GLib.Variant('(b)', (starts_sunday,)))

    def _refresh_time_changed(self):
        self.refresh_time = int(self.app.settings.get_string('refresh-frequency').strip('m'))
        self.countdowns.add_timeout(self.refresh_time, self._refresh_cb, 'refresh')

    def _synced_task_list_changed(self):
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.do_emit('SyncedListsChanged', self.get_enabled_lists())
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

    def _set_synced_lists_no_refresh(self, lists):
        variant = GLib.Variant('a{sas}', lists)

        self.app.settings.disconnect(self.synced_changed)

        self.app.settings.set_value('synced-task-lists', variant)

        self.synced_changed = self.app.settings.connect('changed::synced-task-lists', lambda *args: self._synced_task_list_changed())

    def _sync_remote(self, old_reminders, old_lists, old_list_ids, notify_past, only_user_id):
        ms_lists, ms_not_synced = self.to_do.get_lists(only_user_id)

        caldav_lists, caldav_not_synced = self.caldav.get_lists(only_user_id)

        not_synced = ms_not_synced + caldav_not_synced

        if ms_lists is None:
            ms_lists = {}
        if caldav_lists is None:
            caldav_lists = {}

        new_reminders = old_reminders.copy()
        for reminder_id, reminder in old_reminders.items():
            if reminder['user-id'] != 'local' and reminder['user-id'] not in not_synced:
                new_reminders.pop(reminder_id)

        list_names = old_lists.copy()
        for user_id in old_lists.keys():
            if user_id != 'local' and user_id not in not_synced:
                list_names.pop(user_id)

        list_ids = old_list_ids.copy()
        for list_id, value in old_list_ids.items():
            if value['user-id'] != 'local' and value['user-id'] not in not_synced:
                list_ids.pop(list_id)

        updated_reminder_ids = self.queue.get_updated_reminder_ids()
        removed_reminder_ids = self.queue.get_removed_reminder_ids()

        updated_list_ids = self.queue.get_updated_list_ids()
        removed_list_ids = self.queue.get_removed_list_ids()

        for user_id in ms_lists.keys():
            list_names[user_id] = {}
            for task_list in ms_lists[user_id]:
                list_id = None

                if task_list['id'] in removed_list_ids:
                    continue

                if task_list['default']:
                    list_id = user_id
                else:
                    try:
                        for task_list_id, value in old_list_ids.items():
                            if value['uid'] == task_list['id'] and value['user-id'] == user_id:
                                list_id = task_list_id
                    except:
                        pass

                if list_id is None:
                    list_id = self._do_generate_id(used_ids)

                list_ids[list_id] = {
                    'uid': task_list['id'],
                    'user-id': user_id
                }

                list_names[user_id][list_id] = task_list['name']

                if user_id not in self.synced_ids or ('all' not in self.synced_ids[user_id] and list_id not in self.synced_ids[user_id]):
                    continue

                for task in task_list['tasks']:
                    if task['id'] in removed_reminder_ids:
                        continue

                    reminder_id = None
                    for old_reminder_id, old_reminder in old_reminders.items():
                        if old_reminder['uid'] == task['id']:
                            reminder_id = old_reminder_id
                            break

                    if reminder_id is None:
                        reminder_id = self._do_generate_id()

                    try:
                        timestamp = self._rfc_to_timestamp(task['reminderDateTime']['dateTime']) if 'reminderDateTime' in task else 0
                    except:
                        timestamp = 0

                    is_future = timestamp > floor(time.time())

                    if reminder_id in old_reminders:
                        if reminder_id in updated_reminder_ids:
                            continue
                        reminder = old_reminders[reminder_id].copy()
                    else:
                        reminder = Reminder()
                        reminder['shown'] = timestamp != 0 and not (is_future or notify_past)

                    new_reminders[reminder_id] = self.to_do.task_to_reminder(task, list_id, user_id, reminder, timestamp)

        for user_id in caldav_lists.keys():
            list_names[user_id] = {}
            for task_list in caldav_lists[user_id]:
                list_id = None

                if task_list['id'] in removed_list_ids:
                    continue

                try:
                    for task_list_id, value in old_list_ids.items():
                        if value['uid'] == task_list['id'] and value['user-id'] == user_id:
                            list_id = task_list_id
                except:
                    pass

                used_ids = []
                for value in list_names.values():
                    for used_list_id in value.keys():
                        used_ids.append(used_list_id)

                if list_id is None:
                    list_id = self._do_generate_id(used_ids)

                list_ids[list_id] = {
                    'uid': task_list['id'],
                    'user-id': user_id
                }

                list_names[user_id][list_id] = task_list['name']

                if user_id not in self.synced_ids or ('all' not in self.synced_ids[user_id] and list_id not in self.synced_ids[user_id]):
                    continue

                for task in task_list['tasks']:
                    task_id = task.icalendar_component.get('UID', None)
                    if task_id in removed_reminder_ids:
                        continue

                    reminder_id = None
                    for old_reminder_id, old_reminder in old_reminders.items():
                        if old_reminder['uid'] == task_id:
                            reminder_id = old_reminder_id
                            break

                    if reminder_id is None:
                        reminder_id = self._do_generate_id()

                    due_date = 0
                    timestamp = 0
                    due = task.icalendar_component.get('DUE', None)
                    if due is not None:
                        due = due.dt
                        try:
                            if isinstance(due, datetime.datetime):
                                timestamp = due.timestamp()
                            elif isinstance(due, datetime.date):
                                due_date = datetime.combine(due, datetime.time(), tzinfo=datetime.timezone.utc).timestamp()
                        except:
                            pass

                    is_future = timestamp > floor(time.time())

                    if reminder_id in old_reminders:
                        if reminder_id in updated_reminder_ids:
                            continue
                        reminder = old_reminders[reminder_id].copy()
                    else:
                        reminder = Reminder()
                        reminder['shown'] = timestamp != 0 and not (is_future or notify_past)

                    new_reminders[reminder_id] = self.caldav.task_to_reminder(task.icalendar_component, list_id, user_id, reminder, timestamp, due_date)

        for reminder_id in updated_reminder_ids:
            if reminder_id in old_reminders.keys():
                new_reminders[reminder_id] = old_reminders[reminder_id].copy()

        for list_id in updated_list_ids:
            if list_id in old_list_ids.keys():
                user_id = old_list_ids[list_id]['user-id']
                if user_id in old_lists and list_id in old_lists[user_id]:
                    list_ids[list_id] = old_list_ids[list_id]
                    if user_id not in list_names:
                        list_names[user_id] = {}
                    list_names[user_id][list_id] = old_lists[user_id][list_id]

        return new_reminders, list_names, list_ids

    def _do_remote_create_reminder(self, reminder_id, location):
        try:
            try:
                self.queue.load()
                uid = self._to_remote_task(self.reminders[reminder_id], location, False)
            except (requests.ConnectionError, requests.Timeout):
                uid = None
                self.queue.create_reminder(reminder_id)

            if uid is not None:
                self.reminders[reminder_id]['uid'] = uid
                self._save_reminders()
        except Exception as error:
            self.emit_error(error)

    def _do_remote_update_reminder(self, reminder_id, location, old_user_id, old_list_id, old_task_id, updating):
        try:
            try:
                self.queue.load()
                uid = self._to_remote_task(self.reminders[reminder_id], location, updating, old_user_id, old_list_id, old_task_id)
            except (requests.ConnectionError, requests.Timeout):
                uid = None
                self.queue.update_reminder(reminder_id, old_task_id, old_user_id, old_list_id, updating)

            if uid is not None:
                self.reminders[reminder_id]['uid'] = uid
                self._save_reminders()
        except Exception as error:
            self.emit_error(error)

    def _do_remote_update_completed(self, reminder_id, reminder_dict):
        try:
            try:
                self.queue.load()
                self._remote_set_completed(reminder_id, reminder_dict)
            except (requests.ConnectionError, requests.Timeout):
                self.queue.update_completed(reminder_id)
        except Exception as error:
            self.emit_error(error)

    def _do_remote_remove_reminder(self, reminder_id, task_id, user_id, task_list):
        try:
            try:
                self.queue.load()
                self._remote_remove_task(user_id, task_list, task_id)
            except (requests.ConnectionError, requests.Timeout):
                self.queue.remove_reminder(reminder_id, task_id, user_id, task_list)
        except Exception as error:
            self.emit_error(error)

    def _do_remote_create_list(self, user_id, list_name, list_id):
        try:
            uid = None
            try:
                self.queue.load()
                uid = self._remote_create_list(user_id, list_name)
            except (requests.ConnectionError, requests.Timeout):
                self.queue.add_list(list_id)

            self.list_ids[list_id] = {
                'uid': '' if uid is None else uid,
                'user-id': user_id
            }
            self._save_list_ids()
        except Exception as error:
            self.emit_error(error)

    def _do_remote_rename_list(self, user_id, new_name, list_id):
        try:
            try:
                self.queue.load()
                uid = self.list_ids[list_id]['uid']
                self._remote_rename_list(user_id, uid, new_name)
            except (requests.ConnectionError, requests.Timeout):
                self.queue.update_list(list_id)
        except Exception as error:
            self.emit_error(error)

    def _do_remote_delete_list(self, user_id, list_id):
        try:
            try:
                uid = self.list_ids[list_id]['uid']
            except:
                uid = ''
            try:
                self.queue.load()
                self._remote_delete_list(user_id, uid)
            except (requests.ConnectionError, requests.Timeout):
                self.queue.remove_list(list_id, uid, user_id)
            self.list_ids.pop(list_id)
            self._save_list_ids()
        except Exception as error:
            self.emit_error(error)

    def _remote_remove_task(self, user_id, task_list, task_id):
        if user_id in self.to_do.users.keys():
            self.to_do.remove_task(user_id, task_list, task_id)
        elif user_id in self.caldav.users.keys():
            self.caldav.remove_task(user_id, task_list, task_id)
        else:
            raise KeyError('Invalid user id')

    def _remote_create_list(self, user_id, list_name):
        if user_id in self.to_do.users.keys():
            return self.to_do.create_list(user_id, list_name)
        elif user_id in self.caldav.users.keys():
            return self.caldav.create_list(user_id, list_name)
        else:
            raise KeyError('Invalid user id')

    def _remote_rename_list(self, user_id, list_id, list_name):
        if user_id in self.to_do.users.keys():
            self.to_do.update_list(user_id, list_id, list_name)
        elif user_id in self.caldav.users.keys():
            self.caldav.update_list(user_id, list_id, list_name)
        else:
            raise KeyError('Invalid user id')

    def _remote_delete_list(self, user_id, list_id):
        if user_id in self.to_do.users.keys():
            self.to_do.delete_list(user_id, list_id)
        elif user_id in self.caldav.users.keys():
            self.caldav.delete_list(user_id, list_id)
        else:
            raise KeyError('Invalid user id')

    def _remote_set_completed(self, reminder_id, reminder_dict):
        if reminder_dict['user-id'] in self.to_do.users.keys():
            self._ms_set_completed(reminder_id, reminder_dict)
        elif reminder_dict['user-id'] in self.caldav.users.keys():
            self._caldav_set_completed(reminder_id, reminder_dict)

    def _ms_set_completed(self, reminder_id, reminder):
        reminder_json = {}
        reminder_json['status'] = 'completed' if reminder['completed'] else 'notStarted'

        list_id = reminder['list-id']
        user_id = reminder['user-id']
        list_uid = self.list_ids[list_id]['uid']
        results = self.to_do.update_task(user_id, list_uid, reminder['uid'], reminder_json)

        try:
            if reminder_json['status'] == 'completed' and results['status'] != 'completed':
                # this sucks but microsofts api is goofy and this is the only way I can get the new uid of the reminder that was completed
                updated_timestamp = self._rfc_to_timestamp(results['lastModifiedDateTime'])
                match_diff = None
                new_uid = ''
                for task in self.to_do.get_tasks(list_uid, user_id):
                    if task['id'] == results['id']:
                        continue
                    timestamp = self._rfc_to_timestamp(task['lastModifiedDateTime'])
                    diff = abs(updated_timestamp - timestamp)
                    if match_diff is None or diff < match_diff:
                        match_diff = diff
                        new_uid = task['id']

                reminder = self.to_do.task_to_reminder(results, list_id, user_id)
                new_id = self._do_generate_id()
                self.reminders[reminder_id]['uid'] = new_uid
                self.reminders[new_id] = reminder
                self._set_countdown(new_id)
                self._reminder_updated(info.service_id, new_id, reminder)
                self._save_reminders()
        except:
            pass

    def _caldav_set_completed(self, reminder_id, reminder):
        list_id = reminder['list-id']
        user_id = reminder['user-id']
        task_id = reminder['uid']

        list_uid = self.list_ids[list_id]['uid']

        if reminder['completed']:
            new_uid, task = self.caldav.complete_task(user_id, list_uid, task_id)
            if new_uid is not None:
                new_reminder = self.caldav.task_to_reminder(task, list_id, user_id)
                new_id = self._do_generate_id()
                self.reminders[reminder_id]['uid'] = new_uid
                self.reminders[new_id] = new_reminder
                self._set_countdown(new_id)
                self._reminder_updated(info.service_id, new_id, new_reminder)
                self._save_reminders()
        else:
            self.caldav.incomplete_task(user_id, list_uid, task_id)

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

    def _do_generate_id(self):
        return str(uuid.uuid1())

    def _remove_countdown(self, reminder_id):
        self.countdowns.remove_countdown(reminder_id)

    def _set_countdown(self, reminder_id):
        self.countdowns.remove_countdown(reminder_id)

        reminder = self.reminders[reminder_id]
        if reminder['timestamp'] == 0:
            return

        if reminder['completed'] or reminder['shown']:
            return

        def do_show_notification():
            self.show_notification(reminder_id)
            return False

        self.countdowns.add_countdown(reminder['timestamp'], do_show_notification, reminder_id)

    def show_notification(self, reminder_id):
        notification = Gio.Notification.new(self.reminders[reminder_id]['title'])
        notification.set_body(self.reminders[reminder_id]['description'])
        notification.add_button_with_target(_('Mark as completed'), 'app.reminder-completed', GLib.Variant('s', reminder_id))
        notification.set_default_action('app.notification-clicked')

        self.app.send_notification(reminder_id, notification)
        if self.app.settings.get_boolean('notification-sound') and not self.playing_sound:
            self.playing_sound = True
            if self.app.settings.get_boolean('included-notification-sound'):
                self.sound.play_full({GSound.ATTR_MEDIA_FILENAME: f'{GLib.get_system_data_dirs()[0]}/sounds/{info.app_executable}/notification.ogg'}, None, self._sound_cb)
            else:
                self.sound.play_full({GSound.ATTR_EVENT_ID: 'bell'}, None, self._sound_cb)
        self._shown(reminder_id)
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
            reminder_datetime = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

        repeat_until_date = datetime.datetime.fromtimestamp(repeat_until, tz=datetime.timezone.utc).date()

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
            starts_sunday = self.app.settings.get_boolean('week-starts-sunday')
            week_frequency = 0

            if not starts_sunday:
                weekday = reminder_datetime.date().weekday()
            else:
                weekday = (reminder_datetime.date().weekday() + 1) % 7

            if repeat_days == 0:
                repeat_days = weekday

            repeat_days_flag = info.RepeatDays(repeat_days)
            index = 0
            days = []
            if not starts_sunday:
                flags = (
                    info.RepeatDays.MON,
                    info.RepeatDays.TUE,
                    info.RepeatDays.WED,
                    info.RepeatDays.THU,
                    info.RepeatDays.FRI,
                    info.RepeatDays.SAT,
                    info.RepeatDays.SUN
                )
            else:
                flags = (
                    info.RepeatDays.SUN,
                    info.RepeatDays.MON,
                    info.RepeatDays.TUE,
                    info.RepeatDays.WED,
                    info.RepeatDays.THU,
                    info.RepeatDays.FRI,
                    info.RepeatDays.SAT
                )

            for num, flag in enumerate(flags):
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

                if not starts_sunday:
                    weekday = reminder_datetime.date().weekday()
                else:
                    weekday = (reminder_datetime.date().weekday() + 1) % 7

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

    def _shown(self, reminder_id):
        if not self.reminders[reminder_id]['shown'] > 0:
            self.reminders[reminder_id]['shown'] = True
            self._save_reminders()

    def _save_reminders(self):
        with open(REMINDERS_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['id'] + list(info.reminder_defaults.keys()))
            writer.writeheader()

            for reminder_id, reminder in self.reminders.items():
                writer.writerow({
                    'id': reminder_id,
                    'title': reminder['title'],
                    'description': reminder['description'],
                    'due-date': reminder['due-date'],
                    'timestamp': reminder['timestamp'],
                    'shown': reminder['shown'],
                    'completed': reminder['completed'],
                    'important': reminder['important'],
                    'repeat-type': reminder['repeat-type'],
                    'repeat-frequency': reminder['repeat-frequency'],
                    'repeat-days': reminder['repeat-days'],
                    'repeat-times': reminder['repeat-times'],
                    'repeat-until': reminder['repeat-until'],
                    'created-timestamp': reminder['created-timestamp'],
                    'updated-timestamp': reminder['updated-timestamp'],
                    'list-id': reminder['list-id'],
                    'user-id': reminder['user-id'],
                    'uid': reminder['uid']
                })

    def _save_lists(self):
        with open(TASK_LISTS_FILE, 'w', newline='') as jsonfile:
            json.dump(self.lists, jsonfile)

    def _save_list_ids(self):
        with open(TASK_LIST_IDS_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['list-id', 'uid', 'user-id'])
            writer.writeheader()

            for list_id in self.list_ids.keys():
                writer.writerow({
                    'list-id': list_id,
                    'uid': self.list_ids[list_id]['uid'],
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
            retval = info.reminder_defaults[key] if key in info.reminder_defaults.keys() else 0
        return retval

    def _get_str(self, row, key, old = None):
        try:
            retval = str(row[key])
        except:
            if old is None:
                retval = info.reminder_defaults[key] if key in info.reminder_defaults.keys() else ''
            else:
                retval = row[old] if old in row.keys() else ''
        return retval

    def _get_reminders(self, notify_past = True, only_user_id = None):
        reminders = {}
        list_ids = {}
        all_lists = {}
        remote_lists = {}
        lists = {}

        try:
            if os.path.isfile(TASK_LISTS_FILE):
                with open(TASK_LISTS_FILE, newline='') as jsonfile:
                    all_lists = json.load(jsonfile)
        except:
            pass

        remote_lists = all_lists.copy()
        if 'local' in remote_lists.keys():
            remote_lists.pop('local')

        if 'local' not in all_lists.keys():
            all_lists['local'] = {}
        if 'local' not in all_lists['local'].keys():
            all_lists['local']['local'] = _('Local Reminders')

        lists['local'] = all_lists['local']

        if os.path.isfile(REMINDERS_FILE):
            with open(REMINDERS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    reminder_id = row['id']

                    user_id = self._get_str(row, 'user-id')
                    if user_id not in all_lists.keys():
                        continue

                    list_id = self._get_str(row, 'list-id')
                    if list_id not in all_lists[user_id].keys():
                        continue

                    repeat_type = self._get_int(row, 'repeat-type')
                    repeat_times = self._get_int(row, 'repeat-times')

                    old_shown = repeat_times == 0

                    reminders[reminder_id] = Reminder()
                    reminders[reminder_id]['title'] = self._get_str(row, 'title')
                    reminders[reminder_id]['description'] = self._get_str(row, 'description')
                    reminders[reminder_id]['due-date'] = self._get_int(row, 'due-date')
                    reminders[reminder_id]['timestamp'] = self._get_int(row, 'timestamp')
                    reminders[reminder_id]['shown'] = self._get_boolean(row, 'shown', old_shown)
                    reminders[reminder_id]['completed'] = self._get_boolean(row, 'completed')
                    reminders[reminder_id]['important'] = self._get_boolean(row, 'important')
                    reminders[reminder_id]['repeat-type'] = repeat_type
                    reminders[reminder_id]['created-timestamp'] = self._get_int(row, 'created-timestamp')
                    reminders[reminder_id]['updated-timestamp'] = self._get_int(row, 'updated-timestamp')
                    reminders[reminder_id]['list-id'] = list_id
                    reminders[reminder_id]['user-id'] = user_id
                    reminders[reminder_id]['uid'] = self._get_str(row, 'uid')

                    if repeat_type != 0:
                        reminders[reminder_id]['repeat-frequency'] = self._get_int(row, 'repeat-frequency')
                        reminders[reminder_id]['repeat-days'] = self._get_int(row, 'repeat-days')
                        reminders[reminder_id]['repeat-until'] = self._get_int(row, 'repeat-until')
                        reminders[reminder_id]['repeat-times'] = repeat_times

        if os.path.isfile(TASK_LIST_IDS_FILE):
            with open(TASK_LIST_IDS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    list_ids[row['list-id']] = {
                        'uid': self._get_str(row, 'uid', 'ms-id'),
                        'user-id': self._get_str(row, 'user-id')
                    }

        reminders, remote_lists, list_ids = self._sync_remote(reminders, remote_lists, list_ids, notify_past, only_user_id)
        lists.update(remote_lists)

        return reminders, lists, list_ids

    def _to_remote_task(self, reminder, location, updating, old_user_id = None, old_list_id = None, old_task_id = None):
        user_id = reminder['user-id']
        task_list = reminder['list-id']
        list_id = self.list_ids[task_list]['uid'] if task_list in self.list_ids.keys() else None
        task_id = reminder['uid']
        moving = old_list_id not in (None, list_id) or old_task_id not in (None, task_id)

        new_task_id = None

        if location == 'ms-to-do':
            task = self.to_do.reminder_to_task(reminder)
            if updating:
                self.to_do.update_task(user_id, list_id, task_id, task)
            else:
                new_task_id = self.to_do.create_task(user_id, list_id, task)
        elif location == 'caldav':
            task = self.caldav.reminder_to_task(reminder)
            if updating:
                self.caldav.update_task(user_id, list_id, task_id, task)
            else:
                new_task_id = self.caldav.create_task(user_id, list_id, task)

        if moving:
            if old_user_id is None:
                old_user_id = user_id
            if old_user_id in self.to_do.users.keys():
                self.to_do.remove_task(old_user_id, old_list_id, old_task_id)
            elif old_user_id in self.caldav.users.keys():
                self.caldav.remove_task(old_user_id, old_list_id, old_task_id)

        return new_task_id

    # Below methods can be accessed by other apps over dbus
    def update_completed(self, app_id: str, reminder_id: str, completed: bool):
        now = floor(time.time())
        if reminder_id in self.reminders.keys():
            self.reminders[reminder_id]['completed'] = completed
            self.reminders[reminder_id]['updated-timestamp'] = now
            self._save_reminders()

            reminder_dict = self.reminders[reminder_id]

            if reminder_dict['user-id'] != 'local':
                GLib.idle_add(lambda *args: self._do_remote_update_completed(reminder_id, reminder_dict))

            if completed:
                self.app.withdraw_notification(reminder_id)
                self._remove_countdown(reminder_id)
                if reminder_dict['user-id'] == 'local' and reminder_dict['repeat-type'] != 0 and reminder_dict['repeat-times'] != 0:
                    try:
                        new_dict = reminder_dict.copy()
                        new_dict['timestamp'], new_dict['due-date'], new_dict['repeat-times'] = self._repeat(reminder_dict)
                        new_dict['completed'] = False
                        new_id = self._do_generate_id()
                        self.reminders[new_id] = new_dict
                        self._set_countdown(new_id)
                        self._reminder_updated(info.service_id, new_id, new_dict)
                        self._save_reminders()
                    except:
                        pass
            else:
                self._set_countdown(reminder_id)

            self.do_emit('CompletedUpdated', GLib.Variant('(ssbu)', (app_id, reminder_id, completed, now)))

        return GLib.Variant('(u)', (now,))

    def remove_reminder(self, app_id: str, reminder_id: str):
        self.app.withdraw_notification(reminder_id)
        self._remove_countdown(reminder_id)

        if reminder_id in self.reminders:
            if self.reminders[reminder_id]['user-id'] != 'local':
                task_id = self.reminders[reminder_id]['uid']
                user_id = self.reminders[reminder_id]['user-id']
                task_list = self.list_ids[self.reminders[reminder_id]['list-id']]['uid']
                GLib.idle_add(lambda *args: self._do_remote_remove_reminder(reminder_id, task_id, user_id, task_list))
            self.reminders.pop(reminder_id)
            self._save_reminders()

        self.do_emit('ReminderRemoved', GLib.Variant('(ss)', (app_id, reminder_id)))

    def create_reminder(self, app_id: str, **kwargs):
        reminder_id = self._do_generate_id()

        reminder_dict = Reminder()

        for i in ('title', 'description', 'list-id', 'user-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'due-date'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        if reminder_dict['user-id'] == 'local':
            location = 'local'
        elif reminder_dict['user-id'] in self.to_do.users.keys():
            location = 'ms-to-do'
        elif reminder_dict['user-id'] in self.caldav.users.keys():
            location = 'caldav'
        else:
            raise KeyError('Invalid user id')

        try:
            list_name = self.lists[reminder_dict['user-id']][reminder_dict['list-id']]
        except KeyError:
            raise KeyError('Invalid list id')

        if 'repeat-type' in kwargs.keys():
            repeat_type = int(kwargs['repeat-type'])
            if location != 'ms-to-do' or repeat_type not in (1, 2):
                reminder_dict['repeat-type'] = repeat_type

        for i in ('repeat-frequency', 'repeat-days'):
            if reminder_dict['repeat-type'] != 0 and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        for i in ('repeat-times', 'repeat-until'):
            if reminder_dict['repeat-type'] != 0 and location != 'ms-to-do' and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        if 'important' in kwargs.keys():
            reminder_dict['important'] = bool(kwargs['important'])

        if reminder_dict['timestamp'] != 0:
            notif_date = datetime.date.fromtimestamp(reminder_dict['timestamp'])
            due_date = datetime.datetime.fromtimestamp(reminder_dict['due-date'], tz=datetime.timezone.utc).date()
            if notif_date != due_date:
                # due date has to be the same day as the reminder date
                reminder_dict['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())

        now = floor(time.time())
        reminder_dict['created-timestamp'] = now
        reminder_dict['updated-timestamp'] = now

        self.reminders[reminder_id] = reminder_dict
        self._set_countdown(reminder_id)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders()

        GLib.idle_add(lambda *args: self._do_remote_create_reminder(reminder_id, location))

        return GLib.Variant('(su)', (reminder_id, now))

    def update_reminder(self, app_id: str, **kwargs):
        reminder_id = str(kwargs['id'])

        reminder_dict = self.reminders[reminder_id].copy()

        for i in ('title', 'description', 'list-id', 'user-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'due-date'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        if reminder_dict['user-id'] == 'local':
            location = 'local'
        elif reminder_dict['user-id'] in self.to_do.users.keys():
            location = 'ms-to-do'
        elif reminder_dict['user-id'] in self.caldav.users.keys():
            location = 'caldav'
        else:
            raise KeyError('Invalid user id')

        try:
            list_name = self.lists[reminder_dict['user-id']][reminder_dict['list-id']]
        except KeyError:
            raise KeyError('Invalid list id')

        if 'repeat-type' in kwargs.keys():
            repeat_type = int(kwargs['repeat-type'])
            reminder_dict['repeat-type'] = 0 if location == 'ms-to-do' and repeat_type in (1, 2) else repeat_type

        for i in ('repeat-frequency', 'repeat-days'):
            if reminder_dict['repeat-type'] != 0 and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])
            else:
                reminder_dict.set_default(i)

        for i in ('repeat-times', 'repeat-until'):
            if reminder_dict['repeat-type'] != 0 and location != 'ms-to-do' and i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])
            else:
                reminder_dict.set_default(i)

        if 'important' in kwargs.keys():
            reminder_dict['important'] = bool(kwargs['important'])

        now = floor(time.time())
        reminder_dict['updated-timestamp'] = now

        if reminder_dict['timestamp'] > floor(time.time()):
            reminder_dict['shown'] = False

        if reminder_dict['timestamp'] != 0:
            notif_date = datetime.date.fromtimestamp(reminder_dict['timestamp'])
            due_date = datetime.datetime.fromtimestamp(reminder_dict['due-date'], tz=datetime.timezone.utc).date()
            if notif_date != due_date:
                # due date has to be the same day as the reminder date
                reminder_dict['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())

        old_list_id = None
        old_task_id = None
        old_user_id = None
        updating = True
        if self.reminders[reminder_id]['list-id'] != reminder_dict['list-id'] or self.reminders[reminder_id]['user-id'] != reminder_dict['user-id']:
            updating = False
            reminder_dict['uid'] = ''
            if self.reminders[reminder_id]['user-id'] != 'local':
                old_list_id = self.list_ids[self.reminders[reminder_id]['list-id']]['uid'] if self.reminders[reminder_id]['list-id'] in self.list_ids.keys() else None
                old_task_id = self.reminders[reminder_id]['uid']
                old_user_id = self.reminders[reminder_id]['user-id']

        self.reminders[reminder_id] = reminder_dict

        self._set_countdown(reminder_id)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders()

        GLib.idle_add(lambda *args: self._do_remote_update_reminder(reminder_id, location, old_user_id, old_list_id, old_task_id, updating))

        return GLib.Variant('(u)', (now,))

    def get_reminders_in_list(self, user_id: str, list_id: str):
        array = []

        for reminder_id, reminder in self.reminders.items():
            if reminder['user-id'] != user_id:
                continue
            if reminder['list-id'] != list_id:
                continue
            array.append({
                'id': GLib.Variant('s', reminder_id),
                'title': GLib.Variant('s', reminder['title']),
                'description': GLib.Variant('s', reminder['description']),
                'due-date': GLib.Variant('u', reminder['due-date']),
                'timestamp': GLib.Variant('u', reminder['timestamp']),
                'shown': GLib.Variant('b', reminder['shown']),
                'completed': GLib.Variant('b', reminder['completed']),
                'important': GLib.Variant('b', reminder['important']),
                'repeat-type': GLib.Variant('q', reminder['repeat-type']),
                'repeat-frequency': GLib.Variant('q', reminder['repeat-frequency']),
                'repeat-days': GLib.Variant('q', reminder['repeat-days']),
                'repeat-times': GLib.Variant('n', reminder['repeat-times']),
                'repeat-until': GLib.Variant('u', reminder['repeat-until']),
                'created-timestamp': GLib.Variant('u', reminder['created-timestamp']),
                'updated-timestamp': GLib.Variant('u', reminder['updated-timestamp']),
                'list-id': GLib.Variant('s', reminder['list-id']),
                'user-id': GLib.Variant('s', reminder['user-id']),
            })

        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))
        return GLib.Variant('(aa{sv})', ([{}]))

    def get_reminders(self, ids = None, return_variant = True):
        array = []

        for reminder_id, reminder in self.reminders.items():
            if ids is not None and reminder_id not in ids:
                continue
            array.append({
                'id': GLib.Variant('s', reminder_id),
                'title': GLib.Variant('s', reminder['title']),
                'description': GLib.Variant('s', reminder['description']),
                'due-date': GLib.Variant('u', reminder['due-date']),
                'timestamp': GLib.Variant('u', reminder['timestamp']),
                'shown': GLib.Variant('b', reminder['shown']),
                'completed': GLib.Variant('b', reminder['completed']),
                'important': GLib.Variant('b', reminder['important']),
                'repeat-type': GLib.Variant('q', reminder['repeat-type']),
                'repeat-frequency': GLib.Variant('q', reminder['repeat-frequency']),
                'repeat-days': GLib.Variant('q', reminder['repeat-days']),
                'repeat-times': GLib.Variant('n', reminder['repeat-times']),
                'repeat-until': GLib.Variant('u', reminder['repeat-until']),
                'created-timestamp': GLib.Variant('u', reminder['created-timestamp']),
                'updated-timestamp': GLib.Variant('u', reminder['updated-timestamp']),
                'list-id': GLib.Variant('s', reminder['list-id']),
                'user-id': GLib.Variant('s', reminder['user-id']),
            })

        if not return_variant:
            return array
        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))
        return GLib.Variant('(aa{sv})', ([{}]))

    def get_version(self):
        return GLib.Variant('(s)', (VERSION,))

    def create_list(self, app_id, user_id, list_name, variant = True):
        if user_id in self.lists:
            list_id = self._do_generate_id()

            if user_id != 'local':
                if user_id not in self.synced_ids:
                    self.synced_ids[user_id] = []
                if 'all' not in self.synced_ids[user_id]:
                    self.synced_ids[user_id].append(list_id)
                    self._set_synced_lists_no_refresh(self.synced_ids)
                GLib.idle_add(lambda *args: self._do_remote_create_list(user_id, list_name, list_id))

            self.lists[user_id][list_id] = list_name
            self._save_lists()
            self.do_emit('ListUpdated', GLib.Variant('(ssss)', (app_id, user_id, list_id, list_name)))
            if variant:
                return GLib.Variant('(s)', (list_id,))
            else:
                return list_id
        else:
            raise KeyError('Invalid User ID')

    def rename_list(self, app_id, user_id, list_id, new_name):
        if user_id in self.lists and list_id in self.lists[user_id]:
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._do_remote_rename_list(user_id, new_name, list_id))
            self.lists[user_id][list_id] = new_name
            self._save_lists()
            self.do_emit('ListUpdated', GLib.Variant('(ssss)', (app_id, user_id, list_id, new_name)))

    def delete_list(self, app_id, user_id, list_id):
        if list_id == user_id:
            raise Exception('Tried to remove default list')
        if user_id in self.lists and list_id in self.lists[user_id]:
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._do_remote_delete_list(user_id, list_id))
            self.lists[user_id].pop(list_id)
            self._save_lists()
            self.do_emit('ListRemoved', GLib.Variant('(sss)', (app_id, user_id, list_id)))
            GLib.idle_add(lambda *args: self.refresh(only_user_id=user_id))

    def get_todo_login_url(self):
        url = self.to_do.get_login_url()
        return GLib.Variant('(s)', (url,))

    def login_caldav(self, name: str, url: str, username: str, password: str):
        user_id = self.caldav.login(name, url, username, password)
        self.synced_ids[user_id] = ['all']
        self._set_synced_lists_no_refresh(self.synced_ids)
        self.do_emit('CalDAVSignedIn', GLib.Variant('(ss)', (user_id, name)))
        GLib.idle_add(lambda *args: self.refresh(False, user_id))

    def caldav_update_username(self, user_id, username):
        self.caldav.users[user_id]['name'] = username
        self.caldav.store()
        self.do_emit('UsernameUpdated', GLib.Variant('(ss)', (user_id, username)))

    def logout(self, user_id: str):
        if user_id in self.to_do.users.keys():
            self.to_do.logout(user_id)
        elif user_id in self.caldav.users.keys():
            self.caldav.logout(user_id)
        else:
            raise KeyError('Invalid user id')

        if user_id in self.synced_ids:
            self.synced_ids.pop(user_id)
            self._set_synced_lists_no_refresh(self.synced_ids)
        self.do_emit('SignedOut', GLib.Variant('(s)', (user_id,)))
        GLib.idle_add(lambda *args: self.refresh(only_user_id=user_id))

    def refresh_user(self, user_id):
        self.refresh(only_user_id=user_id)

    def refresh(self, notify_past = True, only_user_id = None):
        if self.refreshing:
            return
        self.refreshing = True
        try:
            if only_user_id is None: # if only refreshing one user don't reset the timeout
                self.countdowns.add_timeout(self.refresh_time, self._refresh_cb, 'refresh')

            reminders, list_names, list_ids = self._get_reminders(notify_past, only_user_id)

            new_ids = []
            removed_ids = []
            for reminder_id, reminder in reminders.items():
                if reminder_id not in self.reminders.keys() or reminder != self.reminders[reminder_id]:
                    new_ids.append(reminder_id)
            for reminder_id in self.reminders.keys():
                if reminder_id not in reminders.keys():
                    removed_ids.append(reminder_id)

            for user_id, value in list_names.items():
                for list_id, list_name in value.items():
                    if user_id not in self.lists or list_id not in self.lists[user_id] or self.lists[user_id][list_id] != list_names[user_id][list_id]:
                        self.do_emit('ListUpdated', GLib.Variant('(ssss)', (info.service_id, user_id, list_id, list_name)))

            for user_id, value in self.lists.items():
                for list_id in value.keys():
                    if user_id not in list_names or list_id not in list_names[user_id]:
                        self.do_emit('ListRemoved', GLib.Variant('(sss)', (info.service_id, user_id, list_id)))

            if list_names != self.lists:
                self.lists = list_names
                self._save_lists()

            if list_ids != self.list_ids:
                self.list_ids = list_ids
                self._save_list_ids()

            if self.reminders != reminders:
                self.reminders = reminders
                self._save_reminders()

            try:
                self.queue.load()
            except:
                pass

            if len(new_ids) > 0 or len(removed_ids) > 0:
                new_reminders = self.get_reminders(ids=new_ids, return_variant=False)

                self.do_emit('Refreshed', GLib.Variant('(aa{sv}as)', (new_reminders, removed_ids)))

                for reminder_id in new_ids:
                    self._set_countdown(reminder_id)
                for reminder_id in removed_ids:
                    self._remove_countdown(reminder_id)

        except Exception as error:
            logger.exception(error)
        self.refreshing = False

    def get_lists(self):
        return GLib.Variant('(a{sa{ss}})', (self.lists,))

    def set_synced_lists(self, **lists):
        variant = GLib.Variant('a{sas}', lists)

        self.app.settings.set_value('synced-task-lists', variant)

    def get_synced_lists(self):
        lists = self.app.settings.get_value('synced-task-lists').unpack()
        return GLib.Variant('(a{sas})', (lists,))

    def get_week_start(self):
        starts_sunday = self.app.settings.get_boolean('week-starts-sunday')
        return GLib.Variant('(b)', (starts_sunday,))

    def set_week_start(self, starts_sunday: bool):
        self.app.settings.set_boolean('week-starts-sunday', starts_sunday)

    def get_users(self):
        usernames = {
            'local': {
                'local': _('Local')
            }
        }
        usernames['ms-to-do'] = {}
        for user_id in self.to_do.users.keys():
            usernames['ms-to-do'][user_id] = self.to_do.users[user_id]['email']

        usernames['caldav'] = {}
        for user_id in self.caldav.users.keys():
            usernames['caldav'][user_id] = self.caldav.users[user_id]['name']

        return GLib.Variant('(a{sa{ss}})', (usernames,))

    def export_lists(self, lists):
        folder = self.ical.to_ical(lists)
        return GLib.Variant('(s)', (folder,))

    def import_lists(self, files, user_id, list_id):
        if user_id == 'auto' or list_id == 'auto':
            new_reminders = self.ical.from_ical(files)
        else:
            new_reminders = self.ical.from_ical(files, user_id, list_id)

        self.do_emit('Refreshed', GLib.Variant('(aa{sv}as)', (new_reminders, [])))

    def caldav_get_users(self):
        usernames = {}
        logout = []

        for i in logout:
            self.logout(i)

        return GLib.Variant('(a{ss})', (usernames,))
