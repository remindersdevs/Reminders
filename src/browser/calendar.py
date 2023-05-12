# calendar.py
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

from gi.repository import GLib, Gio

from reminders import info
from logging import getLogger
from time import time
if info.on_windows:
    from winsdk.windows.system.threading import ThreadPoolTimer

logger = getLogger(info.app_executable)

class Calendar():
    '''Updates date labels when day changes'''
    def __init__(self, win):
        self.win = win
        self.time = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.timer = 0

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

        self.run_countdown()

    def on_wake_from_suspend(self, connection, sender, object, interface, signal, parameters, data = None):
        if parameters.unpack()[0]:
            return

        self.run_countdown(False)

    def on_countdown_done(self):
        for reminder in self.win.reminder_lookup_dict.values():
            reminder.set_time_label()
            reminder.refresh_time()
        if self.win.reminder_edit_win is not None:
            self.win.reminder_edit_win.update_date_button_label()
        self.timer = 0
        self.run_countdown()
        return False

    def remove_countdown(self):
        if self.timer != 0 and self.timer is not None:
            if info.on_windows:
                self.timer.cancel()
            else:
                GLib.Source.remove(self.timer)
            self.timer = 0

    def run_countdown(self, new_day = True):
        try:
            if new_day:
                self.time += datetime.timedelta(days=1)
                self.timestamp = self.time.timestamp()

            self.remove_countdown()

            now = time()
            wait = int(1000 * (self.timestamp - now))
            if wait > 0:
                if info.on_windows:
                    self.timer = ThreadPoolTimer.create_timer(lambda *args: self.on_countdown_done(), datetime.timedelta(milliseconds=wait))
                else:
                    self.timer = GLib.timeout_add(wait, self.on_countdown_done)
            else:
                self.on_countdown_done()
        except Exception as error:
            logger.exception(f'{error}: Failed to set timeout to refresh date labels')
