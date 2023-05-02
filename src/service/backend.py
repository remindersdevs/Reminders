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

import datetime

from gi import require_version
require_version('GSound', '1.0')
require_version('Secret', '1')

from gi.repository import GLib, Gio, GSound, Secret
from remembrance import info
from remembrance.service.ms_to_do import MSToDo
from remembrance.service.caldav import CalDAV
from remembrance.service.queue import ReminderQueue
from remembrance.service.countdowns import Countdowns
from remembrance.service.icalendar import iCalendar
from remembrance.service.reminder import Reminder

from gettext import gettext as _
from math import floor
from calendar import monthrange
from threading import Thread
from queue import Queue
from uuid import uuid1
from traceback import format_exception
from logging import getLogger
from time import time
from os import path, mkdir, remove, getpid
from json import load as load_json
from csv import DictReader, DictWriter
from requests import HTTPError, Timeout, ConnectionError

REMINDERS_FILE = f'{info.data_dir}/reminders.csv'
LISTS_FILE = f'{info.data_dir}/lists.csv'

# these are no longer used
MS_REMINDERS_FILE = f'{info.data_dir}/ms_reminders.csv'
TASK_LISTS_FILE = f'{info.data_dir}/task_lists.json'
TASK_LIST_IDS_FILE = f'{info.data_dir}/task_list_ids.csv'

VERSION = info.service_version
PID = getpid()

logger = getLogger(info.service_executable)

XML = f'''<node name="/">
<interface name="{info.service_interface}">
    <method name='GetUsers'>
        <arg name='usernames' direction='out' type='a{{sa{{ss}}}}'/>
    </method>
    <method name='GetLists'>
        <arg name='lists' direction='out' type='aa{{sv}}'/>
    </method>
    <method name='GetListsDict'>
        <arg name='lists' direction='out' type='a{{sa{{sv}}}}'/>
    </method>
    <method name='GetReminders'>
        <arg name='reminders' direction='out' type='aa{{sv}}'/>
    </method>
    <method name='GetRemindersDict'>
        <arg name='reminders' direction='out' type='a{{sa{{sv}}}}'/>
    </method>
    <method name='GetRemindersInList'>
        <arg name='list-id' type='s'/>
        <arg name='reminders' direction='out' type='aa{{sv}}'/>
    </method>
    <method name='GetSyncedLists'>
        <arg name='list-ids' direction='out' type='as'/>
    </method>
    <method name='SetSyncedLists'>
        <arg name='synced-lists' type='as'/>
    </method>
    <method name='GetWeekStart'>
        <arg name='week-start-sunday' direction='out' type='b'/>
    </method>
    <method name='SetWeekStart'>
        <arg name='week-start-sunday' type='b'/>
    </method>
    <method name='CreateList'>
        <arg name='app-id' type='s'/>
        <arg name='list' type='a{{sv}}'/>
        <arg name='list-id' direction='out' type='s'/>
    </method>
    <method name='UpdateList'>
        <arg name='app-id' type='s'/>
        <arg name='list' type='a{{sv}}'/>
    </method>
    <method name='RemoveList'>
        <arg name='app-id' type='s'/>
        <arg name='list-id' type='s'/>
    </method>
    <method name='CreateReminder'>
        <arg name='app-id' type='s'/>
        <arg name='reminder' type='a{{sv}}'/>
        <arg name='reminder-id' direction='out' type='s'/>
        <arg name='created-timestamp' direction='out' type='u'/>
    </method>
    <method name='UpdateReminder'>
        <arg name='app-id' type='s'/>
        <arg name='reminder' type='a{{sv}}'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
    </method>
    <method name='UpdateCompleted'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-id' type='s'/>
        <arg name='completed' type='b'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
        <arg name='completed-date' direction='out' type='u'/>
    </method>
    <method name='RemoveReminder'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-id' type='s'/>
    </method>
    <method name='UpdateReminderv'>
        <arg name='app-id' type='s'/>
        <arg name='reminders' type='aa{{sv}}'/>
        <arg name='updated-reminder-ids' direction='out' type='as'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
    </method>
    <method name='UpdateCompletedv'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-ids' type='as'/>
        <arg name='completed' type='b'/>
        <arg name='updated-reminder-ids' direction='out' type='as'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
        <arg name='completed-date' direction='out' type='u'/>
    </method>
    <method name='RemoveReminderv'>
        <arg name='app-id' type='s'/>
        <arg name='reminder-ids' type='as'/>
        <arg name='removed-reminder-ids' direction='out' type='as'/>
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
        <arg name='list-ids' type='as'/>
        <arg name='folder' direction='out' type='s'/>
    </method>
    <method name='ImportLists'>
        <arg name='ical-files' type='as'/>
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
        <arg name='lists' direction='out' type='as'/>
    </signal>
    <signal name='WeekStartChanged'>
        <arg name='week-start-sunday' direction='out' type='b'/>
    </signal>
    <signal name='ListUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='list' direction='out' type='a{{sv}}'/>
    </signal>
    <signal name='ListRemoved'>
        <arg name='app-id' direction='out' type='s'/>
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
        <arg name='completed-date' direction='out' type='u'/>
    </signal>
    <signal name='ReminderRemoved'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder-id' direction='out' type='s'/>
    </signal>
    <signal name='RemindersCompleted'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder-ids' direction='out' type='as'/>
        <arg name='completed' direction='out' type='b'/>
        <arg name='updated-timestamp' direction='out' type='u'/>
        <arg name='completed-date' direction='out' type='u'/>
    </signal>
    <signal name='RemindersUpdated'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminders' direction='out' type='aa{{sv}}'/>
    </signal>
    <signal name='RemindersRemoved'>
        <arg name='app-id' direction='out' type='s'/>
        <arg name='reminder-ids' direction='out' type='as'/>
    </signal>
    <signal name='MSSignedIn'>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='username' direction='out' type='s'/>
    </signal>
    <signal name='CalDAVSignedIn'>
        <arg name='user-id' direction='out' type='s'/>
        <arg name='display-name' direction='out' type='s'/>
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
        if not path.isdir(info.data_dir):
            mkdir(info.data_dir)
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.app = app
        self.reminders = self.lists = {}
        self.schema = Secret.Schema.new(
            info.app_id,
            Secret.SchemaFlags.NONE,
            { 'name': Secret.SchemaAttributeType.STRING }
        )
        self.refreshing = False
        self._regid = None
        self.playing_sound = False
        self.synced_ids = self.app.settings.get_value('synced-lists').unpack()
        self.to_do = MSToDo(self)
        self.caldav = CalDAV(self)
        self.ical = iCalendar(self)
        self.queue = ReminderQueue(self)
        self.synced_changed = self.app.settings.connect('changed::synced-lists', lambda *args: self._synced_task_list_changed())
        self.reminders, self.lists = self._get_reminders(migrate_old=True)
        self.sound = GSound.Context()
        self.sound.init()
        self.countdowns = Countdowns()
        self.refresh_time = int(self.app.settings.get_string('refresh-frequency').strip('m'))
        self.app.settings.connect('changed::refresh-frequency', lambda *args: self._refresh_time_changed())
        self.app.settings.connect('changed::week-starts-sunday', lambda *args: self._week_start_changed())
        try:
            self.queue.load()
        except:
            pass
        self._save_reminders()
        self._save_lists()
        self._methods = {
            'GetUsers': self.get_users,
            'GetLists': self.get_lists,
            'GetListsDict': self.get_lists_dict,
            'GetReminders': self.get_reminders,
            'GetRemindersDict': self.get_reminders_dict,
            'GetRemindersInList': self.get_reminders_in_list,
            'GetSyncedLists': self.get_synced_lists,
            'SetSyncedLists': self.set_synced_lists,
            'GetWeekStart': self.get_week_start,
            'SetWeekStart': self.set_week_start,
            'CreateList': self.create_list,
            'UpdateList': self.update_list,
            'RemoveList': self.remove_list,
            'CreateReminder': self.create_reminder,
            'UpdateReminder': self.update_reminder,
            'UpdateCompleted': self.update_completed,
            'RemoveReminder': self.remove_reminder,
            'UpdateReminderv': self.update_reminderv,
            'UpdateCompletedv': self.update_completedv,
            'RemoveReminderv': self.remove_reminderv,
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
        logger.error("".join(format_exception(error)))
        self.do_emit('Error', GLib.Variant('(s)', ("".join(format_exception(error)),)))

    def emit_login(self, user_id):
        username = self.to_do.users[user_id]['email']
        self.synced_ids.append(user_id)
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
        self.synced_ids = self.app.settings.get_value('synced-lists').unpack()
        self.do_emit('SyncedListsChanged', self.get_synced_lists())
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
            'list-id': GLib.Variant('s', reminder['list-id'])
        }

        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, variant)))

    def _list_updated(self, app_id, list_id, list_name, user_id):
        variant = {
            'id': GLib.Variant('s', list_id),
            'name': GLib.Variant('s', list_name),
            'user-id': GLib.Variant('s', user_id)
        }

        self.do_emit('ListUpdated', GLib.Variant('(sa{sv})', (app_id, variant)))

    def _set_synced_lists_no_refresh(self, lists):
        variant = GLib.Variant('as', lists)

        self.app.settings.disconnect(self.synced_changed)

        self.app.settings.set_value('synced-lists', variant)

        self.do_emit('SyncedListsChanged', self.get_synced_lists())

        self.synced_changed = self.app.settings.connect('changed::synced-lists', lambda *args: self._synced_task_list_changed())

    def _sync_remote(self, old_reminders, old_lists, notify_past, only_user_id):
        updated_reminder_ids = self.queue.get_updated_reminder_ids()
        removed_reminder_ids = self.queue.get_removed_reminder_ids()

        updated_list_ids = self.queue.get_updated_list_ids()
        removed_list_ids = self.queue.get_removed_list_ids()

        ms_lists, ms_not_synced = self.to_do.get_lists(removed_list_ids, old_lists, self.synced_ids, only_user_id)

        caldav_lists, caldav_not_synced = self.caldav.get_lists(removed_list_ids, old_lists, self.synced_ids, only_user_id)

        not_synced = ms_not_synced + caldav_not_synced

        if ms_lists is None:
            ms_lists = {}
        if caldav_lists is None:
            caldav_lists = {}

        new_lists = old_lists.copy()
        for list_id, value in old_lists.items():
            if value['user-id'] != 'local' and value['user-id'] not in not_synced:
                new_lists.pop(list_id)

        new_reminders = old_reminders.copy()
        for reminder_id, reminder in old_reminders.items():
            if reminder['list-id'] not in new_lists.keys():
                new_reminders.pop(reminder_id)

        for user_id in ms_lists.keys():
            for task_list in ms_lists[user_id]:
                list_id = task_list['id']

                new_lists[list_id] = {
                    'name': task_list['name'],
                    'user-id': user_id,
                    'uid': task_list['uid']
                }

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

                    is_future = timestamp > floor(time())

                    if reminder_id in old_reminders:
                        if reminder_id in updated_reminder_ids:
                            continue
                        reminder = old_reminders[reminder_id].copy()
                    else:
                        reminder = Reminder()
                        reminder['shown'] = timestamp != 0 and not (is_future or notify_past)

                    new_reminders[reminder_id] = self.to_do.task_to_reminder(task, list_id, reminder, timestamp)

        for user_id in caldav_lists.keys():
            for task_list in caldav_lists[user_id]:
                list_id = task_list['id']

                new_lists[list_id] = {
                    'name': task_list['name'],
                    'user-id': user_id,
                    'uid': task_list['uid']
                }

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

                    is_future = timestamp > floor(time())

                    if reminder_id in old_reminders:
                        if reminder_id in updated_reminder_ids:
                            continue
                        reminder = old_reminders[reminder_id].copy()
                    else:
                        reminder = Reminder()
                        reminder['shown'] = timestamp != 0 and not (is_future or notify_past)

                    new_reminders[reminder_id] = self.caldav.task_to_reminder(task.icalendar_component, list_id, reminder, timestamp, due_date)

        for reminder_id in updated_reminder_ids:
            if reminder_id in old_reminders.keys():
                new_reminders[reminder_id] = old_reminders[reminder_id].copy()

        for list_id in updated_list_ids:
            if list_id in old_lists.keys():
                new_lists[list_id] = old_lists[list_id].copy()

        return new_reminders, new_lists

    def _do_remote_create_reminder(self, reminder_id, location):
        try:
            uid = None
            try:
                self.queue.load()
                uid = self._to_remote_task(self.reminders[reminder_id], location, False)
            except (ConnectionError, Timeout):
                self.queue.create_reminder(reminder_id, location)
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.create_reminder(reminder_id, location)
                else:
                    raise error
            if uid is not None:
                self.reminders[reminder_id]['uid'] = uid
                self._save_reminders()
        except Exception as error:
            self.emit_error(error)

    def _do_remote_update_reminder(self, reminder_id, location, old_user_id, old_list_uid, old_uid, updating, old_list_id, save = True):
        try:
            uid = None
            try:
                self.queue.load()
                uid = self._to_remote_task(self.reminders[reminder_id], location, updating, old_user_id, old_list_uid, old_uid, self.reminders[reminder_id]['completed'], self.reminders[reminder_id]['completed-timestamp'], self.reminders[reminder_id]['completed-date'])
            except (ConnectionError, Timeout):
                self.queue.update_reminder(reminder_id, old_uid, old_user_id, old_list_uid, old_list_id, updating, self.reminders[reminder_id]['completed'], self.reminders[reminder_id]['completed-timestamp'], self.reminders[reminder_id]['completed-date'])
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.update_reminder(reminder_id, old_uid, old_user_id, old_list_uid, old_list_id, updating, self.reminders[reminder_id]['completed'], self.reminders[reminder_id]['completed-timestamp'], self.reminders[reminder_id]['completed-date'])
                else:
                    raise error
            if uid is not None:
                self.reminders[reminder_id]['uid'] = uid
                if save:
                    self._save_reminders()
        except Exception as error:
            self.reminders[reminder_id]['uid'] = old_uid
            self.reminders[reminder_id]['list-id'] = old_list_id
            if save:
                self._save_reminders()
            self.emit_error(error)

    def _do_remote_update_completed(self, reminder_id, reminder_dict):
        try:
            try:
                self.queue.load()
                self._remote_set_completed(reminder_id, reminder_dict)
            except (ConnectionError, Timeout):
                self.queue.update_completed(reminder_id)
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.update_completed(reminder_id)
                else:
                    raise error
        except Exception as error:
            self.emit_error(error)

    def _do_remote_remove_reminder(self, reminder_id, task_id, user_id, task_list):
        try:
            try:
                self.queue.load()
                self._remote_remove_task(user_id, task_list, task_id)
            except (ConnectionError, Timeout):
                self.queue.remove_reminder(reminder_id, task_id, user_id, task_list)
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.remove_reminder(reminder_id, task_id, user_id, task_list)
                else:
                    raise error
        except Exception as error:
            self.emit_error(error)

    def _do_remote_create_list(self, user_id, list_name, list_id):
        try:
            uid = None
            try:
                self.queue.load()
                uid = self._remote_create_list(user_id, list_name)
            except (ConnectionError, Timeout):
                self.queue.add_list(list_id)
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.add_list(list_id)
                else:
                    raise error
            self.lists[list_id]['uid'] = uid
            self._save_lists()
        except Exception as error:
            self.emit_error(error)

    def _do_remote_rename_list(self, user_id, list_id, new_name, uid):
        try:
            try:
                self.queue.load()
                self._remote_rename_list(user_id, uid, new_name)
            except (ConnectionError, Timeout):
                self.queue.update_list(list_id)
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.update_list(list_id)
                else:
                    raise error
        except Exception as error:
            self.emit_error(error)

    def _do_remote_delete_list(self, user_id, list_id, uid):
        try:
            try:
                self.queue.load()
                self._remote_delete_list(user_id, uid)
            except (ConnectionError, Timeout):
                self.queue.remove_list(list_id, uid, user_id)
            except HTTPError as error:
                if error.response.status_code == 503:
                    self.queue.remove_list(list_id, uid, user_id)
                else:
                    raise error
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
        user_id = self.lists[reminder_dict['list-id']]['user-id']
        if user_id in self.to_do.users.keys():
            self._ms_set_completed(reminder_id, reminder_dict)
        elif user_id in self.caldav.users.keys():
            self._caldav_set_completed(reminder_id, reminder_dict)
        else:
            raise KeyError('Invalid user id')

    def _ms_set_completed(self, reminder_id, reminder):
        reminder_json = {}
        reminder_json['status'] = 'completed' if reminder['completed'] else 'notStarted'

        if reminder['completed']:
            reminder_json['completedDateTime'] = {}
            reminder_json['completedDateTime']['dateTime'] = self._timestamp_to_rfc(reminder['completed-date'])
            reminder_json['completedDateTime']['timeZone'] = 'UTC'
        else:
            reminder_json['completedDateTime'] = None

        list_id = reminder['list-id']
        user_id = self.lists[reminder['list-id']]['user-id']
        list_uid = self.lists[list_id]['uid']
        results = self.to_do.update_task(user_id, list_uid, reminder['uid'], reminder_json)

        try:
            if reminder['completed'] and results['status'] != 'completed':
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

                reminder = self.to_do.task_to_reminder(results, list_id)
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
        user_id = self.lists[reminder['list-id']]['user-id']
        task_id = reminder['uid']

        list_uid = self.lists[list_id]['uid']
        completed_timestamp = reminder['completed-timestamp']

        if reminder['completed']:
            new_uid, task = self.caldav.complete_task(user_id, list_uid, task_id, completed_timestamp)
            if new_uid is not None:
                new_reminder = self.caldav.task_to_reminder(task, list_id)
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
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed', f'{error} - Method {method} failed to execute\n{"".join(format_exception(error))}')

    def _do_generate_id(self):
        return str(uuid1())

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
        self.do_emit('ReminderShown', GLib.Variant('(s)', (reminder_id,)))
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
            while ((timestamp < floor(time())) if notify else (reminder_datetime.date() < datetime.date.today())):
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
            while ((timestamp < floor(time())) if notify else (reminder_datetime.date() < datetime.date.today())):
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
            while ((timestamp < floor(time())) if notify else (reminder_datetime.date() < datetime.date.today())):
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                reminder_datetime = self._month_repeat(reminder_datetime, frequency)
                timestamp = reminder_datetime.timestamp()

        elif repeat_type == info.RepeatType.YEAR:
            reminder_datetime = self._year_repeat(reminder_datetime, frequency)
            timestamp = reminder_datetime.timestamp()
            while ((timestamp < floor(time())) if notify else (reminder_datetime.date() < datetime.date.today())):
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
            writer = DictWriter(csvfile, fieldnames=['id'] + list(info.reminder_defaults.keys()))
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
                    'completed-timestamp': reminder['completed-timestamp'],
                    'completed-date': reminder['completed-date'],
                    'list-id': reminder['list-id'],
                    'uid': reminder['uid']
                })

    def _save_lists(self):
        with open(LISTS_FILE, 'w', newline='') as csvfile:
            writer = DictWriter(csvfile, fieldnames=['id', 'name', 'user-id', 'uid'])
            writer.writeheader()

            for list_id, task_list in self.lists.items():
                writer.writerow({
                    'id': list_id,
                    'name': task_list['name'],
                    'user-id': task_list['user-id'],
                    'uid': task_list['uid']
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

    def _migrate_old(self, reminders, lists):
        old_lists = {}
        list_ids = {}
        synced = []

        if path.isfile(TASK_LISTS_FILE):
            try:
                with open(TASK_LISTS_FILE, newline='') as jsonfile:
                    old_lists = load_json(jsonfile)
            except:
                pass
            remove(TASK_LISTS_FILE)

        if path.isfile(TASK_LIST_IDS_FILE):
            try:
                with open(TASK_LIST_IDS_FILE, newline='') as csvfile:
                    reader = DictReader(csvfile)

                    for row in reader:
                        list_ids[row['list-id']] = {
                            'uid': self._get_str(row, 'uid', 'ms-id'),
                            'user-id': self._get_str(row, 'user-id')
                        }
            except:
                pass
            remove(TASK_LIST_IDS_FILE)

        for user_id, value in old_lists.items():
            for list_id, list_name in value.items():
                lists[list_id] = {
                    'name': list_name,
                    'user-id': user_id,
                    'uid': list_ids[list_id]['uid'] if list_id in list_ids.keys() else ''
                }

        if path.isfile(MS_REMINDERS_FILE):
            try:
                with open(MS_REMINDERS_FILE, newline='') as csvfile:
                    reader = DictReader(csvfile)
                    for row in reader:
                        repeat_times = self._get_int(row, 'repeat-times')
                        reminder_id = row['id']

                        old_shown = repeat_times == 0

                        reminders[reminder_id] = info.reminder_defaults.copy()
                        reminders[reminder_id]['title'] = self._get_str(row, 'title')
                        reminders[reminder_id]['description'] = self._get_str(row, 'description')
                        reminders[reminder_id]['due-date'] = self._get_int(row, 'due-date')
                        reminders[reminder_id]['timestamp'] = self._get_int(row, 'timestamp')
                        reminders[reminder_id]['shown'] = self._get_boolean(row, 'shown', old_shown)
                        reminders[reminder_id]['completed'] = self._get_boolean(row, 'completed')
                        reminders[reminder_id]['important'] = self._get_boolean(row, 'important')
                        reminders[reminder_id]['created-timestamp'] = self._get_int(row, 'created-timestamp')
                        reminders[reminder_id]['updated-timestamp'] = self._get_int(row, 'updated-timestamp')
                        reminders[reminder_id]['list-id'] = self._get_str(row, 'list-id')
                        reminders[reminder_id]['uid'] = self._get_str(row, 'ms-id')
            except:
                pass
            remove(MS_REMINDERS_FILE)

        old_synced = self.app.settings.get_value('synced-task-lists').unpack()
        for user_id, values in old_synced.items():
            for list_id in values:
                if list_id == 'all':
                    list_id = user_id

                if list_id not in self.synced_ids:
                    synced.append(user_id)

        self.app.settings.set_value('synced-task-lists', GLib.Variant('a{sas}', {}))

        if len(synced) != 0:
            self.synced_ids += synced
            self._set_synced_lists_no_refresh(self.synced_ids)

    def _get_reminders(self, notify_past = True, only_user_id = None, migrate_old = False):
        reminders = {}
        lists = {}

        try:
            if path.isfile(LISTS_FILE):
                with open(LISTS_FILE, newline='') as csvfile:
                    reader = DictReader(csvfile)

                    for row in reader:
                        try:
                            list_id = row['id']
                            user_id = row['user-id']
                            if user_id not in 'local' and user_id not in self.to_do.users.keys() and user_id not in self.caldav.users.keys():
                                continue
                            lists[list_id] = {
                                'name': row['name'],
                                'user-id': user_id,
                                'uid': row['uid']
                            }
                        except:
                            logger.exception(f'Something is wrong with {LISTS_FILE}')
        except:
            logger.exception(f'Something is wrong with {LISTS_FILE}')

        if 'local' not in lists.keys():
            lists['local'] = {
                'name': _('Local Reminders'),
                'user-id': 'local',
                'uid': ''
            }

        try:
            if path.isfile(REMINDERS_FILE):
                with open(REMINDERS_FILE, newline='') as csvfile:
                    reader = DictReader(csvfile)

                    for row in reader:
                        try:
                            reminder_id = row['id']

                            list_id = self._get_str(row, 'list-id')
                            if list_id not in lists.keys():
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
                            reminders[reminder_id]['completed-timestamp'] = self._get_int(row, 'completed-timestamp')
                            reminders[reminder_id]['completed-date'] = self._get_int(row, 'completed-date')
                            reminders[reminder_id]['list-id'] = list_id
                            reminders[reminder_id]['uid'] = self._get_str(row, 'uid')

                            if repeat_type != 0:
                                reminders[reminder_id]['repeat-frequency'] = self._get_int(row, 'repeat-frequency')
                                reminders[reminder_id]['repeat-days'] = self._get_int(row, 'repeat-days')
                                reminders[reminder_id]['repeat-until'] = self._get_int(row, 'repeat-until')
                                reminders[reminder_id]['repeat-times'] = repeat_times
                        except:
                            logger.exception(f'Something is wrong with {REMINDERS_FILE}')
        except:
            logger.exception(f'Something is wrong with {REMINDERS_FILE}')


        self._migrate_old(reminders, lists)

        reminders, lists = self._sync_remote(reminders, lists, notify_past, only_user_id)

        return reminders, lists

    def _to_remote_task(self, reminder, location, updating, old_user_id = None, old_list_id = None, old_task_id = None, completed = None, completed_timestamp = None, completed_date = None):
        list_id = reminder['list-id']
        user_id = self.lists[list_id]['user-id']
        list_uid = self.lists[list_id]['uid']
        task_id = reminder['uid']
        moving = old_list_id not in (None, list_uid) or old_task_id not in (None, task_id)

        new_task_id = None

        if location == 'ms-to-do':
            task = self.to_do.reminder_to_task(reminder, completed=completed, completed_date=completed_date)
            if updating:
                self.to_do.update_task(user_id, list_uid, task_id, task)
            else:
                new_task_id = self.to_do.create_task(user_id, list_uid, task)
        elif location == 'caldav':
            task = self.caldav.reminder_to_task(reminder, completed=completed, completed_timestamp=completed_timestamp)
            if updating:
                self.caldav.update_task(user_id, list_uid, task_id, task)
            else:
                new_task_id = self.caldav.create_task(user_id, list_uid, task)

        if moving:
            if old_user_id is None:
                old_user_id = user_id
            if old_user_id in self.to_do.users.keys():
                self.to_do.remove_task(old_user_id, old_list_id, old_task_id)
            elif old_user_id in self.caldav.users.keys():
                self.caldav.remove_task(old_user_id, old_list_id, old_task_id)

        return new_task_id

    # Below methods can be accessed by other apps over dbus
    def update_completed(self, app_id: str, reminder_id: str, completed: bool, now = None, today = None, save = True):
        if now is None:
            now = floor(time())

        if today is None:
            today = datetime.datetime.combine(datetime.date.fromtimestamp(now), datetime.time(), tzinfo=datetime.timezone.utc).timestamp()

        if reminder_id in self.reminders.keys():
            self.reminders[reminder_id]['completed'] = completed
            self.reminders[reminder_id]['updated-timestamp'] = now
            self.reminders[reminder_id]['completed-timestamp'] = now if completed else 0
            self.reminders[reminder_id]['completed-date'] = today if completed else 0

            reminder_dict = self.reminders[reminder_id]

            user_id = self.lists[self.reminders[reminder_id]['list-id']]['user-id']
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._do_remote_update_completed(reminder_id, reminder_dict))

            if completed:
                self.app.withdraw_notification(reminder_id)
                self._remove_countdown(reminder_id)
                if user_id == 'local' and reminder_dict['repeat-type'] != 0 and reminder_dict['repeat-times'] != 0:
                    try:
                        new_dict = reminder_dict.copy()
                        new_dict['timestamp'], new_dict['due-date'], new_dict['repeat-times'] = self._repeat(reminder_dict)
                        new_dict['completed'] = False
                        new_id = self._do_generate_id()
                        self.reminders[new_id] = new_dict
                        self._set_countdown(new_id)
                        self._reminder_updated(info.service_id, new_id, new_dict)
                    except:
                        pass
            else:
                self._set_countdown(reminder_id)

            if save:
                self.do_emit('CompletedUpdated', GLib.Variant('(ssbuu)', (app_id, reminder_id, completed, now, today)))
                self._save_reminders()

        return GLib.Variant('(uu)', (now, today))

    def update_completedv(self, app_id: str, reminder_ids: list, completed: bool):
        now = floor(time())
        today = datetime.datetime.combine(datetime.date.fromtimestamp(now), datetime.time(), tzinfo=datetime.timezone.utc).timestamp()
        threads = []
        queue = Queue()
        for reminder_id in reminder_ids:
            thread = UpdateThread(queue, reminder_id, target=self.update_completed, args=(app_id, reminder_id, completed, now, today, False))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        completed_ids = []
        while not queue.empty():
            value = queue.get()
            if isinstance(value, Exception):
                self.emit_error(value)
            else:
                completed_ids.append(value)

        if len(completed_ids) == 1:
            reminder_id = completed_ids[0]
            self.do_emit('CompletedUpdated', GLib.Variant('(ssbuu)', (app_id, reminder_id, completed, now, today)))
        elif len(completed_ids) > 1:
            self.do_emit('RemindersCompleted', GLib.Variant('(sasbuu)', (app_id, completed_ids, completed, now, today)))

        self._save_reminders()

        return GLib.Variant('(asuu)', (completed_ids, now, today))

    def remove_reminder(self, app_id: str, reminder_id: str, save = True):
        self.app.withdraw_notification(reminder_id)
        self._remove_countdown(reminder_id)

        if reminder_id in self.reminders:
            user_id = self.lists[self.reminders[reminder_id]['list-id']]['user-id']
            if user_id != 'local':
                task_id = self.reminders[reminder_id]['uid']
                task_list = self.lists[self.reminders[reminder_id]['list-id']]['uid']
                GLib.idle_add(lambda *args: self._do_remote_remove_reminder(reminder_id, task_id, user_id, task_list))
            self.reminders.pop(reminder_id)
            if save:
                self.do_emit('ReminderRemoved', GLib.Variant('(ss)', (app_id, reminder_id)))
                self._save_reminders()

    def remove_reminderv(self, app_id: str, reminder_ids: list):
        threads = []
        queue = Queue()
        for reminder_id in reminder_ids:
            thread = UpdateThread(queue, reminder_id, target=self.remove_reminder, args=(app_id, reminder_id, False))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        removed_ids = []
        while not queue.empty():
            value = queue.get()
            if isinstance(value, Exception):
                self.emit_error(value)
            else:
                removed_ids.append(value)

        if len(removed_ids) == 1:
            reminder_id = removed_ids[0]
            self.do_emit('ReminderRemoved', GLib.Variant('(ss)', (app_id, reminder_id)))
        elif len(removed_ids) > 1:
            self.do_emit('RemindersRemoved', GLib.Variant('(sas)', (app_id, removed_ids)))

        self._save_reminders()

        return GLib.Variant('(as)', (removed_ids,))

    def create_reminder(self, app_id: str, **kwargs):
        reminder_id = self._do_generate_id()

        reminder_dict = Reminder()

        for i in ('title', 'description', 'list-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'due-date'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        user_id = self.lists[reminder_dict['list-id']]['user-id']
        if user_id == 'local':
            location = 'local'
        elif user_id in self.to_do.users.keys():
            location = 'ms-to-do'
        elif user_id in self.caldav.users.keys():
            location = 'caldav'
        else:
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

        now = floor(time())
        reminder_dict['created-timestamp'] = now
        reminder_dict['updated-timestamp'] = now

        self.reminders[reminder_id] = reminder_dict
        self._set_countdown(reminder_id)
        self._reminder_updated(app_id, reminder_id, reminder_dict)
        self._save_reminders()

        GLib.idle_add(lambda *args: self._do_remote_create_reminder(reminder_id, location))

        return GLib.Variant('(su)', (reminder_id, now))

    def update_reminder(self, app_id: str, now = None, save = True, **kwargs):
        reminder_id = str(kwargs['id'])

        reminder_dict = self.reminders[reminder_id].copy()

        for i in ('title', 'description', 'list-id'):
            if i in kwargs.keys():
                reminder_dict[i] = str(kwargs[i])
        for i in ('timestamp', 'due-date'):
            if i in kwargs.keys():
                reminder_dict[i] = int(kwargs[i])

        user_id = self.lists[reminder_dict['list-id']]['user-id']
        if user_id == 'local':
            location = 'local'
        elif user_id in self.to_do.users.keys():
            location = 'ms-to-do'
        elif user_id in self.caldav.users.keys():
            location = 'caldav'
        else:
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

        if now is None:
            now = floor(time())
        reminder_dict['updated-timestamp'] = now

        if reminder_dict['timestamp'] > floor(time()):
            reminder_dict['shown'] = False

        if reminder_dict['timestamp'] != 0:
            notif_date = datetime.date.fromtimestamp(reminder_dict['timestamp'])
            due_date = datetime.datetime.fromtimestamp(reminder_dict['due-date'], tz=datetime.timezone.utc).date()
            if notif_date != due_date:
                # due date has to be the same day as the reminder date
                reminder_dict['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())

        old_list_uid = None
        old_uid = None
        old_user_id = None
        updating = True
        old_list_id = self.reminders[reminder_id]['list-id']
        if old_list_id != reminder_dict['list-id']:
            updating = False
            user_id = self.lists[old_list_id]['user-id']
            if user_id != 'local':
                old_list_uid = self.lists[old_list_id]['uid']
                old_uid = self.reminders[reminder_id]['uid']
                old_user_id = user_id

        self.reminders[reminder_id] = reminder_dict

        self._set_countdown(reminder_id)
        if save:
            self._reminder_updated(app_id, reminder_id, reminder_dict)
            self._save_reminders()

        GLib.idle_add(lambda *args: self._do_remote_update_reminder(reminder_id, location, old_user_id, old_list_uid, old_uid, updating, old_list_id, save))

        return GLib.Variant('(u)', (now,))

    def update_reminderv(self, app_id: str, reminders: list):
        now = floor(time())

        updated_ids = []
        if len(reminders) > 1:
            threads = []
            queue = Queue()
            for reminder in reminders:
                thread = UpdateThread(queue, reminder['id'], target=self.update_reminder, args=(app_id, now, False), kwargs=reminder)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            while not queue.empty():
                value = queue.get()
                if isinstance(value, Exception):
                    self.emit_error(value)
                else:
                    updated_ids.append(value)

            if len(updated_ids) > 0:
                updated_reminders = self.get_reminders(ids=updated_ids, return_variant=False)
                self.do_emit('RemindersUpdated', GLib.Variant('(saa{sv})', (app_id, updated_reminders)))

        elif len(reminders) == 1:
            reminder = reminders[0]
            self.update_reminder(app_id, now, **reminder)
            updated_ids.append(reminder['id'])

        self._save_reminders()

        return GLib.Variant('(asu)', (updated_ids, now))

    def get_reminders_in_list(self, list_id: str):
        array = []

        for reminder_id, reminder in self.reminders.items():
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
                'completed-date': GLib.Variant('u', reminder['completed-date']),
                'list-id': GLib.Variant('s', reminder['list-id'])
            })

        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))
        return GLib.Variant('(aa{sv})', ([],))

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
                'completed-date': GLib.Variant('u', reminder['completed-date']),
                'list-id': GLib.Variant('s', reminder['list-id'])
            })

        if not return_variant:
            return array
        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))
        return GLib.Variant('(aa{sv})', ([],))

    def get_reminders_dict(self):
        dictionary = {}

        for reminder_id, reminder in self.reminders.items():
            dictionary[reminder_id] = {
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
                'completed-date': GLib.Variant('u', reminder['completed-date']),
                'list-id': GLib.Variant('s', reminder['list-id'])
            }

        if len(dictionary) > 0:
            return GLib.Variant('(a{sa{sv}})', (dictionary,))
        return GLib.Variant('(a{sa{sv}})', ({},))

    def get_lists(self):
        array = []

        for list_id, task_list in self.lists.items():
            array.append({
                'id': GLib.Variant('s', list_id),
                'name': GLib.Variant('s', task_list['name']),
                'user-id': GLib.Variant('s', task_list['user-id'])
            })

        return GLib.Variant('(aa{sv})', (array,))

    def get_lists_dict(self):
        dictionary = {}

        for list_id, task_list in self.lists.items():
            dictionary[list_id] = {
                'name': GLib.Variant('s', task_list['name']),
                'user-id': GLib.Variant('s', task_list['user-id'])
            }

        return GLib.Variant('(a{sa{sv}})', (dictionary,))

    def get_version(self):
        return GLib.Variant('(s)', (VERSION,))

    def create_list(self, app_id, variant = True, **kwargs):
        list_name = str(kwargs['name'])
        user_id = str(kwargs['user-id'])

        if user_id in self.to_do.users.keys() or user_id in self.caldav.users.keys() or user_id == 'local':
            list_id = self._do_generate_id()

            if user_id != 'local':
                if user_id not in self.synced_ids:
                    self.synced_ids.append(list_id)
                    self._set_synced_lists_no_refresh(self.synced_ids)
                GLib.idle_add(lambda *args: self._do_remote_create_list(user_id, list_name, list_id))

            self.lists[list_id] = {
                'name': list_name,
                'user-id': user_id,
                'uid': ''
            }
            self._save_lists()
            self._list_updated(app_id, list_id, list_name, user_id)
            if variant:
                return GLib.Variant('(s)', (list_id,))
            else:
                return list_id
        else:
            raise KeyError('Invalid User ID')

    def update_list(self, app_id, **kwargs):
        list_id = str(kwargs['id'])
        new_name = str(kwargs['name'])

        if list_id in self.lists:
            user_id = self.lists[list_id]['user-id']
            uid = self.lists[list_id]['uid']
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._do_remote_rename_list(user_id, list_id, new_name, uid))

            self.lists[list_id]['name'] = new_name
            self._save_lists()
            self._list_updated(app_id, list_id, new_name, user_id)
        else:
            raise KeyError('Invalid List ID')

    def remove_list(self, app_id, list_id):
        if list_id in self.lists:
            user_id = self.lists[list_id]['user-id']
            uid = self.lists[list_id]['uid']
            if list_id == user_id:
                raise Exception("Can't remove default list")
            if user_id != 'local':
                GLib.idle_add(lambda *args: self._do_remote_delete_list(user_id, list_id, uid))

            self.lists.pop(list_id)
            self._save_lists()
            self.do_emit('ListRemoved', GLib.Variant('(ss)', (app_id, list_id)))
        else:
            raise KeyError('Invalid List ID')

    def get_todo_login_url(self):
        url = self.to_do.get_login_url()
        return GLib.Variant('(s)', (url,))

    def login_caldav(self, name: str, url: str, username: str, password: str):
        user_id = self.caldav.login(name, url, username, password)
        self.synced_ids.append(user_id)
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
            self.synced_ids.remove(user_id)
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

            reminders, lists = self._get_reminders(notify_past, only_user_id)

            new_ids = []
            removed_ids = []
            for reminder_id, reminder in reminders.items():
                if reminder_id not in self.reminders.keys() or reminder != self.reminders[reminder_id]:
                    new_ids.append(reminder_id)
            for reminder_id in self.reminders.keys():
                if reminder_id not in reminders.keys():
                    removed_ids.append(reminder_id)

            for list_id, value in lists.items():
                user_id = value['user-id']
                list_name = value['name']
                if list_id not in self.lists or self.lists[list_id] != lists[list_id]:
                    self._list_updated(info.service_id, list_id, list_name, user_id)

            for list_id in self.lists.keys():
                if list_id not in lists:
                    self.do_emit('ListRemoved', GLib.Variant('(ss)', (info.service_id, list_id)))

            if lists != self.lists:
                self.lists = lists
                self._save_lists()

            if self.reminders != reminders:
                self.reminders = reminders
                self._save_reminders()

            try:
                self.queue.load()
            except:
                pass

            if len(new_ids) > 0:
                new_reminders = self.get_reminders(ids=new_ids, return_variant=False)

                self.do_emit('RemindersUpdated', GLib.Variant('(saa{sv})', (info.service_id, new_reminders)))

            if len(removed_ids) > 0:
                self.do_emit('RemindersRemoved', GLib.Variant('(sas)', (info.service_id, removed_ids)))

            for reminder_id in new_ids:
                self._set_countdown(reminder_id)
            for reminder_id in removed_ids:
                self._remove_countdown(reminder_id)

        except Exception as error:
            logger.exception(error)
        self.refreshing = False

    def set_synced_lists(self, lists):
        variant = GLib.Variant('as', lists)

        self.app.settings.set_value('synced-lists', variant)

    def get_synced_lists(self):
        lists = self.app.settings.get_value('synced-lists').unpack()
        return GLib.Variant('(as)', (lists,))

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

    def import_lists(self, files, list_id):
        if list_id == 'auto':
            self.ical.from_ical(files)
        else:
            self.ical.from_ical(files, list_id)

class UpdateThread(Thread):
    def __init__(self, queue, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue
        self.val = value

    def run(self):
        try:
            retval = self._target(*self._args, **self._kwargs)
            self.queue.put(self.val)
        except Exception as error:
            self.queue.put(error)
