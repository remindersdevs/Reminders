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

from gi.repository import GLib, Gio
from remembrance import info
from gettext import gettext as _

DATA_DIR = f'{GLib.get_user_data_dir()}/remembrance'
REMINDERS_FILE = f'{DATA_DIR}/reminders.csv'
FIELDNAMES = ['id', 'title', 'description', 'timestamp', 'completed', 'shown']

VERSION = info.service_version
PID = os.getpid()

logger = logging.getLogger(info.service_executable)

def get_xml(dict_empty):
    return_param = '' if dict_empty else "<arg name='reminders' direction='out' type='aa{sv}'/>" 
    xml = f'''<node name="/">
    <interface name="{info.service_id}">
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
        <method name='GetVersion'>
            <arg name='version' direction='out' type='d'/>
        </method>
        <signal name='ReminderShown'>
            <arg name='reminder_id' direction='out' type='s'/>
        </signal>
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
        if reminder_id in self.dict and self.dict[reminder_id]['id'] != 0:
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

        now = int(time.time())
        wait = dictionary['timestamp'] - now
        if wait > 0:
            try: 
                dictionary['id'] = GLib.timeout_add_seconds(wait, dictionary['callback'])
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
            info.service_id,
            signal_name,
            parameters
        )

    def _update_cb(self, n_ops, op, progress, status, error, error_message):
        from gi.repository import Xdp
        logger.info(status)
        if status == Xdp.UpdateStatus.DONE:
            logger.info('done')

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
        if not self.dict[reminder_id]['shown'] and not self.dict[reminder_id]['completed'] and self.dict[reminder_id]['timestamp'] != 0:
            notification = Gio.Notification.new(self.dict[reminder_id]['title'])
            notification.set_body(self.dict[reminder_id]['description'])
            notification.add_button_with_target(_('Mark as completed'), 'app.reminder-completed', GLib.Variant('s', reminder_id))
            notification.set_default_action('app.notification-clicked')

            def do_send_notification():
                self.app.send_notification(reminder_id, notification)
                self._set_shown(reminder_id, True)
                self.do_emit('ReminderShown', GLib.Variant('(s)', (reminder_id,)))
                self.countdowns.dict[reminder_id]['id'] = 0
                return False

            self.countdowns.add_countdown(self.dict[reminder_id]['timestamp'], do_send_notification, reminder_id)

    def _set_shown(self, reminder_id, shown):
        if reminder_id in self.dict:
            self.dict[reminder_id]['shown'] = shown
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
                    'shown': self.dict[reminder]['shown']
                })

    def _get_boolean(self, row, key):
        return (key in row.keys() and row[key] == 'True')

    def _get_int(self, row, key):
        try:
            retval = int(row[key])
        except:
            retval = 0
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
                        shown = self._get_boolean(row, 'shown')
                    except Exception as error:
                        logger.error(f'{error}: Failed to read reminder')
                        continue

                    self.dict[reminder_id] = {
                        'title': title,
                        'description': description,
                        'timestamp': timestamp,
                        'completed': completed,
                        'shown': shown
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

        reminder_id = self._do_generate_id()
        self._remove_countdown(reminder_id)
        self.dict[reminder_id] = {
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'completed': False,
            'shown': False
        }
        with open(REMINDERS_FILE, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

            writer.writerow({
                'id': reminder_id,
                'title': title,
                'description': description,
                'timestamp': timestamp,
                'completed': False,
                'shown': False
            })
        self._set_countdown(reminder_id)
        self._update_dict_empty()

        reminder = {
            'id': GLib.Variant('s', reminder_id),
            'title': GLib.Variant('s', title),
            'description': GLib.Variant('s', description),
            'timestamp': GLib.Variant('u', timestamp)
        }
        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, reminder)))

        return GLib.Variant('(s)', (reminder_id,))

    def update_reminder(self, app_id: str, **kwargs):
        reminder_id = str(kwargs['id'])
        title = str(kwargs['title'])
        description = str(kwargs['description'])
        timestamp = int(kwargs['timestamp'])

        self.dict[reminder_id]['title'] = title
        self.dict[reminder_id]['description'] = description
        self.dict[reminder_id]['timestamp'] = timestamp

        if timestamp > int(time.time()):
            self.dict[reminder_id]['shown'] = False

        self._save_reminders()

        self._set_countdown(reminder_id)
        reminder = {
            'id': GLib.Variant('s', reminder_id),
            'title': GLib.Variant('s', title),
            'description': GLib.Variant('s', description),
            'timestamp': GLib.Variant('u', timestamp)
        }
        self.do_emit('ReminderUpdated', GLib.Variant('(sa{sv})', (app_id, reminder)))

    def return_reminders(self):
        array = []
        for reminder in self.dict:
            array.append({
                'id': GLib.Variant('s', reminder),
                'title': GLib.Variant('s', self.dict[reminder]['title']),
                'description': GLib.Variant('s', self.dict[reminder]['description']),
                'timestamp': GLib.Variant('u', self.dict[reminder]['timestamp']),
                'completed': GLib.Variant('b', self.dict[reminder]['completed'])
            })

        if len(array) > 0:
            return GLib.Variant('(aa{sv})', (array,))

    def get_version(self):
        return GLib.Variant('(d)', (VERSION,))
