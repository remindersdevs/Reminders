# countdown.py
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

import time
import logging

from gi.repository import GLib, Gio

from remembrance import info

logger = logging.getLogger(info.service_executable)

class Countdowns():
    '''Handles timeouts for notifications'''
    def __init__(self):
        self.dict = {}

        self.connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.connection.signal_subscribe(
            'org.freedesktop.login1',
            'org.freedesktop.login1.Manager',
            'PrepareForSleep',
            '/org/freedesktop/login1',
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_wake_from_suspend,
            None
        )

    def on_wake_from_suspend(self, connection, sender, object, interface, signal, parameters, data = None):
        if parameters.unpack()[0]:
            return
    
        for reminder_id in self.dict.keys():
            self._start(reminder_id)

    def remove_countdown(self, reminder_id):
        if reminder_id in self.dict:
            countdown_id = self.dict[reminder_id]['id']
            if countdown_id != 0:
                GLib.Source.remove(countdown_id)
            self.dict.pop(reminder_id)

    def add_timeout(self, interval, callback, timeout_id):
        if timeout_id in self.dict.keys() and self.dict[timeout_id]['id'] != 0:
            GLib.Source.remove(self.dict[timeout_id]['id'])
    
        dictionary = {
            'interval': interval,
            'callback': callback,
            'id': 0
        }
        self.dict[timeout_id] = dictionary
        self._start(timeout_id)

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
        
        if 'interval' in dictionary.keys():
            wait = dictionary['interval'] * 60000
        else:
            now = time.time()
            wait = int(1000 * (dictionary['timestamp'] - now))

        if wait > 0:
            try: 
                self.dict[reminder_id]['id'] = GLib.timeout_add(wait, dictionary['callback'])
            except Exception as error:
                logger.error(f'{error}: Failed to set timeout for {reminder_id}')
        else:
            dictionary['callback']()