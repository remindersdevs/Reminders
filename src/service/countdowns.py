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

from gi.repository import GLib, Gio

from reminders import info
from time import time
from logging import getLogger
if info.on_windows:
    from winsdk.windows.system.threading import ThreadPoolTimer
    from datetime import timedelta

logger = getLogger(info.service_executable)

class Countdowns():
    '''Handles timeouts for notifications'''
    def __init__(self):
        self.dict = {}

        if not info.on_windows:
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

        for reminder_id in self.dict.copy().keys():
            self._start(reminder_id, resuming=True)

    def remove_countdown(self, reminder_id, pop = True):
        if reminder_id in self.dict.keys():
            timer = self.dict[reminder_id]['timer']
            if timer != 0 and timer is not None:
                if info.on_windows:
                    timer.cancel()
                else:
                    GLib.Source.remove(timer)
            if pop:
                self.dict.pop(reminder_id)

    def add_timeout(self, interval, callback, timeout_id):
        self.remove_countdown(timeout_id, pop=False)

        dictionary = {
            'interval': interval,
            'callback': callback,
            'timer': 0
        }
        self.dict[timeout_id] = dictionary
        self._start(timeout_id)

    def add_countdown(self, timestamp, callback, reminder_id):
        self.remove_countdown(reminder_id, pop=False)

        dictionary = {
            'timestamp': timestamp,
            'callback': callback,
            'timer': 0
        }
        self.dict[reminder_id] = dictionary
        self._start(reminder_id)

    def _start(self, reminder_id, resuming = False):
        self.remove_countdown(reminder_id, pop=False)

        dictionary = self.dict[reminder_id]

        if 'interval' in dictionary.keys():
            # wait 30 seconds after waking from suspend, this hopefully will give enough time for internet to reconnect
            wait = 30000 if resuming else dictionary['interval'] * 60000
        else:
            now = time()
            wait = int(1000 * (dictionary['timestamp'] - now))

        if wait > 0:
            try:
                if info.on_windows:
                    self.dict[reminder_id]['timer'] = ThreadPoolTimer.create_timer(lambda *args: dictionary['callback'](), timedelta(milliseconds=wait))
                else:
                    self.dict[reminder_id]['timer'] = GLib.timeout_add(wait, dictionary['callback'])
            except Exception as error:
                logger.exception(f'{error}: Failed to set timeout for {reminder_id}')
        else:
            dictionary['callback']()
