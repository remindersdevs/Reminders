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
import datetime

from gi.repository import GLib, Gio, GObject

DATA_DIR = f'{GLib.get_user_data_dir()}/remembrance'
REMINDERS_FILE = f'{DATA_DIR}/reminders.csv'
    
class Countdown():
    def __init__(self, timestamp, countdown_done_func):
        self.timestamp = timestamp
        self.context = GLib.MainContext
        now = int(time.time())
        self.wait = self.timestamp - now
        self.func = countdown_done_func

        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,
            'org.freedesktop.login1',
            '/org/freedesktop/login1',
            'org.freedesktop.login1.Manager',
            None,
            self.bus_callback
        );

    def refresh(self):
        now = int(time.time())
        self.wait = self.timestamp - now
        self.start()

    def bus_callback(self, obj, result):
        proxy = obj.new_for_bus_finish(result)
        proxy.connect("g-signal", self.on_signal_received)

    def on_signal_received(self, proxy, sender, signal, parameters):
        if signal == "PrepareForSleep" and parameters[0]:
            self.refresh()

    def start(self):
        if self.wait > 0:
            countdown_id = GLib.timeout_add_seconds(self.wait, self.func)
            return countdown_id
        else:
            self.func()
        return None

class Calendar(GObject.Object):
    def __init__(self, app):
        self.app = app
        today = datetime.datetime.combine(datetime.date.today(), datetime.time())
        tomorrow = today + datetime.timedelta(days=1)
        tomorrow = tomorrow.timestamp()
        countdown = Countdown(tomorrow, self.on_countdown_done)
        self.countdown_id = countdown.start()

    def on_countdown_done(self):
        for reminder in self.app.win.reminder_lookup_dict.values():
            reminder.refresh_time()
        tomorrow = tomorrow + datetime.timedelta(days=1)
        countdown = Countdown(tomorrow, self.on_countdown_done)
        self.countdown_id = countdown.start()

class Reminders():
    def __init__(self, app):
        super().__init__()
        self.dict = {}
        self.app = app

        if not os.path.isdir(DATA_DIR):
            os.mkdir(DATA_DIR)

        if os.path.isfile(REMINDERS_FILE):
            self.get_reminders()

        self.save_reminders()

    def remove_reminder(self, reminder_id):
        if reminder_id in self.dict:
            self.dict.pop(reminder_id)
            self.save_reminders()

    def set_countdown(self, reminder_id, title, description, timestamp, countdown_id = None):
        notification = Gio.Notification.new(title)
        notification.set_body(description)
        notification.add_button_with_target('Mark as completed', 'app.reminder-completed', GLib.Variant('s', reminder_id))

        def do_send_notification():
            self.app.send_notification(reminder_id, notification)
            try:
                self.app.win.reminder_lookup_dict[reminder_id].refresh_time()
            except AttributeError:
                pass

        countdown = Countdown(timestamp, do_send_notification)
        if countdown_id is not None:
            GLib.Source.remove(countdown_id)

        countdown.start()

    def set_completed(self, reminder_id, completed):
        self.dict[reminder_id]['completed'] = completed
        self.save_reminders()
        try:
            self.app.win.reminder_lookup_dict[reminder_id].set_property('completed', True)
            self.app.win.move_reminder(reminder_id)
        except AttributeError:
            pass

    def add_reminder(self, reminder_id, title, description, time_enabled, timestamp):
        self.dict[reminder_id] = {
            'title': title,
            'description': description,
            'time-enabled': time_enabled,
            'timestamp': timestamp,
            'completed': False
        }
        with open(REMINDERS_FILE, 'a', newline='') as csvfile:
            fieldnames = ['id', 'title', 'description', 'time-enabled', 'timestamp', 'completed']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writerow({
                'id': reminder_id,
                'title': title,
                'description': description,
                'time-enabled': time_enabled,
                'timestamp': timestamp,
                'completed': False
            })

    def save_reminders(self):
        with open(REMINDERS_FILE, 'w', newline='') as csvfile:
            fieldnames = ['id', 'title', 'description', 'time-enabled', 'timestamp', 'completed']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for reminder in self.dict:
                writer.writerow({
                    'id': reminder,
                    'title': self.dict[reminder]['title'],
                    'description': self.dict[reminder]['description'],
                    'time-enabled': self.dict[reminder]['time-enabled'],
                    'timestamp': self.dict[reminder]['timestamp'],
                    'completed': self.dict[reminder]['completed'],
                })

    def get_reminders(self):
        with open(REMINDERS_FILE, newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                reminder_id = row['id']
                title = row['title']
                description = row['description']
                time_enabled = True if row['time-enabled'] == 'True' else False
                timestamp = int(row['timestamp'])
                completed = True if row['completed'] == 'True' else False

                if not completed:
                    self.set_countdown(reminder_id, title, description, timestamp)

                self.dict[reminder_id] ={
                    'id': reminder_id,
                    'title': title,
                    'description': description,
                    'time-enabled': time_enabled,
                    'timestamp': timestamp,
                    'completed': completed
                }
