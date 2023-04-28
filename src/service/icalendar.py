# icalendar.py
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

import icalendar
import datetime
import logging
import time

from remembrance import info
from remembrance.service.reminder import Reminder

from gi.repository import GLib
from os import path, mkdir
from math import floor

logger = logging.getLogger(info.service_executable)

DOWNLOADS_DIR = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
if DOWNLOADS_DIR is None:
    DOWNLOADS_DIR = GLib.get_home_dir()

class iCalendar():
    def __init__(self, reminders):
        self.reminders = reminders

    def to_ical(self, lists):
        folder = DOWNLOADS_DIR + '/' + f'Reminders {datetime.datetime.now().strftime("%c")}'

        calendars = {}
        for user_id, list_id in lists:
            list_names = self.reminders.lists
            if user_id in list_names and list_id in list_names[user_id]:
                list_name = list_names[user_id][list_id]
                calendar = icalendar.cal.Calendar()
                calendar.add('X-WR-CALNAME', list_name)
                calendar.add('VERSION', 2.0)

                if user_id not in calendars.keys():
                    calendars[user_id] = {}

                calendars[user_id][list_id] = calendar

        for reminder in self.reminders.reminders.values():
            user_id = user_id
            list_id = reminder['list-id']
            if (user_id, list_id) not in lists:
                continue

            task = self.reminders.caldav.reminder_to_task(reminder, exporting = True)

            todo = icalendar.cal.Todo()
            for key, value in task.items():
                if key in todo:
                    todo.pop(key, None)
                if value is not None:
                    todo.add(key, value)
            try:
                calendars[user_id][list_id].add_component(todo)
            except:
                pass

        mkdir(folder)

        for user_id in calendars:
            for list_id, calendar in calendars[user_id].items():
                base_filename = folder + '/' + calendar['X-WR-CALNAME']
                filename = f'{base_filename}.ical'
                count = 1
                while path.exists(filename):
                    filename = f'{base_filename} ({count}).ical'
                    count += 1

                with open(filename, 'w') as f:
                    f.write(calendar.to_ical().decode('UTF-8'))

        return folder

    def from_ical(self, files, user_id = None, list_id = None):
        for file in files:
            if path.isfile(file):
                with open(file, 'r') as f:
                    calendar = icalendar.cal.Calendar.from_ical(f.read())
                    list_name = calendar['X-WR-CALNAME'] if 'X-WR-CALNAME' in calendar else path.splitext(path.basename(file))[0]
                    if user_id is None and list_id is None:
                        user_id = 'local'
                        list_id = self.reminders.create_list(info.service_id, user_id, list_name, variant = False)

                    if user_id == 'local':
                        location = 'local'
                    elif user_id in self.reminders.to_do.users.keys():
                        location = 'ms-to-do'
                    elif user_id in self.reminders.caldav.users.keys():
                        location = 'caldav'
                    else:
                        raise KeyError('Invalid user id')

                    try:
                        list_name = self.reminders.lists[user_id][list_id]
                    except KeyError:
                        raise KeyError('Invalid list id')

                    new_ids = []
                    for todo in calendar.subcomponents:
                        try:
                            reminder = Reminder()
                            due_date = 0
                            timestamp = 0
                            due = todo.get('DUE', None)
                            if due is not None:
                                due = due.dt
                                try:
                                    if isinstance(due, datetime.datetime):
                                        timestamp = due.timestamp()
                                    elif isinstance(due, datetime.date):
                                        due_date = datetime.datetime.combine(due, datetime.time()).astimezone(tz=datetime.timezone.utc).timestamp()
                                except:
                                    pass

                            is_future = timestamp > floor(time.time())
                            reminder['shown'] = timestamp != 0 and not is_future

                            reminder = self.reminders.caldav.task_to_reminder(todo, list_id, user_id, reminder, timestamp, due_date)
                            new_id = self.reminders._do_generate_id(list(self.reminders.ms_reminders.keys()) + list(self.reminders.caldav_reminders.keys()) + list(self.reminders.local_reminders.keys()))
                            new_ids.append(new_id)
                            self.reminders[new_id] = reminder
                            self.reminders._set_countdown(new_id)
                            self.reminders._do_remote_create_reminder(new_id, location)
                        except Exception as error:
                            logger.exception(error)
                            continue

                    if len(new_ids) > 0:
                        new_reminders = self.reminders.get_reminders(ids=new_ids, return_variant=False)
                        self.reminders.do_emit('Refreshed', GLib.Variant('(aa{sv}as)', (new_reminders, [])))
                    self.reminders._save_reminders()
