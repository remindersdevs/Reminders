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

from gi import require_version
require_version('Gtk', '4.0')
require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, GObject, Gdk

from remembrance import info
from remembrance.browser.reminder import Reminder
from remembrance.browser.calendar import Calendar
from remembrance.browser.edit_lists_window import EditListsWindow
from remembrance.browser.reminder_edit_window import ReminderEditWindow
from remembrance.browser.move_reminders_window import MoveRemindersWindow
from time import time, strftime
from logging import getLogger
from gettext import gettext as _
from difflib import SequenceMatcher
from math import floor, ceil

logger = getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/task_list_row.ui')
class TaskListRow(Gtk.ListBoxRow):
    __gtype_name__ = 'TaskListRow'
    label = Gtk.Template.Child()
    icon = Gtk.Template.Child()
    count_label = Gtk.Template.Child()

    def __init__(self, label, user_id, list_id, icon = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_id = list_id
        self.user_id = user_id
        self.set_action_target_value(GLib.Variant('s', list_id))

        if icon is not None:
            self.icon.set_from_icon_name(icon)

        self.label.set_label(label)

    def set_count(self, count):
        self.count_label.set_visible(count != 0)
        self.count_label.set_label(str(count))

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/main_window.ui')
class MainWindow(Adw.ApplicationWindow):
    '''Main application Window'''
    __gtype_name__ = 'MainWindow'

    page_label = Gtk.Template.Child()
    page_sub_label = Gtk.Template.Child()
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
    task_lists_list = Gtk.Template.Child()
    label_revealer = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    add_reminder_revealer = Gtk.Template.Child()
    multiple_select_revealer = Gtk.Template.Child()
    incomplete_revealer = Gtk.Template.Child()
    complete_revealer = Gtk.Template.Child()
    unimportant_revealer = Gtk.Template.Child()
    important_revealer = Gtk.Template.Child()
    move_revealer = Gtk.Template.Child()
    all_count_label = Gtk.Template.Child()
    upcoming_count_label = Gtk.Template.Child()
    past_count_label = Gtk.Template.Child()
    completed_count_label = Gtk.Template.Child()

    def __init__(self, page: str, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.placeholder = Adw.ActionRow(
            title=_('Nothing to see here!'),
            subtitle=_('Press the plus button below to add a reminder')
        )
        self.placeholder.add_css_class('card')
        self.search_placeholder = Adw.ActionRow(
            title=_('No reminders match your search')
        )
        self.search_placeholder.add_css_class('card')

        self.set_title(info.app_name)
        self.set_icon_name(info.app_id)
        self.dropdown_connection = None
        self.reminder_edit_win = None
        self.edit_lists_window = None
        self.expanded = None
        self.last_selected_row = None
        self.selected = None

        self.row_filter_pairs = (
            (self.all_row, self.all_filter, self.all_count_label),
            (self.upcoming_row, self.upcoming_filter, self.upcoming_count_label),
            (self.past_row, self.past_filter, self.past_count_label)
        )

        self.app = app
        self.selected_list_id = self.app.settings.get_string('selected-list')
        self.set_time_format()

        self.reminders_list.set_placeholder(self.placeholder)
        self.reminders_list.set_sort_func(self.sort_func)

        self.create_action('all', lambda *args: self.all_reminders())
        self.create_action('upcoming', lambda *args: self.upcoming_reminders())
        self.create_action('past', lambda *args: self.past_reminders())
        self.create_action('completed', lambda *args: self.completed_reminders())
        self.create_action('search', lambda *args: self.search_revealer.set_reveal_child(True), accels=['<Ctrl>f'])
        self.create_action('edit-task-lists', lambda *args: self.edit_lists(), accels=['<Ctrl>l'])
        self.create_action('new-reminder', lambda *args: self.new_reminder(), accels=['<Ctrl>n'])
        self.create_action('select-all', lambda *args: self.select_all(), accels=['<Ctrl>a'])
        self.search_entry.connect('stop-search', lambda *args: self.search_revealer.set_reveal_child(False))
        self.settings_create_action('sort')
        self.settings_create_action('descending-sort')
        self.settings_create_action('selected-list')
        self.app.settings.connect('changed::sort', self.set_sort)
        self.app.settings.connect('changed::descending-sort', self.set_sort_direction)
        self.app.settings.connect('changed::week-starts-sunday', lambda *args: self.week_start_changed())
        self.descending_sort = self.app.settings.get_boolean('descending-sort')
        self.sort = self.app.settings.get_enum('sort')
        self.sort_button.set_icon_name('view-sort-descending-symbolic' if self.descending_sort else 'view-sort-ascending-symbolic')

        self.reminder_lookup_dict = {}
        self.calendar = Calendar(self)

        self.app.service.connect('g-signal::SyncedListsChanged', self.synced_ids_changed)

        users = self.app.run_service_method('GetUsers', None).unpack()[0]

        self.ms_users = users['ms-to-do'].copy()
        self.caldav_users = users['caldav'].copy()

        self.usernames = {}
        for value in users.values():
            for key, value in value.items():
                self.usernames[key] = value

        self.app.service.connect('g-signal::CalDAVSignedIn', self.caldav_signed_in_cb)
        self.app.service.connect('g-signal::MSSignedIn', self.ms_signed_in_cb)
        self.app.service.connect('g-signal::SignedOut', self.signed_out_cb)
        self.app.service.connect('g-signal::UsernameUpdated', self.username_updated)

        self.all_lists = self.app.run_service_method('GetListsDict', None).unpack()[0]
        self.set_synced_ids()
        self.set_task_lists()

        reminders = self.app.run_service_method('GetReminders', None).unpack()[0]
        self.unpack_reminders(reminders)

        self.reminders_list.connect('selected-rows-changed', self.selected_changed)

        key_pressed = Gtk.EventControllerKey()
        key_pressed.connect('key-released', self.key_released)
        self.add_controller(key_pressed)
        self.setup_dnd()

        self.task_lists_list.set_sort_func(self.task_lists_sort_func)
        self.app.settings.connect('changed::time-format', lambda *args: self.set_time_format())
        self.set_application(self.app)

        self.activate_action('win.' + page, None)

    @GObject.Property(type=int)
    def time_format(self):
        return self._time_format

    @time_format.setter
    def time_format(self, value):
        self._time_format = value

    def invalidate_filter(self):
        self.reminders_list.invalidate_filter()
        current_filter = None
        for row, filter_func, count_label in self.row_filter_pairs:
            count = 0
            for reminder in self.reminder_lookup_dict.values():
                if reminder.completed:
                    continue
                result = filter_func(reminder, just_filter = True)
                if result:
                    count += 1
            count_label.set_visible(count != 0)
            count_label.set_label(str(count))
            if self.selected is row:
                current_filter = filter_func

        for list_id, row in self.task_list_rows.items():
            count = 0
            if current_filter is not None:
                for reminder in self.reminder_lookup_dict.values():
                    if reminder.completed:
                        continue
                    result = current_filter(reminder, list_id, just_filter = True)
                    if result:
                        count += 1
            row.set_count(count)

    def setup_dnd(self):
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRV, Gdk.DragAction.MOVE)
        drop_target.connect('enter', self.enter)
        drop_target.connect('motion', self.motion)
        drop_target.connect('leave', self.leave)
        drop_target.connect('drop', self.drop)
        self.task_lists_list.add_controller(drop_target)

    def enter(self, drop_target, x, y):
        row = self.task_lists_list.get_row_at_y(y)
        if row is not None and row.list_id != 'all':
            self.task_lists_list.drag_highlight_row(row)
            return Gdk.DragAction.MOVE
        else:
            self.task_lists_list.drag_unhighlight_row()
            return 0

    def motion(self, drop_target, x, y):
        row = self.task_lists_list.get_row_at_y(y)
        if row is not None and row.list_id != 'all':
            self.task_lists_list.drag_highlight_row(row)
            return Gdk.DragAction.MOVE
        else:
            self.task_lists_list.drag_unhighlight_row()
            return 0

    def leave(self, drop_target):
        self.task_lists_list.drag_unhighlight_row()

    def drop(self, drop_target, values, x, y):
        row = self.task_lists_list.get_row_at_y(y)
        if row is None and row.list_id == 'all':
            self.task_lists_list.drag_unhighlight_row()
            return False
        variants = []
        options = {}
        for reminder_id in values:
            try:
                reminder = self.reminder_lookup_dict[reminder_id]
            except:
                continue
            options[reminder.id] = reminder.options.copy()
            opts = options[reminder.id]
            opts['list-id'] = row.list_id
            if reminder.options['list-id'] != opts['list-id']:
                user_id = self.synced_lists[opts['list-id']]['user-id']
                if user_id in self.ms_users.keys():
                    if opts['repeat-type'] in (1, 2):
                        opts['repeat-type'] = 0
                        opts['repeat-frequency'] = 1
                        opts['repeat-days'] = 0
                    opts['repeat-until'] = 0
                    opts['repeat-times'] = -1

                variants.append({
                    'id': GLib.Variant('s', reminder.id),
                    'repeat-type': GLib.Variant('q', opts['repeat-type']),
                    'repeat-frequency': GLib.Variant('q', opts['repeat-frequency']),
                    'repeat-days': GLib.Variant('q', opts['repeat-days']),
                    'repeat-times': GLib.Variant('n', opts['repeat-times']),
                    'repeat-until': GLib.Variant('u', opts['repeat-until']),
                    'list-id': GLib.Variant('s', opts['list-id'])
                })
            reminder.show()

        results = self.app.run_service_method(
            'UpdateReminderv',
            GLib.Variant(
                '(saa{sv})',
                (
                    info.app_id,
                    variants
                )
            )
        )

        updated_ids, timestamp = results.unpack()
        for reminder_id in updated_ids:
            reminder = self.reminder_lookup_dict[reminder_id]
            options[reminder_id]['updated-timestamp'] = timestamp
            reminder.options.update(options[reminder_id])
            reminder.set_repeat_label()

        self.invalidate_filter()
        self.reminders_list.invalidate_sort()
        self.task_lists_list.drag_unhighlight_row()
        return True

    def week_start_changed(self):
        for reminder in self.reminder_lookup_dict.values():
            reminder.set_time_label()

    def key_released(self, event, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.set_selecting(False)
        if keyval == Gdk.KEY_Delete:
            if self.reminders_list.get_property('selection-mode') != Gtk.SelectionMode.NONE:
                self.selected_remove()

    def set_selecting(self, selecting):
        if selecting:
            if self.reminders_list.get_property('selection-mode') != Gtk.SelectionMode.MULTIPLE:
                self.reminders_list.set_property('selection-mode', Gtk.SelectionMode.MULTIPLE)
                self.add_reminder_revealer.set_reveal_child(False)
                self.multiple_select_revealer.set_reveal_child(True)
                for reminder in self.reminder_lookup_dict.values():
                    reminder.set_enable_expansion(False)
        else:
            if self.reminders_list.get_property('selection-mode') != Gtk.SelectionMode.NONE:
                self.reminders_list.set_property('selection-mode', Gtk.SelectionMode.NONE)
                self.multiple_select_revealer.set_reveal_child(False)
                self.add_reminder_revealer.set_reveal_child(True)
                for reminder in self.reminder_lookup_dict.values():
                    reminder.set_enable_expansion(True)
                    reminder.set_selectable(False)
                    reminder.set_expanded(False)

    def select_all(self):
        self.set_selecting(True)
        for reminder in self.reminder_lookup_dict.values():
            reminder.set_selectable(True)
            if reminder.get_visible():
                self.reminders_list.select_row(reminder)

    def selected_changed(self, list_box = None):
        selected = self.reminders_list.get_selected_rows()
        if len(selected) == 0:
            self.set_selecting(False)
            return

        self.incomplete_revealer.set_reveal_child(False)
        self.complete_revealer.set_reveal_child(False)
        self.unimportant_revealer.set_reveal_child(False)
        self.important_revealer.set_reveal_child(False)

        for reminder in selected:
            if reminder.completed:
                self.incomplete_revealer.set_reveal_child(True)
            else:
                self.complete_revealer.set_reveal_child(True)

            if reminder.options['important']:
                self.unimportant_revealer.set_reveal_child(True)
            else:
                self.important_revealer.set_reveal_child(True)

        self.incomplete_revealer.set_hexpand(self.incomplete_revealer.props.reveal_child)
        self.complete_revealer.set_hexpand(self.complete_revealer.props.reveal_child)
        self.unimportant_revealer.set_hexpand(self.unimportant_revealer.props.reveal_child)
        self.important_revealer.set_hexpand(self.important_revealer.props.reveal_child)

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

            if repeat_days != 0:
                suffix = f" ({','.join(days)})"
        elif repeat_type == info.RepeatType.MONTH:
            if repeat_frequency == 1:
                type_name = _('month')
            else:
                type_name = repeat_frequency + ' ' + _('months')
        elif repeat_type == info.RepeatType.YEAR:
            if repeat_frequency == 1:
                type_name = _('year')
            else:
                type_name = repeat_frequency + ' ' + _('years')
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
            if strftime('%p'):
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

    def get_date_label(self, time, short_date = False):
        reminder_day = time.get_day_of_year()
        reminder_weekday = (time.get_day_of_week()) % 7  if self.app.settings.get_boolean('week-starts-sunday') else time.get_day_of_week() - 1
        reminder_year = time.get_year()
        now = GLib.DateTime.new_now_local()
        today = now.get_day_of_year()
        weekday = (now.get_day_of_week()) % 7  if self.app.settings.get_boolean('week-starts-sunday') else now.get_day_of_week() - 1
        year = now.get_year()

        if reminder_year == year:
            if reminder_day == today:
                return _('Today')
            if reminder_day == today + 1:
                return _('Tomorrow')
            if reminder_day == today - 1:
                return _('Yesterday')
            if abs(reminder_day - today) < 7 and ((reminder_day > today and not reminder_weekday < weekday) or (reminder_day < today and not reminder_weekday > weekday)):
                return time.format('%A')
            if not short_date:
                return time.format("<span allow_breaks='false'>%d %B</span>")

        if short_date:
            return time.format('%x')

        return time.format("<span allow_breaks='false'>%d %B</span> %Y")

    def get_time_label(self, time):
        if self.props.time_format == info.TimeFormat.TWELVE_HOUR:
            time = time.format("<span allow_breaks='false'>%I:%M %p</span>")
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
        self.selected_list_id = variant.unpack()
        self.app.settings.set_string('selected-list', self.selected_list_id)

    def set_synced_ids(self):
        self.synced_ids = self.app.settings.get_value('synced-lists').unpack()

    def synced_ids_changed(self, proxy, sender_name, signal_name, parameters):
        self.synced_ids = parameters.unpack()[0]

        removed_task_lists = []
        new_task_lists = []

        for list_id, value in self.all_lists.items():
            list_name = value['name']
            user_id = value['user-id']
            if user_id == 'local' or (user_id in self.synced_ids or list_id in self.synced_ids):
                if list_id not in self.synced_lists:
                    self.synced_lists[list_id] = self.all_lists[list_id]
                    new_task_lists.append((user_id, list_id, list_name))
            else:
                if list_id in self.synced_lists:
                    self.synced_lists.pop(list_id)
                    removed_task_lists.append(list_id)

        if len(new_task_lists) > 0 or len(removed_task_lists) > 0:
            for user_id, list_id, list_name in new_task_lists:
                self.update_task_list_row(user_id, list_id, list_name)
            for list_id in removed_task_lists:
                self.remove_task_list_row(list_id)

            self.set_reminder_task_list_dropdown()

    def signed_out_cb(self, proxy, sender_name, signal_name, parameters):
        user_id = parameters.unpack()[0]
        self.usernames.pop(user_id)
        if user_id in self.ms_users:
            self.ms_users.pop(user_id)
        if user_id in self.caldav_users:
            self.caldav_users.pop(user_id)
        if self.app.preferences is not None:
            self.app.preferences.on_signed_out(user_id)
        if self.edit_lists_window is not None:
            self.edit_lists_window.signed_out(user_id)

    def ms_signed_in_cb(self, proxy, sender_name, signal_name, parameters):
        user_id, username = parameters.unpack()
        self.usernames[user_id] = username
        self.ms_users[user_id] = username
        if self.app.preferences is not None:
            self.app.preferences.ms_signed_in(user_id, username)
        if self.edit_lists_window is not None:
            self.edit_lists_window.signed_in(user_id, username)

    def caldav_signed_in_cb(self, proxy, sender_name, signal_name, parameters):
        user_id, username = parameters.unpack()
        self.usernames[user_id] = username
        self.caldav_users[user_id] = username
        if self.app.preferences is not None:
            self.app.preferences.caldav_signed_in(user_id, username)
        if self.edit_lists_window is not None:
            self.edit_lists_window.signed_in(user_id, username)

    def update_task_list(self):
        self.selected_list_id = self.app.settings.get_string('selected-list')

        try:
            row = self.task_list_rows[self.selected_list_id]
            if row not in self.task_lists_list.get_selected_rows():
                row.activate()
            self.page_sub_label.set_label(row.label.get_label())
        except:
            self.app.settings.set_string('selected-list', 'all')
            return

        self.invalidate_filter()
        self.reminders_list.invalidate_sort()

    def update_task_list_row(self, user_id, list_id, list_name):
        old_duplicated = self.duplicated.copy()
        self.duplicated = []
        values = {}
        for dictionary in self.synced_lists.values():
            if dictionary['name'] in values and values[dictionary['name']] != dictionary['user-id']:
                self.duplicated.append(dictionary['name'])
            else:
                values[dictionary['name']] = dictionary['user-id']

        duplicated = False
        for task_list_id, dictionary in self.synced_lists.items():
            list_user_id = dictionary['user-id']
            task_list_name = dictionary['name']
            if user_id == list_user_id:
                continue
            if list_name == task_list_name:
                duplicated = True
                if task_list_id in self.task_list_rows:
                    label = f"{task_list_name} ({self.usernames[list_user_id]})"
                    self.task_list_rows[task_list_id].label.set_label(label)

        for name in old_duplicated:
            if name not in self.duplicated:
                for task_list_id, dictionary in self.synced_lists.items():
                    task_list_name = dictionary['name']
                    if task_list_name == name:
                        self.task_list_rows[task_list_id].label.set_label(name)

        label = f"{list_name} ({self.usernames[user_id]})" if duplicated else list_name

        if list_id in self.task_list_rows:
            self.task_list_rows[list_id].label.set_label(label)
        else:
            row = TaskListRow(label, user_id, list_id)
            self.task_lists_list.append(row)
            self.task_list_rows[list_id] = row
            self.task_lists_list.invalidate_sort()

    def username_updated(self, proxy, sender_name, signal_name, parameters):
        user_id, username = parameters.unpack()
        self.usernames[user_id] = username
        for task_list_id, dictionary in self.synced_lists.items():
            list_user_id = dictionary['user-id']
            task_list_name = dictionary['name']
            if user_id != list_user_id:
                continue
            if task_list_name in self.duplicated:
                if task_list_id in self.task_list_rows:
                    label = f"{task_list_name} ({self.usernames[list_user_id]})"
                    self.task_list_rows[task_list_id].label.set_label(label)

        self.set_reminder_task_list_dropdown()

        if self.app.preferences is not None:
            self.app.preferences.username_updated(user_id, username)
        if self.edit_lists_window is not None:
            self.edit_lists_window.username_updated(user_id, username)

    def list_updated(self, user_id, list_id, list_name):
        self.all_lists[list_id] = {
            'name': list_name,
            'user-id': user_id
        }
        self.synced_lists[list_id] = self.all_lists[list_id]
        self.update_task_list_row(user_id, list_id, list_name)

        self.set_reminder_task_list_dropdown()

    def remove_task_list_row(self, list_id):
        old_duplicated = self.duplicated.copy()
        self.duplicated = []
        values = {}
        for dictionary in self.synced_lists.values():
            if dictionary['name'] in values and values[dictionary['name']] != dictionary['user-id']:
                self.duplicated.append(dictionary['name'])
            else:
                values[dictionary['name']] = dictionary['user-id']

        row = self.task_list_rows[list_id]
        self.task_lists_list.remove(row)
        self.task_list_rows.pop(list_id)

        for name in old_duplicated:
            if name not in self.duplicated:
                for task_list_id, dictionary in self.synced_lists.items():
                    task_list_name = dictionary['name']
                    if task_list_name == name:
                        self.task_list_rows[task_list_id].label.set_label(name)

    def list_removed(self, list_id):
        for dictionary in self.all_lists, self.synced_lists:
            try:
                dictionary.pop(list_id)
            except:
                pass

        self.remove_task_list_row(list_id)

        self.set_reminder_task_list_dropdown()
        self.update_task_list()

    def set_task_lists(self):
        self.synced_lists = {}
        for list_id, value in self.all_lists.items():
            user_id = value['user-id']
            if user_id == 'local' or (user_id in self.synced_ids or list_id in self.synced_ids):
                self.synced_lists[list_id] = self.all_lists[list_id]

        self.duplicated = []
        values = {}
        for dictionary in self.synced_lists.values():
            if dictionary['name'] in values and values[dictionary['name']] != dictionary['user-id']:
                self.duplicated.append(dictionary['name'])
            else:
                values[dictionary['name']] = dictionary['user-id']

        self.task_list_rows = {}

        all_row = TaskListRow(_('All Lists'), None, 'all', icon='view-grid-symbolic')
        self.task_lists_list.append(all_row)
        self.task_list_rows['all'] = all_row

        for list_id, value in self.synced_lists.items():
            name = value['name']
            user_id = value['user-id']
            if name in self.duplicated:
                label = f"{name} ({self.usernames[user_id]})"
            else:
                label = name
            row = TaskListRow(label, user_id, list_id)
            self.task_lists_list.append(row)
            self.task_list_rows[list_id] = row

        self.set_reminder_task_list_dropdown()

        try:
            row = self.task_list_rows[self.selected_list_id]
            row.activate()
            self.page_sub_label.set_label(row.label.get_label())
        except:
            self.app.settings.connect('changed::selected-list', lambda *args: self.update_task_list())
            self.task_list_rows['all'].activate()
            return

        self.app.settings.connect('changed::selected-list', lambda *args: self.update_task_list())

    def set_reminder_task_list_dropdown(self):
        self.string_list = Gtk.StringList()
        self.task_list_ids = []

        for list_id, value in self.synced_lists.items():
            name = value['name']
            user_id = value['user-id']
            if name not in self.duplicated or user_id not in self.usernames.keys():
                self.string_list.append(f'{name}')
            else:
                self.string_list.append(f"{name} ({self.usernames[user_id]})")
            self.task_list_ids.append(list_id)

        if self.reminder_edit_win is not None:
            self.reminder_edit_win.set_task_list_dropdown()

        self.move_revealer.set_reveal_child(len(self.task_list_ids) > 1)
        self.move_revealer.set_hexpand(self.move_revealer.props.reveal_child)

    def unpack_reminders(self, reminders):
        for reminder in reminders:
            if 'error' in reminder:
                raise Exception

            self.display_reminder(**reminder)

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
        due_date = self.get_kwarg(kwargs, 'due-date')
        timestamp = self.get_kwarg(kwargs, 'timestamp')
        completed = self.get_kwarg(kwargs, 'completed', False)
        important = self.get_kwarg(kwargs, 'important', False)
        repeat_type = self.get_kwarg(kwargs, 'repeat-type', 0)
        repeat_frequency = self.get_kwarg(kwargs, 'repeat-frequency', 1)
        repeat_days = self.get_kwarg(kwargs, 'repeat-days', 0)
        repeat_times = self.get_kwarg(kwargs, 'repeat-times')
        repeat_until = self.get_kwarg(kwargs, 'repeat-until', 0)
        created_timestamp = self.get_kwarg(kwargs, 'created-timestamp', 0)
        updated_timestamp = self.get_kwarg(kwargs, 'updated-timestamp', 0)
        completed_timestamp = self.get_kwarg(kwargs, 'completed-date', 0)
        task_list = self.get_kwarg(kwargs, 'list-id', 'local')

        if reminder_id not in self.reminder_lookup_dict.keys():
            reminder = Reminder(
                self,
                {
                    'title': title,
                    'description': description,
                    'due-date': due_date,
                    'timestamp': timestamp,
                    'important': important,
                    'repeat-type': repeat_type,
                    'repeat-frequency': repeat_frequency,
                    'repeat-days': repeat_days,
                    'repeat-until': repeat_until,
                    'repeat-times': repeat_times,
                    'created-timestamp': created_timestamp,
                    'updated-timestamp': updated_timestamp,
                    'completed-date': completed_timestamp,
                    'list-id': task_list
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
                GLib.Variant(
                    '(sa{sv})', (
                        info.app_id,
                        {
                            'name': GLib.Variant('s', list_name),
                            'user-id': GLib.Variant('s', user_id)
                        }
                    )
                )
            ).unpack()[0]
        else:
            self.app.run_service_method(
                'UpdateList',
                GLib.Variant(
                    '(sa{sv})', (
                        info.app_id,
                        {
                            'id': GLib.Variant('s', list_id),
                            'name': GLib.Variant('s', list_name),
                            'user-id': GLib.Variant('s', user_id)
                        }
                    )
                )
            )
        return retval

    def delete_list(self, list_id):
        self.app.run_service_method(
            'RemoveList',
            GLib.Variant('(ss)', (info.app_id, list_id))
        )

    def sign_out(self, user_id):
        self.app.run_service_method('Logout', GLib.Variant('(s)', (user_id,)))

    def create_action(self, name, callback, variant = None, accels = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        if accels is not None:
            self.app.set_accels_for_action('win.' + name, accels)
        self.add_action(action)

    def settings_create_action(self, name):
        action = self.app.settings.create_action(name)
        self.add_action(action)

    def task_list_filter(self, reminder, list_id = None):
        task_list = reminder.options['list-id']
        selected_list_id = self.selected_list_id if list_id is None else list_id
        if selected_list_id == 'all':
            return True
        else:
            return task_list == selected_list_id

    def no_filter(self, reminder):
        #reminder.set_sensitive(True)
        reminder.set_no_strikethrough(True)
        return True

    def all_filter(self, reminder, list_id = None, just_filter = False):
        retval = self.task_list_filter(reminder, list_id)
        if not just_filter:
            reminder.set_no_strikethrough(False)
            #reminder.set_sensitive(retval)
            if not retval:
                self.reminders_list.unselect_row(reminder)
                reminder.set_selectable(False)
        return retval

    def upcoming_filter(self, reminder, list_id = None, just_filter = False):
        now = floor(time())
        if (reminder.options['timestamp'] == 0 or reminder.options['timestamp'] > now) and not reminder.completed:
            retval = self.task_list_filter(reminder, list_id)
        else:
            retval = False
        if not just_filter:
            #reminder.set_sensitive(retval)
            if not retval:
                self.reminders_list.unselect_row(reminder)
                reminder.set_selectable(False)
        return retval

    def past_filter(self, reminder, list_id = None, just_filter = False):
        now = ceil(time())
        if not reminder.completed and ((reminder.options['timestamp'] != 0 and reminder.options['timestamp'] < now) or \
        (reminder.options['due-date'] != 0 and datetime.datetime.fromtimestamp(reminder.options['due-date'], tz=datetime.timezone.utc).date() < datetime.date.today())):
            retval = self.task_list_filter(reminder, list_id)
        else:
            retval = False
        if not just_filter:
            #reminder.set_sensitive(retval)
            if not retval:
                self.reminders_list.unselect_row(reminder)
                reminder.set_selectable(False)
        return retval

    def completed_filter(self, reminder, list_id = None, just_filter = False):
        if reminder.completed:
            retval = self.task_list_filter(reminder, list_id)
            if not just_filter:
                reminder.set_no_strikethrough(True)
        else:
            retval = False
        if not just_filter:
            #reminder.set_sensitive(retval)
            if not retval:
                self.reminders_list.unselect_row(reminder)
                reminder.set_selectable(False)
        return retval

    def task_lists_sort_func(self, row1, row2):
        row1_ms = row1.user_id in self.usernames.keys()
        row2_ms = row2.user_id in self.usernames.keys()

        if not row1_ms and row2_ms:
            return -1

        if row1_ms and not row2_ms:
            return 1

        if row1_ms and row2_ms:
            if list(self.usernames.keys()).index(row1.user_id) < list(self.usernames.keys()).index(row2.user_id):
                return -1
            elif list(self.usernames.keys()).index(row1.user_id) > list(self.usernames.keys()).index(row2.user_id):
                return 1
        return 0

    def sort_func(self, row1, row2):
        # sort by timestamp from lowest to highest, showing completed reminders last
        # insensitive rows first as a part of fixing https://gitlab.gnome.org/GNOME/gtk/-/issues/5309
        try:
            if not row1.get_sensitive() and row2.get_sensitive():
                return -1
            if row1.get_sensitive() and not row2.get_sensitive():
                return 1

            if not row1.completed and row2.completed:
                return -1
            if row1.completed and not row2.completed:
                return 1

            if not row1.completed:
                if row1.options['important'] and not row2.options['important']:
                    return -1
                if not row1.options['important'] and row2.options['important']:
                    return 1

            if self.sort == 0: # time
                if row1.options['timestamp'] > row2.options['timestamp']:
                    return -1 if self.descending_sort else 1

                if row1.options['timestamp'] < row2.options['timestamp']:
                    return 1 if self.descending_sort else -1

                if row1.options['due-date'] > row2.options['due-date']:
                    return -1 if self.descending_sort else 1

                if row1.options['due-date'] < row2.options['due-date']:
                    return 1 if self.descending_sort else -1

            elif self.sort == 2: # created
                if row1.options['created-timestamp'] > row2.options['created-timestamp']:
                    return -1 if self.descending_sort else 1

                if row1.options['created-timestamp'] < row2.options['created-timestamp']:
                    return 1 if self.descending_sort else -1

            elif self.sort == 3: # updated
                if row1.options['updated-timestamp'] > row2.options['updated-timestamp']:
                    return -1 if self.descending_sort else 1

                if row1.options['updated-timestamp'] < row2.options['updated-timestamp']:
                    return 1 if self.descending_sort else -1

            # Alphabetical, also used as fallback
            name1 = (row1.options['title'] + row1.options['description']).lower()
            name2 = (row2.options['title'] + row2.options['description']).lower()
            if name1 == name2:
                return 0
            if name1 < name2:
                return 1 if self.descending_sort else -1
            # if name1 > name2
            return -1 if self.descending_sort else 1

        except Exception as error:
            return 0

    def all_reminders(self):
        if not self.all_row.is_selected():
            self.sidebar_list.select_row(self.all_row)
        self.reminders_list.set_filter_func(self.all_filter)
        self.page_label.set_label(_('All Reminders'))
        self.selected = self.all_row
        self.invalidate_filter()
        self.reminders_list.invalidate_sort()
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def upcoming_reminders(self):
        if not self.upcoming_row.is_selected():
            self.sidebar_list.select_row(self.upcoming_row)
        self.reminders_list.set_filter_func(self.upcoming_filter)
        self.page_label.set_label(_('Upcoming Reminders'))
        self.selected = self.upcoming_row
        self.invalidate_filter()
        self.reminders_list.invalidate_sort()
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def past_reminders(self):
        if not self.past_row.is_selected():
            self.sidebar_list.select_row(self.past_row)
        self.reminders_list.set_filter_func(self.past_filter)
        self.page_label.set_label(_('Past Reminders'))
        self.selected = self.past_row
        self.invalidate_filter()
        self.reminders_list.invalidate_sort()
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def completed_reminders(self):
        if not self.completed_row.is_selected():
            self.sidebar_list.select_row(self.completed_row)
        self.reminders_list.set_filter_func(self.completed_filter)
        self.page_label.set_label(_('Completed Reminders'))
        self.selected = self.completed_row
        self.invalidate_filter()
        self.reminders_list.invalidate_sort()
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def stop_search(self):
        self.search_entry.set_text('')
        self.flap.set_fold_policy(Adw.FlapFoldPolicy.AUTO)
        self.reminders_list.set_placeholder(self.placeholder)
        self.reminders_list.set_sort_func(self.sort_func)
        self.selected.emit('activate')
        self.label_revealer.set_reveal_child(True)

    def search_filter(self, reminder):
        retval = True
        text = self.search_entry.get_text().lower()
        words = text.split()
        reminder_text = reminder.options['title'].lower() + ' ' + reminder.options['description'].lower()

        for word in words:
            if word not in reminder_text:
                retval = False

        if retval:
            reminder.set_no_strikethrough(True)

        #reminder.set_sensitive(retval)
        if not retval:
            self.reminders_list.unselect_row(reminder)
            reminder.set_selectable(False)

        return retval

    def search_sort_func(self, row1, row2):
        if (not row1.get_sensitive() and row2.get_sensitive()):
            return -1
        if (row1.get_sensitive() and not row2.get_sensitive()):
            return 1
        text = self.search_entry.get_text().lower()
        row1_text = row1.options['title'].lower() + ' ' + row1.options['description'].lower()
        row2_text = row2.options['title'].lower() + ' ' + row2.options['description'].lower()

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

    def selected_remove_reminders(self):
        try:
            reminder_ids = []
            for reminder in self.reminders_list.get_selected_rows():
                if reminder.get_visible():
                    reminder_ids.append(reminder.id)

            results = self.app.run_service_method(
                'RemoveReminderv',
                GLib.Variant(
                    '(sas)', (info.app_id, reminder_ids)
                )
            )

            removed_reminder_ids = results.unpack()[0]
            for reminder_id in removed_reminder_ids:
                reminder = self.reminder_lookup_dict[reminder_id]
                self.reminder_lookup_dict.pop(reminder_id)
                self.reminders_list.remove(reminder)
        except Exception as error:
            logger.exception(error)

        self.set_selecting(False)
        self.invalidate_filter()

    def selected_change_important(self, important):
        try:
            variants = []
            for reminder in self.reminders_list.get_selected_rows():
                if reminder.get_visible() and reminder.options['important'] != important:
                    variants.append(
                        {
                            'id': GLib.Variant('s', reminder.id),
                            'important': GLib.Variant('b', important)
                        }
                    )

            results = self.app.run_service_method(
                'UpdateReminderv',
                GLib.Variant(
                    '(saa{sv})',
                    (
                        info.app_id,
                        variants
                    )
                )
            )

            updated_reminder_ids, timestamp = results.unpack()
            for reminder_id in updated_reminder_ids:
                reminder = self.reminder_lookup_dict[reminder_id]
                reminder.options['updated-timestamp'] = timestamp
                reminder.options['important'] = important
                reminder.set_important()
        except Exception as error:
            logger.exception(error)

        self.selected_changed()
        self.invalidate_filter()
        self.reminders_list.invalidate_sort()

    def selected_change_completed(self, completed):
        try:
            reminder_ids = []
            for reminder in self.reminders_list.get_selected_rows():
                if reminder.get_visible() and reminder.completed != completed:
                    reminder_ids.append(reminder.id)

            results = self.app.run_service_method(
                'UpdateCompletedv',
                GLib.Variant(
                    '(sasb)', (info.app_id, reminder_ids, completed)
                )
            )

            updated_reminder_ids, timestamp, completed_date = results.unpack()
            for reminder_id in updated_reminder_ids:
                reminder = self.reminder_lookup_dict[reminder_id]
                reminder.options['updated-timestamp'] = timestamp
                reminder.options['completed-date'] = completed_date
                reminder.set_completed(completed)
        except Exception as error:
            logger.exception(error)

        self.selected_changed()
        self.invalidate_filter()
        self.reminders_list.invalidate_sort()

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
            self.label_revealer.set_reveal_child(False)
        else:
            self.searching = False
            self.sort_button.set_sensitive(True)
            self.reminders_list.set_filter_func(self.no_filter)
            self.reminders_list.set_sort_func(self.sort_func)
            self.page_label.set_label(_('Start typing to search'))
            self.label_revealer.set_reveal_child(False)

    @Gtk.Template.Callback()
    def new_reminder(self, button = None):
        self.search_revealer.set_reveal_child(False)
        self.selected = self.all_row
        self.selected.emit('activate')
        self.new_edit_win()

    @Gtk.Template.Callback()
    def on_cancel(self, btn):
        self.set_selecting(False)

    @Gtk.Template.Callback()
    def selected_complete(self, btn):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Mark reminders as complete?'),
            body=_('Are you sure you want to mark the currently selected reminder(s) as complete?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.selected_change_completed(True))
        confirm_dialog.present()

    @Gtk.Template.Callback()
    def selected_incomplete(self, btn):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Mark reminders as incomplete?'),
            body=_('Are you sure you want to mark the currently selected reminder(s) as incomplete?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.selected_change_completed(False))
        confirm_dialog.present()

    @Gtk.Template.Callback()
    def move_selected(self, btn):
        MoveRemindersWindow(self, self.reminders_list.get_selected_rows())

    @Gtk.Template.Callback()
    def selected_important(self, btn):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Mark reminders as important?'),
            body=_('Are you sure you want to mark the currently selected reminder(s) as important?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.selected_change_important(True))
        confirm_dialog.present()

    @Gtk.Template.Callback()
    def selected_unimportant(self, btn):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Mark reminders as unimportant?'),
            body=_('Are you sure you want to mark the currently selected reminder(s) as unimportant?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.selected_change_important(False))
        confirm_dialog.present()

    @Gtk.Template.Callback()
    def selected_remove(self, btn = None):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Remove reminders?'),
            body=_('Are you sure you want to remove the currently selected reminder(s)? This cannot be undone.')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.selected_remove_reminders())
        confirm_dialog.present()
