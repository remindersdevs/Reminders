# backend.py - Backend that handles files and notifications
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
import time
import logging
import random
import string
import datetime
import gi

gi.require_version('GSound', '1.0')
from gi.repository import GLib, Gio, GSound
from remembrance import info
from gettext import gettext as _
from enum import IntFlag, IntEnum, auto
from math import floor

class RepeatType(IntEnum):
    DISABLED = 0
    MINUTE = 1
    HOUR = 2
    DAY = 3
    WEEK = 4

class RepeatDays(IntFlag):
    MON = auto()
    TUE = auto()
    WED = auto()
    THU = auto()
    FRI = auto()
    SAT = auto()
    SUN = auto()

DATA_DIR = f'{GLib.get_user_data_dir()}/remembrance'
REMINDERS_FILE = f'{DATA_DIR}/reminders.csv'
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

VERSION = info.service_version
PID = os.getpid()

logger = logging.getLogger(info.service_executable)

def get_xml(dict_empty):
    return_param = '' if dict_empty else "<arg name='reminders' direction='out' type='aa{sv}'/>" 
    xml = f'''<node name="/">
    <interface name="{info.service_interface}">
        <method name='AddReminder'>
            <arg name='app_id' type='s'/>
            <arg name='args' type='a{{sv}}'/>
            <arg name='reminder_id' direction='out' type='s'/>
        </method>
        <method name='UpdateReminder'>
            <arg name='app_id' type='s'/>
            <arg name='args' type='a{{sv}}'/>
        </method>
        <method name='UpdateCompleted'>
            <arg name='app_id' type='s'/>
            <arg name='reminder_id' type='s'/>
            <arg name='completed' type='b'/>
        </method>
        <method name='RemoveReminder'>
            <arg name='app_id' type='s'/>
            <arg name='reminder_id' type='s'/>
        </method>
        <method name='ReturnReminders'>
            {return_param}
        </method>
        <method name='Quit'/>
        <method name='GetVersion'>
            <arg name='version' direction='out' type='d'/>
        </method>
        <signal name='CompletedUpdated'>
            <arg name='app_id' direction='out' type='s'/>
            <arg name='reminder_id' direction='out' type='s'/>
            <arg name='completed' direction='out' type='b'/>
        </signal>
        <signal name='ReminderDeleted'>
            <arg name='app_id' direction='out' type='s'/>
            <arg name='reminder_id' direction='out' type='s'/>
        </signal>
        <signal name='ReminderUpdated'>
            <arg name='app_id' direction='out' type='s'/>
            <arg name='reminder' direction='out' type='a{{sv}}'/>
        </signal>
        <signal name='RepeatUpdated'>
            <arg name='reminder_id' direction='out' type='s'/>
            <arg name='timestamp' direction='out' type='u'/>
            <arg name='old-timestamp' direction='out' type='u'/>
            <arg name='repeat-times' direction='out' type='n'/>
        </signal>
    </interface>
    </node>'''
    return xml

class Countdowns():
    '''Handles timeouts for notifications'''
    def __init__(self):
        self.dict = {}

        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,
            'org.freedesktop.login1',
            '/org/freedesktop/login1',
            'org.freedesktop.login1.Manager',
            None,
            self._bus_callback
        );

    def _bus_callback(self, obj, result):
        proxy = obj.new_for_bus_finish(result)
        proxy.connect("g-signal", self._on_signal_received)

    def _on_signal_received(self, proxy, sender, signal, parameters):
        if signal == "PrepareForSleep" and parameters[0]:
            logger.info('Resuming from sleep')
            for i in self.dict.values():
                self._start(i)

    def remove_countdown(self, reminder_id):
        if reminder_id in self.dict:
            countdown_id = self.dict[reminder_id]['id']
            if countdown_id != 0:
                GLib.Source.remove(countdown_id)
            self.dict.pop(reminder_id)

    def add_countdown(self, timestamp, callback, reminder_id):
        if reminder_id in self.dict.keys() and self.dict[reminder_id]['id'] != 0:
            GLib.Source.remove(self.dict[reminder_id]['id'])
    
        dictionary = {
            'timestamp': timestamp,
            'callback': callback,
            'id': 0
        }
        self.dict[reminder_id] = dictionary
        self._start(reminder_id)

    def _start(self, reminder_id):
        dictionary = self.dict[reminder_id]
        if dictionary['id'] != 0:
            GLib.Source.remove(dictionary['id'])
            dictionary['id'] = 0

        now = time.time()
        wait = int(1000 * (dictionary['timestamp'] - now))
        if wait > 0:
            try: 
                self.dict[reminder_id]['id'] = GLib.timeout_add(wait, dictionary['callback'])
            except Exception as error:
                logger.error(f'{error}: Failed to set timeout for {reminder_id}')
        else:
            dictionary['callback']()

class Reminders():
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        if not os.path.isdir(DATA_DIR):
            os.mkdir(DATA_DIR)
        self._regid = None
        self.dict = {}
        self.app = app
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.sound = GSound.Context()
        self.sound.init()
        self.countdowns = Countdowns()
        self._get_reminders()
        self._dict_empty = (len(self.dict.keys()) == 0)
        self._methods = {
            'UpdateCompleted': self.set_completed,
            'AddReminder': self.add_reminder,
            'UpdateReminder': self.update_reminder,
            'RemoveReminder': self.remove_reminder,
            'ReturnReminders': self.return_reminders,
            'GetVersion': self.get_version
        }
        self._register()

    def do_emit(self, signal_name, parameters):
        self.connection.emit_signal(
            None,
            info.service_object,
            info.service_interface,
            signal_name,
            parameters
        )

    def _register(self):
        if self._regid is not None:
            self.connection.unregister_object(self._regid)

        node_info = Gio.DBusNodeInfo.new_for_xml(get_xml(self._dict_empty))
        self._regid = self.connection.register_object(
            info.service_object,
            node_info.interfaces[0],
            self._on_method_call,
            None,
            None
        )

    def _update_dict_empty(self):
        if len(self.dict.keys()) > 0 and self._dict_empty:
            self._dict_empty = False
            self._register()
        elif len(self.dict.keys()) == 0 and not self._dict_empty:
            self._dict_empty = True
            self._register()

    def _on_method_call(self, connection, sender, path, interface, method, parameters, invocation):
        try:
            if method == 'Quit':
                if self._regid is not None:
                    self.connection.unregister_object(self._regid)
                invocation.return_value(None)
                self.app.quit()

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
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed', f'{error} - Method {method} failed to execute')

    def _generate_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def _do_generate_id(self):
        new_id = self._generate_id()
        while new_id in self.dict: # if for some reason it isn't unique
            new_id = self._generate_id()

        return new_id

    def _remove_countdown(self, reminder_id):
        self.countdowns.remove_countdown(reminder_id)

    def _set_countdown(self, reminder_id):
        if self.dict[reminder_id]['repeat-times'] == 0:
            return

        if self.dict[reminder_id]['completed'] or self.dict[reminder_id]['timestamp'] == 0:
            return

        notification = Gio.Notification.new(self.dict[reminder_id]['title'])
        notification.set_body(self.dict[reminder_id]['description'])
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

        self.countdowns.add_countdown(self.dict[reminder_id]['timestamp'], do_send_notification, reminder_id)

    def _update_repeat(self, reminder_id):
        self.dict[reminder_id]['old-timestamp'] = self.dict[reminder_id]['timestamp']
        if self.dict[reminder_id]['repeat-type'] != 0:
            self._repeat(reminder_id)
        self.do_emit('RepeatUpdated', GLib.Variant('(suun)', (reminder_id, self.dict[reminder_id]['timestamp'], self.dict[reminder_id]['old-timestamp'], self.dict[reminder_id]['repeat-times'])))

    def _repeat(self, reminder_id):
        delta = None
        repeat_times = self.dict[reminder_id]['repeat-times']
        if repeat_times == 0:
            return
        timestamp = self.dict[reminder_id]['timestamp']
        old_timestamp = self.dict[reminder_id]['old-timestamp']
        repeat_until = self.dict[reminder_id]['repeat-until']
        if repeat_until > 0 and repeat_until < timestamp:
            return

        repeat_type = self.dict[reminder_id]['repeat-type']
        frequency = self.dict[reminder_id]['repeat-frequency']
        repeat_days = self.dict[reminder_id]['repeat-days']
        timedate = datetime.datetime.fromtimestamp(timestamp)

        if repeat_type == RepeatType.MINUTE:
            delta = datetime.timedelta(minutes=frequency)
        elif repeat_type == RepeatType.HOUR:
            delta = datetime.timedelta(hours=frequency)
        elif repeat_type == RepeatType.DAY:
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

        if repeat_type == RepeatType.WEEK:
            weekday = timedate.date().weekday()
            repeat_days_flag = RepeatDays(repeat_days)
            index = 0
            days = []
            for num, flag in (
                (0, RepeatDays.MON),
                (1, RepeatDays.TUE),
                (2, RepeatDays.WED),
                (3, RepeatDays.THU),
                (4, RepeatDays.FRI),
                (5, RepeatDays.SAT),
                (6, RepeatDays.SUN)
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
                    break
                if value > weekday:
                    index = i
                    break

            timedate += datetime.timedelta(days=((days[index] - weekday) % 7))
            timestamp = timedate.timestamp()

            while timestamp < floor(time.time()):
                old_timestamp = timestamp
                if repeat_times != -1:
                    repeat_times -= 1
                if repeat_times == 0:
                    break
                weekday = timedate.date().weekday()
                index += 1
                if index > len(days) - 1:
                    index = 0
                timedate += datetime.timedelta(days=((days[index] - weekday) % 7))
                timestamp = timedate.timestamp()


        if repeat_until > 0 and repeat_until < floor(timestamp):
            return

        self.dict[reminder_id]['repeat-times'] = repeat_times
        self.dict[reminder_id]['timestamp'] = floor(timestamp)
        self.dict[reminder_id]['old-timestamp'] = int(old_timestamp)

        self._save_reminders()

        if repeat_times != 0:
            self._set_countdown(reminder_id)

    def _shown(self, reminder_id):
        if reminder_id in self.dict:
            if self.dict[reminder_id]['repeat-times'] > 0:
                self.dict[reminder_id]['repeat-times'] -= 1
                self._save_reminders()

    def _save_reminders(self):
        with open(REMINDERS_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()

            for reminder in self.dict:
                writer.writerow({
                    'id': reminder,
                    'title': self.dict[reminder]['title'],
                    'description': self.dict[reminder]['description'],
                    'timestamp': self.dict[reminder]['timestamp'],
                    'completed': self.dict[reminder]['completed'],
                    'repeat-type': self.dict[reminder]['repeat-type'],
                    'repeat-frequency': self.dict[reminder]['repeat-frequency'],
                    'repeat-days': self.dict[reminder]['repeat-days'],
                    'repeat-times': self.dict[reminder]['repeat-times'],
                    'repeat-until': self.dict[reminder]['repeat-until'],
                    'old-timestamp': self.dict[reminder]['old-timestamp']
                })

    def _get_boolean(self, row, key):
        return (key in row.keys() and row[key] == 'True')

    def _get_int(self, row, key, default = 0):
        try:
            retval = int(row[key])
        except:
            retval = default
        return retval

    def _get_reminders(self):
        logger.info('Loading reminders')
        if os.path.isfile(REMINDERS_FILE):
            with open(REMINDERS_FILE, newline='') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        reminder_id = row['id']
                        title = row['title']
                        description = row['description']
                        timestamp = self._get_int(row, 'timestamp')
                        completed = self._get_boolean(row, 'completed')
                        repeat_type = self._get_int(row, 'repeat-type')
                        repeat_frequency = self._get_int(row, 'repeat-frequency', 1)
                        repeat_days = self._get_int(row, 'repeat-days')
                        if self._get_boolean(row, 'shown'):
                            repeat_times = 0
                        else:
                            repeat_times = self._get_int(row, 'repeat-times', 1)
                        repeat_until = self._get_int(row, 'repeat-until')
                        old_timestamp = timestamp if timestamp < floor(time.time()) else self._get_int(row, 'old-timestamp')
                    except Exception as error:
                        logger.error(f'{error}: Failed to read reminder')
                        continue

                    self.dict[reminder_id] = {
                        'title': title,
                        'description': description,
                        'timestamp': timestamp,
                        'completed': completed,
                        'repeat-type': repeat_type,
                        'repeat-frequency': repeat_frequency,
                        'repeat-days': repeat_days,
                        'repeat-times': repeat_times,
                        'repeat-until': repeat_until,
                        'old-timestamp': old_timestamp
                    }

                    self._set_countdown(reminder_id)

    # Below methods can be accessed by other apps over dbus
    def set_completed(self, app_id: str, reminder_id: str, completed: bool):
        self.dict[reminder_id]['completed'] = completed
        self._save_reminders()
        if completed:
            self._remove_countdown(reminder_id)
        else:
            self._set_countdown(reminder_id)
        self.do_emit('CompletedUpdated', GLib.Variant('(ssb)', (app_id, reminder_id, completed)))

    def remove_reminder(self, app_id: str, reminder_id: str):
        self.app.withdraw_notification(reminder_id)
        self._remove_countdown(reminder_id)
        if reminder_id in self.dict:
            self.dict.pop(reminder_id)
            self._save_reminders()
        self._update_dict_empty()
        self.do_emit('ReminderRemoved', GLib.Variant('(ss)', (app_id, reminder_id)))

    def add_reminder(self, app_id: str, **kwargs):
        title = str(kwargs['title'])
        description = str(kwargs['description'])
        timestamp = int(kwargs['timestamp'])
        repeat_type = int(kwargs['repeat-type'])
        repeat_frequency = int(kwargs['repeat-frequency'])
        repeat_days = int(kwargs['repeat-days'])
        repeat_times = int(kwargs['repeat-times'])
        repeat_until = int(kwargs['repeat-until'])

        reminder_id = self._do_generate_id()
        self._remove_countdown(reminder_id)
        self.dict[reminder_id] = {
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'completed': False,
            'repeat-type': repeat_type,
            'repeat-frequency': repeat_frequency,
            'repeat-days': repeat_days,
            'repeat-times': repeat_times,
            'repeat-until': repeat_until,
            'old-timestamp': 0
        }
        with open(REMINDERS_FILE, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

            writer.writerow({
                'id': reminder_id,
                'title': title,
                'description': description,
                'timestamp': timestamp,
                'completed': False,
                'repeat-type': repeat_type,
                'repeat-frequency': repeat_frequency,
                'repeat-days': repeat_days,
                'repeat-times': repeat_times,
                'repeat-until': repeat_until,
                'old-timestamp': 0
            })

        reminder = {
            'id': GLib.Variant('s', reminder_id),
            'title': GLib.Variant('s', title),
            'description': GLib.Variant('s', description),
            'timestamp': GLib.Variant('u', timestamp),
            'repeat-type': GLib.Variant('q', repeat_type),
            'repeat-frequency': GLib.Variant('q', repeat_frequency),
            'repeat-days': GLib.Variant('q', repeat_days),
            'repeat-times': GLib.Variant('n', repeat_times),
            'repeat-until': GLib.Variant('u', repeat_until)
        }
        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, reminder)))

        self._set_countdown(reminder_id)
        self._update_dict_empty()

        return GLib.Variant('(s)', (reminder_id,))

    def update_reminder(self, app_id: str, **kwargs):
        reminder_id = str(kwargs['id'])
        title = str(kwargs['title'])
        description = str(kwargs['description'])
        timestamp = int(kwargs['timestamp'])
        repeat_type = int(kwargs['repeat-type'])
        repeat_frequency = int(kwargs['repeat-frequency'])
        repeat_days = int(kwargs['repeat-days'])
        repeat_times = int(kwargs['repeat-times'])
        repeat_until = int(kwargs['repeat-until'])

        self.dict[reminder_id]['title'] = title
        self.dict[reminder_id]['description'] = description
        self.dict[reminder_id]['timestamp'] = timestamp
        self.dict[reminder_id]['repeat-type'] = repeat_type
        self.dict[reminder_id]['repeat-frequency'] = repeat_frequency
        self.dict[reminder_id]['repeat-days'] = repeat_days
        self.dict[reminder_id]['repeat-times'] = repeat_times
        self.dict[reminder_id]['repeat-until'] = repeat_until

        self._save_reminders()
        self._remove_countdown(reminder_id)

        reminder = {
            'id': GLib.Variant('s', reminder_id),
            'title': GLib.Variant('s', title),
            'description': GLib.Variant('s', description),
            'timestamp': GLib.Variant('u', timestamp),
            'repeat-type': GLib.Variant('q', repeat_type),
            'repeat-frequency': GLib.Variant('q', repeat_frequency),
            'repeat-days': GLib.Variant('q', repeat_days),
            'repeat-times': GLib.Variant('n', repeat_times),
            'repeat-until': GLib.Variant('u', repeat_until)
        }
        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, reminder)))

        if timestamp < floor(time.time()):
            self.dict[reminder_id]['old-timestamp'] = timestamp
            self.do_emit('RepeatUpdated', GLib.Variant('(suun)', (reminder_id, timestamp, self.dict[reminder_id]['old-timestamp'], repeat_times)))

        self._set_countdown(reminder_id)

    def return_reminders(self):
        array = []
        for reminder in self.dict:
            array.append({
                'id': GLib.Variant('s', reminder),
                'title': GLib.Variant('s', self.dict[reminder]['title']),
                'description': GLib.Variant('s', self.dict[reminder]['description']),
                'timestamp': GLib.Variant('u', self.dict[reminder]['timestamp']),
                'completed': GLib.Variant('b', self.dict[reminder]['completed']),
                'repeat-type': GLib.Variant('q', self.dict[reminder]['repeat-type']),
                'repeat-frequency': GLib.Variant('q', self.dict[reminder]['repeat-frequency']),
                'repeat-days': GLib.Variant('q', self.dict[reminder]['repeat-days']),
                'repeat-times': GLib.Variant('n', self.dict[reminder]['repeat-times']),
                'repeat-until': GLib.Variant('u', self.dict[reminder]['repeat-until']),
                'old-timestamp': GLib.Variant('u', self.dict[reminder]['old-timestamp'])
            })

        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))

    def get_version(self):
        return GLib.Variant('(d)', (VERSION,))
