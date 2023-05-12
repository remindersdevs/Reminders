# caldav.py
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

from reminders import info
from reminders.service.reminder import Reminder
from logging import getLogger
from json import loads, dumps
from requests import HTTPError, Timeout, ConnectionError
from caldav.davclient import DAVClient
from caldav.elements.dav import DisplayName
from caldav.objects import Todo
from keyring import get_password, set_password, delete_password, set_keyring
from keyring.backends import SecretService

DAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
logger = getLogger(info.service_executable)

if not info.on_windows:
    set_keyring(SecretService)

class CalDAV():
    def __init__(self, reminders):
        self.users = {}
        self.principals = {}
        self.reminders = reminders
        self.load_users()
        try:
            self.get_principals()
        except:
            pass

    def get_principals(self):
        logout = []
        for user_id in self.users.keys():
            url = self.users[user_id]['url']
            username = self.users[user_id]['username']
            password = self.users[user_id]['password']
            try:
                self.principals[user_id] = DAVClient(url, None, username, password, timeout=5).principal()
            except (ConnectionError, Timeout) as error:
                raise error
            except:
                logout.append(user_id)

        for user_id in logout:
            self.reminders.logout(user_id)

    def store(self):
        if len(self.users.keys()) > 0:
            set_password('caldav', 'users', dumps(self.users))

    def load_users(self):
        try:
            self.users = loads(get_password('caldav', 'users'))
            for i, value in self.users.items():
                for key in ('name', 'url', 'username', 'password'):
                    if key not in value.keys():
                        self.users.pop(i)
                        break
        except:
            self.users = {}

    def login(self, name, url, username, password):
        user_id = self.reminders._do_generate_id()
        if username == '':
            username = None
        if password == '':
            password = None
        self.principals[user_id] = DAVClient(url, None, username, password).principal()
        self.users[user_id] = {
            'name': name,
            'url': url,
            'username': username,
            'password': password
        }
        self.store()
        return user_id

    def logout(self, user_id):
        self.users.pop(user_id)
        try:
            self.principals[user_id].client.close()
            self.principals.pop(user_id)
        except:
            pass

        if self.users == {}:
            delete_password('caldav', 'users')
        else:
            self.store()

    def create_task(self, user_id, task_list, task):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=task_list)
                todo = calendar.save_todo(**task)
                task_id = todo.icalendar_component.get('UID', None)
                return task_id
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def update_task(self, user_id, task_list, task_id, task):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=task_list)
                todo = calendar.object_by_uid(task_id, comp_class=Todo)

                i = todo.icalendar_component
                for key, value in task.items():
                    i.pop(key, None)
                    if value is not None:
                        i.add(key, value)
                todo.save()
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def complete_recurring(self, todo, completion_timestamp):
        # from https://github.com/python-caldav/caldav/blob/v1.2.1/caldav/objects.py#L2492
        if not todo._reduce_count():
            return todo.complete(handle_rrule=False)
        next_dtstart = todo._next(completion_timestamp)
        if not next_dtstart:
            return todo.complete(handle_rrule=False)

        completed = todo.copy()
        completed.url = todo.parent.url.join(completed.id + ".ics")
        completed.save()
        completed.complete(handle_rrule=False)

        duration = todo.get_duration()
        i = todo.icalendar_component
        i.pop("DTSTART", None)
        i.add("DTSTART", next_dtstart)
        todo.set_duration(duration, movable_attr="DUE")

        todo.save()

        return completed.icalendar_component.get('UID', None)

    def complete_task(self, user_id, task_list, task_id, completed_timestamp):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=task_list)
                now = datetime.datetime.fromtimestamp(completed_timestamp, tz=datetime.timezone.utc)
                todo = calendar.object_by_uid(task_id, comp_class=Todo)

                new_id = None
                rrule = todo.icalendar_component.get('RRULE', None)
                if rrule is not None:
                    new_id = self.complete_recurring(todo, now)
                else:
                    todo.complete(handle_rrule=False)
                return new_id, todo.icalendar_component
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def incomplete_task(self, user_id, task_list, task_id):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=task_list)
                todo = calendar.object_by_uid(task_id, comp_class=Todo)
                todo.uncomplete()
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def remove_task(self, user_id, task_list, task_id):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=task_list)
                todo = calendar.object_by_uid(task_id, comp_class=Todo)
                todo.delete()
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def create_list(self, user_id, list_name):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].make_calendar(name=list_name, supported_calendar_component_set=['VTODO'])
                return calendar.id
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def update_list(self, user_id, calendar_id, list_name):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=calendar_id)
                calendar.set_properties([DisplayName(list_name)])
                calendar.save()
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def delete_list(self, user_id, calendar_id):
        if user_id not in self.principals:
            self.get_principals()

        if user_id in self.principals:
            try:
                calendar = self.principals[user_id].calendar(cal_id=calendar_id)
                calendar.delete()
            except HTTPError as error:
                if error.response.status_code == 503:
                    raise error
                else:
                    logger.exception(error)
                    raise error
            except (ConnectionError, Timeout) as error:
                raise error
            except Exception as error:
                logger.exception(error)
                raise error
        else:
            raise ConnectionError

    def get_lists(self, removed_list_ids, old_lists, synced_ids):
        task_lists = {}
        not_synced = []

        try:
            if self.users.keys() != self.principals.keys():
                self.get_principals()
        except:
            pass

        for user_id in self.users.keys():
            if user_id not in self.principals.keys():
                not_synced.append(user_id)
                continue
            try:
                task_lists[user_id] = []
                for calendar in self.principals[user_id].calendars():
                    if 'VTODO' not in calendar.get_supported_components():
                        continue
                    list_uid = calendar.url.strip('/').rsplit('/', 1)[-1]

                    if list_uid in removed_list_ids:
                        continue

                    list_id = None
                    try:
                        for task_list_id, value in old_lists.items():
                            if value['uid'] == list_uid and value['user-id'] == user_id:
                                list_id = task_list_id
                    except:
                        pass

                    if list_id is None:
                        list_id = self.reminders._do_generate_id()

                    if user_id not in synced_ids and list_id not in synced_ids:
                        tasks = []
                    else:
                        tasks = calendar.todos(include_completed=True)

                    task_lists[user_id].append({
                        'id': list_id,
                        'uid': list_uid,
                        'name': calendar.get_display_name(),
                        'tasks': tasks
                    })
            except HTTPError as error:
                if error.response.status_code == 503:
                    not_synced.append(user_id)
                else:
                    logger.exception(error)
                    not_synced.append(user_id)
            except (ConnectionError, Timeout):
                not_synced.append(user_id)
            except Exception as error:
                logger.exception(error)
                not_synced.append(user_id)

        return task_lists, not_synced

    def reminder_to_task(self, reminder, exporting = False, completed = None, completed_timestamp = None):
        task = {}
        task['SUMMARY'] = reminder['title']
        task['DESCRIPTION'] = reminder['description']

        task['PRIORITY'] = 1 if reminder['important'] else 0

        if reminder['timestamp'] != 0:
            task['DTSTART'] = task['DUE'] = datetime.datetime.fromtimestamp(reminder['timestamp'], tz=datetime.timezone.utc)
        elif reminder['due-date'] != 0:
            task['DTSTART'] = task['DUE'] = datetime.datetime.fromtimestamp(reminder['due-date'], tz=datetime.timezone.utc).date()
        else:
            task['DTSTART'] = task['DUE'] = None

        task['LAST-MODIFIED'] = datetime.datetime.fromtimestamp(reminder['updated-timestamp'], tz=datetime.timezone.utc)

        if exporting:
            task['STATUS'] = 'COMPLETED' if reminder['completed'] else 'NEEDS-ACTION'
            task['DTSTAMP'] = datetime.datetime.fromtimestamp(reminder['updated-timestamp'], tz=datetime.timezone.utc)
            if reminder['completed-timestamp'] != 0:
                task['COMPLETED'] = datetime.datetime.fromtimestamp(reminder['completed-timestamp'], tz=datetime.timezone.utc)
            elif reminder['completed-date'] != 0:
                task['COMPLETED'] = datetime.datetime.fromtimestamp(reminder['completed-date'], tz=datetime.timezone.utc)
        elif completed is not None:
            task['STATUS'] = 'COMPLETED' if completed else 'NEEDS-ACTION'
            if completed_timestamp is not None:
                task['COMPLETED'] = datetime.datetime.fromtimestamp(completed_timestamp, tz=datetime.timezone.utc) if completed_timestamp != 0 else None

        if reminder['repeat-type'] != 0:
            task['RRULE'] = {}
            if reminder['repeat-type'] == info.RepeatType.MINUTE:
                task['RRULE']['FREQ'] = 'MINUTELY'
            elif reminder['repeat-type'] == info.RepeatType.HOUR:
                task['RRULE']['FREQ'] = 'HOURLY'
            elif reminder['repeat-type'] == info.RepeatType.DAY:
                task['RRULE']['FREQ'] = 'DAILY'
            elif reminder['repeat-type'] == info.RepeatType.WEEK:
                task['RRULE']['FREQ'] = 'WEEKLY'
            elif reminder['repeat-type'] == info.RepeatType.WEEK:
                task['RRULE']['FREQ'] = 'MONTHLY'
            elif reminder['repeat-type'] == info.RepeatType.WEEK:
                task['RRULE']['FREQ'] = 'YEARLY'

            if reminder['repeat-frequency'] != 1:
                task['RRULE']['INTERVAL'] = reminder['repeat-frequency']

            if reminder['repeat-times'] != -1:
                task['RRULE']['COUNT'] = reminder['repeat-times']

            if reminder['repeat-until'] != 0:
                task['RRULE']['UNTIL'] = datetime.datetime.fromtimestamp(reminder['repeat-until'], tz=datetime.timezone.utc).date()

            if reminder['repeat-type'] == info.RepeatType.WEEK:
                repeat_days = []
                if reminder['repeat-days'] == 0:
                    if reminder['timestamp'] != 0:
                        repeat_days.append(DAYS[datetime.datetime.fromtimestamp(reminder['timestamp'], tz=datetime.timezone.utc).date().weekday()])
                    else:
                        repeat_days.append(DAYS[datetime.datetime.fromtimestamp(reminder['due-date'], tz=datetime.timezone.utc).date().weekday()])
                else:
                    repeat_days_flag = info.RepeatDays(reminder['repeat-days'])
                    for index, flag in enumerate((
                        info.RepeatDays.MON,
                        info.RepeatDays.TUE,
                        info.RepeatDays.WED,
                        info.RepeatDays.THU,
                        info.RepeatDays.FRI,
                        info.RepeatDays.SAT,
                        info.RepeatDays.SUN
                    )):
                        if flag in repeat_days_flag:
                            repeat_days.append(DAYS[index])

                task['RRULE']['BYDAY'] = repeat_days
                task['RRULE']['WKST'] = 'SU' if self.reminders.app.settings.get_boolean('week-starts-sunday') else 'MO'
        else:
            task['RRULE'] = None

        return task

    def task_to_reminder(self, ical_todo, list_id, reminder = None, timestamp = None, due_date = None):
        if reminder is None:
            reminder = Reminder()
        if timestamp is None or due_date is None:
            due_date = 0
            timestamp = 0
            due = ical_todo.get('DUE', None)
            if due is not None:
                due = due.dt
                try:
                    if isinstance(due, datetime.datetime):
                        timestamp = int(due.timestamp())
                    elif isinstance(due, datetime.date):
                        due_date = datetime.datetime.combine(due, datetime.time(), tzinfo=datetime.timezone.utc).timestamp()
                except:
                    pass

        reminder['uid'] = ical_todo.get('UID', None)
        reminder['important'] = ical_todo.get('PRIORITY', None) == 1
        summary = ical_todo.get('SUMMARY', None)
        reminder['title'] = summary if summary is not None else ''
        description = ical_todo.get('DESCRIPTION', None)
        reminder['description'] = description if description is not None else ''
        reminder['completed'] = ical_todo.get('STATUS', None) == 'COMPLETED'
        reminder['timestamp'] = timestamp
        try:
            if timestamp == 0:
                reminder['due-date'] = due_date
            else:
                notif_date = datetime.date.fromtimestamp(reminder['timestamp'])
                reminder['due-date'] = int(datetime.datetime(notif_date.year, notif_date.month, notif_date.day, tzinfo=datetime.timezone.utc).timestamp())
            created = ical_todo.get('DTSTAMP', None)
            if reminder['created-timestamp'] == 0 and created is not None:
                reminder['created-timestamp'] = int(created.dt.timestamp())
            modified = ical_todo.get('LAST-MODIFIED', None)
            if modified is not None:
                reminder['updated-timestamp'] = int(modified.dt.timestamp())
            completed = ical_todo.get('COMPLETED', None)
            if completed is not None:
                reminder['completed-timestamp'] = int(completed.dt.timestamp())
                reminder['completed-date'] = int(datetime.datetime.combine(datetime.date.fromtimestamp(completed.dt.timestamp()), datetime.time(), tzinfo=datetime.timezone.utc).timestamp())
        except:
            pass

        reminder['list-id'] = list_id

        rrule = ical_todo.get('RRULE', None)
        if rrule is not None:
            freq = rrule.get('FREQ', None)
            if freq == 'MINUTELY' or 'MINUTELY' in freq:
                reminder['repeat-type'] = int(info.RepeatType.MINUTE)
            elif freq == 'HOURLY' or 'HOURLY' in freq:
                reminder['repeat-type'] = int(info.RepeatType.HOUR)
            elif freq == 'DAILY' or 'DAILY' in freq:
                reminder['repeat-type'] = int(info.RepeatType.DAY)
            elif freq == 'WEEKLY' or 'WEEKLY' in freq:
                reminder['repeat-type'] = int(info.RepeatType.WEEK)
            elif freq == 'MONTHLY' or 'MONTHLY' in freq:
                reminder['repeat-type'] = int(info.RepeatType.MONTH)
            elif freq == 'YEARLY' or 'YEARLY' in freq:
                reminder['repeat-type'] = int(info.RepeatType.YEAR)
            else:
                return reminder

            try:
                until = rrule.get('UNTIL', None)
                if until is not None:
                    until = until.dt
                    if isinstance(until, datetime.datetime):
                        reminder['repeat-until'] = int(until.timestamp())
                    elif isinstance(until, datetime.date):
                        reminder['repeat-until'] = int(datetime.datetime.combine(until, datetime.time(), tzinfo=datetime.timezone.utc).timestamp())
            except:
                pass

            count = rrule.get('COUNT', None)
            reminder['repeat-times'] = count if count is not None else -1

            interval = rrule.get('INTERVAL', None)
            reminder['repeat-frequency'] = interval if interval is not None else 1

            days = rrule.get('BYDAY', None)
            if days is not None:
                reminder['repeat-days'] = 0
                flags = list(info.RepeatDays.__members__.values())

                for day in days:
                    index = DAYS.index(day)
                    reminder['repeat-days'] += int(flags[index])

        return reminder
