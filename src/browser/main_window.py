# main_window.py
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
import time
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, GObject, Gdk
from gettext import gettext as _
from difflib import SequenceMatcher
from math import floor, ceil

from remembrance import info
from remembrance.browser.reminder import Reminder
from remembrance.browser.calendar import Calendar
from remembrance.browser.edit_lists_window import EditListsWindow
from remembrance.browser.reminder_edit_window import ReminderEditWindow

ALL_LABEL = _('All Lists')

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/main_window.ui')
class MainWindow(Adw.ApplicationWindow):
    '''Main application Window'''
    __gtype_name__ = 'application_window'

    page_label = Gtk.Template.Child()
    app_menu_button = Gtk.Template.Child()
    main_box = Gtk.Template.Child()
    reminders_list = Gtk.Template.Child()
    sidebar_list = Gtk.Template.Child()
    add_reminder = Gtk.Template.Child()
    all_row = Gtk.Template.Child()
    upcoming_row = Gtk.Template.Child()
    past_row = Gtk.Template.Child()
    completed_row = Gtk.Template.Child()
    sort_button = Gtk.Template.Child()
    flap = Gtk.Template.Child()
    flap_button_revealer = Gtk.Template.Child()
    search_revealer = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    task_list_picker = Gtk.Template.Child()
    page_sub_label = Gtk.Template.Child()
    spinner = Gtk.Template.Child()

    def __init__(self, page: str, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.placeholder = Adw.ActionRow(
            title=_('Press the plus button below to add a reminder')
        )

        self.search_placeholder = Adw.ActionRow(
            title=_('No reminders match your search')
        )
        self.set_title(info.app_name)
        self.set_icon_name(info.app_id)
        self.dropdown_connection = None
        self.reminder_edit_win = None
        self.edit_lists_window = None
        self.spinning_cursor = Gdk.Cursor.new_from_name('wait')

        self.app = app
        self.selected_user_id, self.selected_list_id = self.app.settings.get_value('selected-task-list').unpack()
        self.set_time_format()

        self.create_action('all', lambda *args: self.all_reminders())
        self.create_action('upcoming', lambda *args: self.upcoming_reminders())
        self.create_action('past', lambda *args: self.past_reminders())
        self.create_action('completed', lambda *args: self.completed_reminders())
        self.create_action('search', lambda *args: self.search_revealer.set_reveal_child(True), accels=['<Ctrl>f'])
        self.create_action('edit-task-lists', lambda *args: self.edit_lists(), accels=['<Ctrl>l'])
        self.create_action('new-reminder', lambda *args: self.new_reminder(), accels=['<Ctrl>n'])
        self.search_entry.connect('stop-search', lambda *args: self.search_revealer.set_reveal_child(False))
        self.settings_create_action('sort')
        self.settings_create_action('descending-sort')
        self.settings_create_action('selected-task-list')
        self.app.settings.connect('changed::sort', self.set_sort)
        self.app.settings.connect('changed::descending-sort', self.set_sort_direction)

        self.activate_action('win.' + page, None)

        self.set_completed_last()
        self.set_completed_reversed()
        self.app.settings.connect('changed::completed-last', self.set_completed_last)
        self.app.settings.connect('changed::completed-reversed', self.set_completed_reversed)
        self.app.settings.connect('changed::selected-task-list', lambda *args: self.update_task_list())

        self.app.service.connect('g-signal::MSSignedIn', self.signed_in_cb)
        self.app.service.connect('g-signal::MSSignedOut', self.signed_out_cb)

        self.descending_sort = self.app.settings.get_boolean('descending-sort')
        self.sort = self.app.settings.get_enum('sort')
        self.sort_button.set_icon_name('view-sort-descending-symbolic' if self.descending_sort else 'view-sort-ascending-symbolic')

        self.reminders_list.set_placeholder(self.placeholder)
        self.reminders_list.set_sort_func(self.sort_func)

        self.reminder_lookup_dict = {}
        self.calendar = Calendar(self.app)

        self.app.settings.connect('changed::synced-task-lists', lambda *args : self.set_synced_ids())

        self.emails = self.app.run_service_method('MSGetEmails', None).unpack()[0]

        self.all_task_list_names = self.app.run_service_method('ReturnLists', None).unpack()[0]
        self.set_synced_ids()

        reminders = self.app.run_service_method('ReturnReminders', None).unpack()[0]
        self.unpack_reminders(reminders)

        self.app.settings.connect('changed::time-format', lambda *args: self.set_time_format())
        self.set_application(self.app)

    @GObject.Property(type=int)
    def time_format(self):
        return self._time_format

    @time_format.setter
    def time_format(self, value):
        self._time_format = value

    def set_busy(self, busy, win = None):
        if win is None:
            win = self
        if busy:
            win.get_native().get_surface().set_cursor(self.spinning_cursor)
            self.app.mark_busy()
        else:
            win.get_native().get_surface().set_cursor(None)
            self.app.unmark_busy()

    def new_edit_win(self, reminder = None):
        if self.reminder_edit_win is None:
            self.reminder_edit_win = ReminderEditWindow(self, self.app, reminder)
            self.reminder_edit_win.present()
            self.reminder_edit_win.connect('close-request', self.close_edit_win)
        else:
            self.reminder_edit_win.setup(reminder)
            self.reminder_edit_win.set_visible(True)

    def close_edit_win(self, window = None):
        if self.reminder_edit_win.check_changed(self.reminder_edit_win.get_options()):
            confirm_dialog = Adw.MessageDialog(
                transient_for=self.reminder_edit_win,
                heading=_('You have unsaved changes'),
                body=_('Are you sure you want to close the window?'),
            )
            confirm_dialog.add_response('cancel', _('Cancel'))
            confirm_dialog.add_response('yes', _('Yes'))
            confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
            confirm_dialog.set_default_response('cancel')
            confirm_dialog.set_close_response('cancel')
            confirm_dialog.connect('response::yes', lambda *args: self.reminder_edit_win.set_visible(False))
            confirm_dialog.present()
            return True
        else:
            self.reminder_edit_win.set_visible(False)

    def get_repeat_label(self, repeat_type, repeat_frequency, repeat_days, repeat_until, repeat_times):
        repeat_days_flag = info.RepeatDays(repeat_days)
        suffix = ''
        time = None
        if repeat_type == 0:
            return _('Does not repeat')
        if repeat_type == info.RepeatType.MINUTE:
            if repeat_frequency == 1:
                type_name = _('minute')
            else:
                type_name = repeat_frequency + ' ' + _('minutes')
        elif repeat_type == info.RepeatType.HOUR:
            if repeat_frequency == 1:
                type_name = _('hour')
            else:
                type_name = repeat_frequency + ' ' + _('hours')
        elif repeat_type == info.RepeatType.DAY:
            if repeat_frequency == 1:
                type_name = _('day')
            else:
                type_name = repeat_frequency + ' ' + _('days')
        elif repeat_type == info.RepeatType.WEEK:
            days = []
            for day, flag in (
                # Translators: This is an abbreviation for Monday
                (_('M'), info.RepeatDays.MON),
                # Translators: This is an abbreviation for Tuesday
                (_('Tu'), info.RepeatDays.TUE),
                # Translators: This is an abbreviation for Wednesday
                (_('W'), info.RepeatDays.WED),
                # Translators: This is an abbreviation for Thursday
                (_('Th'), info.RepeatDays.THU),
                # Translators: This is an abbreviation for Friday
                (_('F'), info.RepeatDays.FRI),
                # Translators: This is an abbreviation for Saturday
                (_('Sa'), info.RepeatDays.SAT),
                # Translators: This is an abbreviation for Sunday
                (_('Su'), info.RepeatDays.SUN)
            ):
                if flag in repeat_days_flag:
                    days.append(day)

            if repeat_frequency == 1:
                type_name = _('week')
            else:
                type_name = str(repeat_frequency) + ' ' + _('weeks')

            suffix = f" ({','.join(days)})"

        if repeat_until > 0:
            date = GLib.DateTime.new_from_unix_local(repeat_until).format('%x')
            suffix += ' ' + _('until') + ' ' + date
        elif repeat_times == 1:
            # Translators: This is a noun, preceded by a number to represent the number of occurrences of something
            time = _('time')
        elif repeat_times != -1:
            # Translators: This is a noun, preceded by a number to represent the number of occurrences of something
            time = _('times')
        if time is not None:
            suffix += f' ({repeat_times} {time})'

        # Translators: This is a adjective, followed by a number to represent how often something occurs
        return _('Every') + f' {type_name}{suffix}'

    def set_time_format(self):
        setting = self.app.settings.get_enum('time-format')
        if setting == 0:
            if time.strftime('%p'):
                self.set_twelve_hour()
            else:
                self.set_twentyfour_hour()
        elif setting == 1:
            self.set_twelve_hour()
        elif setting == 2:
            self.set_twentyfour_hour()

    def set_twelve_hour(self):
        self.set_property('time-format', info.TimeFormat.TWELVE_HOUR)

    def set_twentyfour_hour(self):
        self.set_property('time-format', info.TimeFormat.TWENTYFOUR_HOUR)

    def get_datetime_label(self, timestamp):
        time = GLib.DateTime.new_from_unix_local(timestamp)

        return f'{self.get_date_label(time)} {self.get_time_label(time)}'

    def get_date_label(self, time):
        reminder_day = time.get_day_of_year()
        reminder_week = time.get_week_of_year()
        reminder_year = time.get_year()
        now = GLib.DateTime.new_now_local()
        today = now.get_day_of_year()
        week = now.get_week_of_year()
        year = now.get_year()

        if reminder_day == today:
            date = _('Today')
        elif reminder_day == today + 1:
            date = _('Tomorrow')
        elif reminder_day == today - 1:
            date = _('Yesterday')
        elif reminder_week == week:
            date = time.format('%A')
        elif reminder_year == year:
            date = time.format('%d %B')
        else:
            date = time.format('%d %B %Y')
        return date

    def get_time_label(self, time):
        if self.props.time_format == info.TimeFormat.TWELVE_HOUR:
            time = time.format("%I:%M %p")
        else:
            time = time.format('%H:%M')
        return time

    def edit_lists(self):
        if self.edit_lists_window is None:
            self.edit_lists_window = EditListsWindow(self)
            self.edit_lists_window.present()
        else:
            self.edit_lists_window.set_visible(True)

    def filter_reminders(self, action, variant, data = None):
        self.selected_user_id, self.selected_list_id = variant.unpack()
        self.app.settings.set_value('selected-task-list', GLib.Variant('(ss)', (self.selected_user_id, self.selected_list_id)))

    def set_synced_ids(self):
        self.synced_ids = self.app.settings.get_value('synced-task-lists').unpack()
        self.set_task_list_dropdown()

    def signed_out_cb(self, proxy, sender_name, signal_name, parameters):
        user_id = parameters.unpack()[0]
        self.emails.pop(user_id)

    def signed_in_cb(self, proxy, sender_name, signal_name, parameters):
        user_id, email = parameters.unpack()
        self.emails[user_id] = email

    def update_task_list(self):
        self.selected_user_id, self.selected_list_id = self.app.settings.get_value('selected-task-list').unpack()
        if self.selected_list_id == 'all':
            self.task_list_picker.set_label(ALL_LABEL)
        else:
            try:
                self.task_list_picker.set_label(self.all_task_list_names[self.selected_user_id][self.selected_list_id])
            except:
                self.app.settings.set_value('selected-task-list', GLib.Variant('(ss)', ('all', 'all')))
                return

        self.reminders_list.invalidate_filter()
        self.reminders_list.invalidate_sort()

    def list_updated(self, user_id, list_id, list_name):
        if user_id not in self.all_task_list_names.keys():
            self.all_task_list_names[user_id] = {}
        self.all_task_list_names[user_id][list_id] = list_name

        if user_id == 'local' or (user_id in self.synced_ids and ('all' in self.synced_ids[user_id] or list_id in self.synced_ids[user_id])):
            if user_id not in self.task_list_names.keys():
                self.task_list_names[user_id] = {}
            self.task_list_names[user_id][list_id] = list_name
            if user_id not in self.menuitems.keys():
                self.menuitems[user_id] = {}
                self.sections[user_id] = Gio.Menu()
                self.task_list_menu.append_section(self.emails[user_id], self.sections[user_id])
            if list_id not in self.menuitems[user_id]:
                item = Gio.MenuItem.new(list_name, 'win.selected-task-list')
                item.set_attribute_value(Gio.MENU_ATTRIBUTE_TARGET, GLib.Variant('(ss)', (user_id, list_id)))
                self.sections[user_id].append_item(item)
                self.menuitems[user_id][list_id] = item
            else:
                self.menuitems[user_id][list_id].set_label(list_name)

            self.set_reminder_task_list_dropdown()

    def list_removed(self, user_id, list_id):
        for dictionary in self.all_task_list_names, self.task_list_names:
            try:
                dictionary[user_id].pop(list_id)
            except:
                pass
        self.set_task_list_dropdown()

    def set_task_list_dropdown(self):
        self.task_list_names = {}
        for user_id in self.all_task_list_names.keys():
            if user_id not in self.task_list_names.keys():
                self.task_list_names[user_id] = {}
            for key, value in self.all_task_list_names[user_id].items():
                if user_id == 'local' or (user_id in self.synced_ids and ('all' in self.synced_ids[user_id] or key in self.synced_ids[user_id])):
                    self.task_list_names[user_id][key] = value

        self.task_list_menu = Gio.Menu()
        all_item = Gio.MenuItem.new(ALL_LABEL, 'win.selected-task-list')
        all_item.set_attribute_value(Gio.MENU_ATTRIBUTE_TARGET, GLib.Variant('(ss)', ('all', 'all')))
        self.task_list_menu.append_item(all_item)

        self.sections = {}
        self.menuitems = {}
        for user_id in self.task_list_names.keys():
            if user_id in self.emails or user_id == 'local':
                self.sections[user_id] = Gio.Menu()
                for list_id, name in self.task_list_names[user_id].items():
                    item = Gio.MenuItem.new(name, 'win.selected-task-list')
                    item.set_attribute_value(Gio.MENU_ATTRIBUTE_TARGET, GLib.Variant('(ss)', (user_id, list_id)))
                    self.sections[user_id].append_item(item)
                    if user_id not in self.menuitems.keys():
                        self.menuitems[user_id] = {}
                    self.menuitems[user_id][list_id] = item
                self.task_list_menu.append_section(_('Local') if user_id == 'local' else self.emails[user_id], self.sections[user_id])
        self.task_list_picker.set_menu_model(self.task_list_menu)
        self.set_reminder_task_list_dropdown()

        self.update_task_list()

    def set_reminder_task_list_dropdown(self):
        self.string_list = Gtk.StringList()
        self.task_list_ids = []
        duplicated = []
        values = []
        for dictionary in self.task_list_names.values():
            for i in dictionary.values():
                if i in values:
                    duplicated.append(i)
                else:
                    values.append(i)

        for user_id in self.task_list_names.keys():
            for list_id, name in self.task_list_names[user_id].items():
                if name not in duplicated:
                    self.string_list.append(f'{name}')
                else:
                    self.string_list.append(f'{name} ({self.emails[user_id]})')
                self.task_list_ids.append((list_id, user_id))

        if self.reminder_edit_win is not None:
            self.reminder_edit_win.set_task_list_dropdown()

    def unpack_reminders(self, reminders):
        for reminder in reminders:
            if 'error' in reminder:
                raise Exception

            self.display_reminder(**reminder)

    def set_completed_last(self, key = None, data = None):
        self.completed_last = self.app.settings.get_boolean('completed-last')
        self.reminders_list.invalidate_sort()

    def set_completed_reversed(self, key = None, data = None):
        self.completed_reversed = self.app.settings.get_boolean('completed-reversed')
        self.reminders_list.invalidate_sort()

    def set_sort(self, key = None, data = None):
        self.sort = self.app.settings.get_enum('sort')
        self.reminders_list.invalidate_sort()

    def set_sort_direction(self, key = None, data = None):
        self.descending_sort = self.app.settings.get_boolean('descending-sort')
        self.sort_button.set_icon_name('view-sort-descending-symbolic' if self.descending_sort else 'view-sort-ascending-symbolic')
        self.reminders_list.invalidate_sort()

    def get_kwarg(self, kwargs, key, default = None):
        if key in kwargs:
            return kwargs[key]
        elif default is not None:
            return default
        else:
            raise KeyError

    def display_reminder(self, **kwargs):
        reminder_id = self.get_kwarg(kwargs, 'id')
        title = self.get_kwarg(kwargs, 'title')
        description = self.get_kwarg(kwargs, 'description')
        timestamp = self.get_kwarg(kwargs, 'timestamp')
        completed = self.get_kwarg(kwargs, 'completed', False)
        repeat_type = self.get_kwarg(kwargs, 'repeat-type', 0)
        repeat_frequency = self.get_kwarg(kwargs, 'repeat-frequency', 1)
        repeat_days = self.get_kwarg(kwargs, 'repeat-days', 0)
        repeat_times = self.get_kwarg(kwargs, 'repeat-times')
        repeat_until = self.get_kwarg(kwargs, 'repeat-until', 0)
        old_timestamp = self.get_kwarg(kwargs, 'old-timestamp', 0)
        task_list = self.get_kwarg(kwargs, 'list', 'local')
        user_id = self.get_kwarg(kwargs, 'user-id', 'local')

        if reminder_id not in self.reminder_lookup_dict.keys():
            reminder = Reminder(
                self,
                {
                    'title': title,
                    'description': description,
                    'timestamp': timestamp,
                    'repeat-type': repeat_type,
                    'repeat-frequency': repeat_frequency,
                    'repeat-days': repeat_days,
                    'repeat-until': repeat_until,
                    'repeat-times': repeat_times,
                    'old-timestamp': old_timestamp,
                    'list': task_list,
                    'user-id': user_id 
                },
                reminder_id,
                completed
            )

            self.reminders_list.append(reminder)

            self.reminder_lookup_dict[reminder_id] = reminder

    def update_list(self, user_id, list_name, list_id = None):
        retval = list_id
        if list_id is None:
            retval = self.app.run_service_method(
                'CreateList',
                GLib.Variant('(sss)', (info.app_id, user_id, list_name))
            ).unpack()[0]
        else:
            self.app.run_service_method(
                'RenameList',
                GLib.Variant('(ssss)', (info.app_id, user_id, list_id, list_name))
            )
        return retval

    def delete_list(self, user_id, list_id):
        self.app.run_service_method(
            'RemoveList',
            GLib.Variant('(sss)', (info.app_id, user_id, list_id))
        )

    def sign_out(self, user_id):
        self.app.run_service_method('MSLogout', GLib.Variant('(s)', (user_id,)), False)

    def sign_in(self):
        self.app.run_service_method('MSLogin', None, False)

    def create_action(self, name, callback, variant = None, accels = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        if accels is not None:
            self.app.set_accels_for_action('win.' + name, accels)
        self.add_action(action)

    def settings_create_action(self, name):
        action = self.app.settings.create_action(name)
        self.add_action(action)

    def task_list_filter(self, user_id, task_list):
        if self.selected_list_id == 'all':
            return True
        else:
            return user_id == self.selected_user_id and task_list == self.selected_list_id

    def no_filter(self, reminder):
        reminder.set_sensitive(True)
        return True

    def all_filter(self, reminder):
        reminder.set_past(False)
        retval = self.task_list_filter(reminder.options['user-id'], reminder.options['list'])
        reminder.set_sensitive(retval)
        return retval

    def upcoming_filter(self, reminder):
        now = floor(time.time())
        if reminder.options['timestamp'] == 0 or (reminder.options['timestamp'] > now and not reminder.completed):
            retval = self.task_list_filter(reminder.options['user-id'], reminder.options['list'])
            reminder.set_past(False)
        else:
            retval = False
        reminder.set_sensitive(retval)
        return retval

    def past_filter(self, reminder):
        now = ceil(time.time())
        if reminder.options['old-timestamp'] != 0 and (reminder.options['old-timestamp'] < now and not reminder.completed):
            retval = self.task_list_filter(reminder.options['user-id'], reminder.options['list'])
            reminder.set_past(True)
        else:
            retval = False
        reminder.set_sensitive(retval)
        return retval

    def completed_filter(self, reminder):
        if reminder.completed:
            retval = self.task_list_filter(reminder.options['user-id'], reminder.options['list'])
            reminder.set_past(False)
        else:
            retval = False
        reminder.set_sensitive(retval)
        return retval

    def sort_func(self, row1, row2):
        # sort by timestamp from lowest to highest, showing completed reminders last
        # insensitive rows first as a part of fixing https://gitlab.gnome.org/GNOME/gtk/-/issues/5309
        try:
            if (not row1.get_sensitive() and row2.get_sensitive()):
                return -1
            if (row1.get_sensitive() and not row2.get_sensitive()):
                return 1
            if self.completed_last:
                if (not row1.completed and row2.completed):
                    return -1
                if (row1.completed and not row2.completed):
                    return 1

            if self.sort == 0: # time
                if row1.timestamp == row2.timestamp:
                    return 0

                # if reminders are completed reverse order
                if self.completed_last and self.completed_reversed and row1.completed:
                    should_reverse = (not self.descending_sort)
                else:
                    should_reverse = self.descending_sort

                if row1.timestamp < row2.timestamp:
                    return 1 if should_reverse else -1
                # if row1.timestamp > row2.timestamp
                return -1 if should_reverse else 1

            elif self.sort == 1: # alphabetical
                name1 = (row1.get_title() + row1.get_subtitle()).lower()
                name2 = (row2.get_title() + row2.get_subtitle()).lower()
                if name1 == name2:
                    return 0
                if name1 < name2:
                    return 1 if self.descending_sort else -1
                # if name1 > name2
                return -1 if self.descending_sort else 1
        except:
            return 0

    def all_reminders(self):
        if not self.all_row.is_selected():
            self.sidebar_list.select_row(self.all_row)
        self.reminders_list.set_filter_func(self.all_filter)
        self.page_label.set_label(_('All Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.all_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def upcoming_reminders(self):
        if not self.upcoming_row.is_selected():
            self.sidebar_list.select_row(self.upcoming_row)
        self.reminders_list.set_filter_func(self.upcoming_filter)
        self.page_label.set_label(_('Upcoming Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.upcoming_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def past_reminders(self):
        if not self.past_row.is_selected():
            self.sidebar_list.select_row(self.past_row)
        self.reminders_list.set_filter_func(self.past_filter)
        self.page_label.set_label(_('Past Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.past_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def completed_reminders(self):
        if not self.completed_row.is_selected():
            self.sidebar_list.select_row(self.completed_row)
        self.reminders_list.set_filter_func(self.completed_filter)
        self.page_label.set_label(_('Completed Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.completed_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def stop_search(self):
        self.search_entry.set_text('')
        self.flap.set_fold_policy(Adw.FlapFoldPolicy.AUTO)
        self.reminders_list.set_placeholder(self.placeholder)
        self.reminders_list.set_sort_func(self.sort_func)
        self.selected.emit('activate')
        self.page_sub_label.set_visible(True)

    def search_filter(self, reminder):
        retval = True
        text = self.search_entry.get_text().lower()
        words = text.split()
        reminder_text = reminder.get_title().lower() + ' ' + reminder.get_subtitle().lower()

        for word in words:
            if word not in reminder_text:
                retval = False

        if retval:
            reminder.set_past(False)

        reminder.set_sensitive(retval)

        return retval

    def search_sort_func(self, row1, row2):
        if (not row1.get_sensitive() and row2.get_sensitive()):
            return -1
        if (row1.get_sensitive() and not row2.get_sensitive()):
            return 1
        text = self.search_entry.get_text().lower()
        row1_text = row1.get_title().lower() + ' ' + row1.get_subtitle().lower()
        row2_text = row2.get_title().lower() + ' ' + row2.get_subtitle().lower()

        row1_ratio = SequenceMatcher(a=text, b=row1_text).ratio()
        row2_ratio = SequenceMatcher(a=text, b=row2_text).ratio()

        if row1_ratio == row2_ratio:
            return 0
        elif row1_ratio < row2_ratio:
            return 1
        else:
            return -1

    def start_search(self):
        self.searching = True
        self.sort_button.set_sensitive(False)

        self.reminders_list.set_placeholder(self.search_placeholder)
        self.reminders_list.set_filter_func(self.search_filter)
        self.reminders_list.set_sort_func(self.search_sort_func)

    @Gtk.Template.Callback()
    def show_flap_button(self, flap = None, data = None):
        if self.search_revealer.get_reveal_child():
            self.flap_button_revealer.set_reveal_child(False)
        else:
            self.flap_button_revealer.set_reveal_child(self.flap.get_folded())

    @Gtk.Template.Callback()
    def search_enabled_cb(self, entry, data):
        self.show_flap_button()
        if self.search_revealer.get_reveal_child():
            self.search_changed_cb()
            self.search_entry.grab_focus()
            self.flap.set_fold_policy(Adw.FlapFoldPolicy.ALWAYS)
            self.flap.set_reveal_flap(False)
        else:
            self.stop_search()

    @Gtk.Template.Callback()
    def search_changed_cb(self, entry = False):
        text = self.search_entry.get_text()
        if len(text) > 0:
            if not self.searching:
                self.start_search()
            self.reminders_list.invalidate_filter()
            self.reminders_list.invalidate_sort()
            self.page_label.set_label(_(f"Searching '{text}'"))
            self.page_sub_label.set_visible(False)
        else:
            self.searching = False
            self.sort_button.set_sensitive(True)
            self.reminders_list.set_filter_func(self.no_filter)
            self.reminders_list.set_sort_func(self.sort_func)
            self.page_label.set_label(_('Start typing to search'))
            self.page_sub_label.set_visible(False)

    @Gtk.Template.Callback()
    def new_reminder(self, button = None):
        self.search_revealer.set_reveal_child(False)
        self.selected = self.all_row
        self.selected.emit('activate')
        self.new_edit_win()
