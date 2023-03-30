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
                self._start(i, True)

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

    def _start(self, reminder_id, resuming = False):
        dictionary = self.dict[reminder_id]
        if dictionary['id'] != 0:
            GLib.Source.remove(dictionary['id'])
            dictionary['id'] = 0

        now = time.time()
        if 'interval' in dictionary.keys():
            wait = dictionary['interval'] * 60000
            if resuming:
                dictionary['callback']()
        else:
            wait = int(1000 * (dictionary['timestamp'] - now))

        if wait > 0:
            try: 
                self.dict[reminder_id]['id'] = GLib.timeout_add(wait, dictionary['callback'])
            except Exception as error:
                logger.error(f'{error}: Failed to set timeout for {reminder_id}')
        else:
            dictionary['callback']()