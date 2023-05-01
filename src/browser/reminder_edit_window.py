# reminder_edit_window.py
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

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _

from remembrance import info
from remembrance.browser.reminder import Reminder
from ctypes import c_double
from logging import getLogger

logger = getLogger(info.app_executable)

DEFAULT_OPTIONS = info.reminder_defaults.copy()
DEFAULT_OPTIONS.pop('uid')
DEFAULT_OPTIONS.pop('updated-timestamp')
DEFAULT_OPTIONS.pop('created-timestamp')
DEFAULT_OPTIONS.pop('completed-timestamp')
DEFAULT_OPTIONS.pop('completed-date')

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/reminder_edit_window.ui')
class ReminderEditWindow(Adw.Window):
    __gtype_name__ = 'ReminderEditWindow'

    title_entry = Gtk.Template.Child()
    description_entry = Gtk.Template.Child()
    task_list_row = Gtk.Template.Child()
    time_row = Gtk.Template.Child()
    date_label = Gtk.Template.Child()
    calendar = Gtk.Template.Child()
    notif_btn = Gtk.Template.Child()
    hour_button = Gtk.Template.Child()
    hour_adjustment = Gtk.Template.Child()
    minute_adjustment = Gtk.Template.Child()
    am_pm_button = Gtk.Template.Child()
    repeat_type_button = Gtk.Template.Child()
    ms_repeat_type_button = Gtk.Template.Child()
    repeat_row = Gtk.Template.Child()
    week_repeat_row = Gtk.Template.Child()
    frequency_btn = Gtk.Template.Child()
    mon_btn = Gtk.Template.Child()
    tue_btn = Gtk.Template.Child()
    wed_btn = Gtk.Template.Child()
    thu_btn = Gtk.Template.Child()
    fri_btn = Gtk.Template.Child()
    sat_btn = Gtk.Template.Child()
    sun_btn = Gtk.Template.Child()
    repeat_times_btn = Gtk.Template.Child()
    repeat_until_btn = Gtk.Template.Child()
    repeat_until_label = Gtk.Template.Child()
    repeat_times_box = Gtk.Template.Child()
    repeat_until_calendar = Gtk.Template.Child()
    repeat_duration_button = Gtk.Template.Child()
    importance_switch = Gtk.Template.Child()
    repeat_times_row = Gtk.Template.Child()
    days_box = Gtk.Template.Child()

    def __init__(self, win, app, reminder = None, **kwargs):
        super().__init__(**kwargs)
        self.task_list_row_connection = None
        self.win = win
        self.app = app
        self.calendar_connections = []
        self.set_transient_for(win)
        self.setup(reminder)
        self.win.connect('notify::time-format', lambda *args: self.time_format_updated())
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>s'), Gtk.CallbackAction.new(lambda *args: self.on_save())))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))
        self.app.settings.connect('changed::week-starts-sunday', lambda *args: self.week_start_changed())
        self.week_start_changed()

    def week_start_changed(self):
        starts_sunday = self.app.settings.get_boolean('week-starts-sunday')
        if starts_sunday:
            self.days_box.remove(self.sun_btn)
            self.days_box.prepend(self.sun_btn)
        else:
            self.days_box.remove(self.sun_btn)
            self.days_box.append(self.sun_btn)

    def setup(self, reminder):
        self.reminder = reminder

        if reminder is not None:
            self.options = reminder.options.copy()
            self.id = reminder.id
            self.task_list = self.options['list-id']
        else:
            self.options = DEFAULT_OPTIONS.copy()
            self.id = None
            self.task_list = self.options['list-id'] = self.win.selected_list_id if self.win.selected_list_id != 'all' else 'local'

        self.set_time(self.options['timestamp'], self.options['due-date'])
        self.set_important(self.options['important'])

        self.set_task_list_dropdown()
        self.task_list_visibility_changed()

        self.set_repeat_days(self.options['repeat-days'])
        self.set_repeat_type(self.options['repeat-type'])
        self.set_repeat_frequency(self.options['repeat-frequency'])
        self.set_repeat_duration(self.options['repeat-until'], self.options['repeat-times'])
        self.repeat_day_changed()

        self.title_entry.set_text(self.options['title'])
        self.description_entry.set_text(self.options['description'])

        if reminder is not None:
            self.set_title(_('Edit Reminder'))
        else:
            self.set_title(_('New Reminder'))

        self.repeat_duration_selected_changed()

        if self.options['repeat-type'] == info.RepeatType.WEEK:
            self.week_repeat_row.set_visible(True)
        else:
            self.week_repeat_row.set_visible(False)

    def create_action(self, name, callback, variant = None, accels = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        if accels is not None:
            self.app.set_accels_for_action('win.' + name, accels)
        self.add_action(action)

    def set_important(self, importance):
        self.importance_switch.set_active(importance)

    def get_options(self):
        options = self.options.copy()
        options['title'] = self.title_entry.get_text()
        options['description'] = self.description_entry.get_text()

        if self.time_row.get_enable_expansion():
            options['due-date'] = int(datetime.datetime(self.calendar.props.year, self.calendar.props.month + 1, self.calendar.props.day, tzinfo=datetime.timezone.utc).timestamp())
            options['timestamp'] = self.get_timestamp() if self.notif_btn.get_active() else 0
        else:
            options['due-date'] = 0
            options['timestamp'] = 0

        options['list-id'] = self.task_list

        if not self.repeat_row.get_enable_expansion() or not self.repeat_row.get_sensitive():
            options['repeat-type'] = 0
        elif self.repeat_type_button.get_visible():
            options['repeat-type'] = self.repeat_type_button.get_selected() + 1
        elif self.ms_repeat_type_button.get_visible():
            options['repeat-type'] = self.ms_repeat_type_button.get_selected() + 3

        options['important'] = self.importance_switch.get_active()

        if options['repeat-type'] != 0:
            self.frequency_btn.update()
            options['repeat-frequency'] = int(self.frequency_btn.get_value())
            if self.repeat_times_row.get_sensitive:
                self.repeat_times_btn.update()
                if self.repeat_duration_button.get_selected() == 0:
                    options['repeat-times'] = -1
                    options['repeat-until'] = 0
                elif self.repeat_duration_button.get_selected() == 1:
                    options['repeat-times'] = int(self.repeat_times_btn.get_value())
                    options['repeat-until'] = 0
                elif self.repeat_duration_button.get_selected() == 2:
                    options['repeat-times'] = -1
                    options['repeat-until'] = int(datetime.datetime(self.repeat_until_calendar.props.year, self.repeat_until_calendar.props.month + 1, self.repeat_until_calendar.props.day, tzinfo=datetime.timezone.utc).timestamp())
            else:
                options['repeat-times'] = -1
                options['repeat-until'] = 0

            if options['repeat-type'] == info.RepeatType.WEEK:
                self.week_repeat_row.set_visible(True)
                repeat_days = self.get_repeat_days()
                if repeat_days == 0:
                    repeat_days = 2**(self.time.get_day_of_week() - 1)
                    self.set_repeat_days(repeat_days)
                options['repeat-days'] = repeat_days
            else:
                options['repeat-days'] = 0
        else:
            options['repeat-frequency'] = 1
            options['repeat-days'] = 0
            options['repeat-until'] = 0
            options['repeat-times'] = -1

        return options

    def get_repeat_days(self):
        repeat_days = 0
        for btn, flag in (
            (self.mon_btn, info.RepeatDays.MON),
            (self.tue_btn, info.RepeatDays.TUE),
            (self.wed_btn, info.RepeatDays.WED),
            (self.thu_btn, info.RepeatDays.THU),
            (self.fri_btn, info.RepeatDays.FRI),
            (self.sat_btn, info.RepeatDays.SAT),
            (self.sun_btn, info.RepeatDays.SUN)
        ):
            if btn.get_active():
                repeat_days += int(flag)

        return repeat_days

    def check_changed(self, options):
        return options != self.options

    def task_list_changed(self, row = None, param = None):
        self.task_list = self.win.task_list_ids[self.task_list_row.get_selected()]
        self.task_list_visibility_changed()

    def update_repeat_day(self):
        if self.repeat_type_button.get_visible():
            repeat_type = self.repeat_type_button.get_selected() + 1
        elif self.ms_repeat_type_button.get_visible():
            repeat_type = self.ms_repeat_type_button.get_selected() + 3
        repeat_days = self.get_repeat_days()
        if self.repeat_row.get_enable_expansion() and repeat_type == info.RepeatType.WEEK:
            if repeat_days == 0 or repeat_days in info.RepeatDays.__members__.values():
                new_repeat_days = 2**(self.time.get_day_of_week() - 1)
                if new_repeat_days != repeat_days:
                    self.set_repeat_days(new_repeat_days)

    def set_time(self, timestamp, due_date):
        for i in self.calendar_connections:
            self.calendar.disconnect(i)
        self.calendar_connections = []

        self.time_row.set_enable_expansion(timestamp != 0 or due_date != 0)
        self.notif_btn.set_active(timestamp != 0 or due_date == 0)
        if due_date == 0 and timestamp == 0:
            self.time = GLib.DateTime.new_now_local()
        elif timestamp == 0:
            now = GLib.DateTime.new_now_utc()
            self.time = GLib.DateTime.new_from_unix_utc(due_date)
            self.time = self.time.add_hours(now.get_hour() - self.time.get_hour())
            self.time = self.time.add_minutes(now.get_minute() - self.time.get_minute())
        else:
            self.time = GLib.DateTime.new_from_unix_local(timestamp)

        # Remove seconds from the time because it isn't important
        seconds = self.time.get_seconds()
        self.time = self.time.add_seconds(-(seconds))

        self.calendar.select_day(self.time)
        self.time_format_updated()
        self.minute_adjustment.set_value(self.time.get_minute())
        self.date_label.set_label(self.win.get_date_label(self.time, True))

        for i in ('day-selected', 'notify::year', 'notify::month'):
            self.calendar_connections.append(self.calendar.connect(i, self.day_changed))

    def update_date_button_label(self):
        self.date_label.set_label(self.win.get_date_label(self.time, True))
        self.repeat_until_label.set_label(self.win.get_date_label(self.repeat_until_calendar.get_date(), True))

    def get_timestamp(self):
        return self.time.to_unix()

    def update_calendar(self):
        self.calendar.select_day(self.time)
        self.date_label.set_label(self.win.get_date_label(self.time, True))

    def set_pm(self):
        self.am_pm_button.set_label(_('PM'))
        self.pm = True

    def set_am(self):
        self.am_pm_button.set_label(_('AM'))
        self.pm = False

    def toggle_am_pm(self):
        if self.pm:
            self.set_am()
        else:
            self.set_pm()
        self.hour_changed()

    def time_format_updated(self):
        hour = self.time.get_hour()
        if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR:
            self.am_pm_button.set_visible(True)
            self.hour_adjustment.set_upper(11)
            if hour >= 12:
                self.am_pm_button.set_label(_('PM'))
                self.pm = True
                self.hour_adjustment.set_value(hour - 12)
            else:
                self.am_pm_button.set_label(_('AM'))
                self.pm = False
                self.hour_adjustment.set_value(hour)
        elif self.win.props.time_format == info.TimeFormat.TWENTYFOUR_HOUR:
            self.hour_adjustment.set_upper(23)
            self.am_pm_button.set_visible(False)
            self.pm = False
            self.hour_adjustment.set_value(hour)

    def set_task_list_dropdown(self):
        visible = len(self.win.task_list_ids) > 1
        self.task_list_row.set_visible(visible)

        if not visible:
            return

        if self.task_list_row_connection is not None:
            self.task_list_row.disconnect(self.task_list_row_connection)
            self.task_list_row_connection = None

        self.task_list_row.set_model(self.win.string_list)

        self.set_task_list_dropdown_selected()

    def set_task_list_dropdown_selected(self):
        if self.task_list_row_connection is not None:
            self.task_list_row.disconnect(self.task_list_row_connection)
            self.task_list_row_connection = None

        try:
            index = self.win.task_list_ids.index(self.task_list)
            self.task_list_row.set_selected(index)
        except:
            self.task_list_row.set_selected(0)

        self.task_list_row_connection = self.task_list_row.connect('notify::selected', self.task_list_changed)

    def entry_check_empty(self):
        if len(self.title_entry.get_text()) == 0:
            if not self.title_entry.has_css_class('error'):
                self.title_entry.add_css_class('error')
            return True
        elif self.title_entry.has_css_class('error'):
            self.title_entry.remove_css_class('error')
        return False

    def set_repeat_type(self, repeat_type):
        if repeat_type != 0 and self.repeat_row.get_sensitive():
            self.repeat_type_button.set_selected(repeat_type - 1)
            ms_selected = repeat_type - 3
            if ms_selected > 0:
                self.ms_repeat_type_button.set_selected(ms_selected)

            self.repeat_row.set_enable_expansion(True)
        else:
            self.repeat_row.set_enable_expansion(False)
            self.repeat_type_button.set_selected(0)
            self.ms_repeat_type_button.set_selected(0)
            self.repeat_duration_button.set_selected(0)
            self.repeat_times_btn.set_value(5)

    def set_repeat_frequency(self, repeat_frequency):
        self.frequency_btn.set_value(repeat_frequency)

    def set_repeat_times(self, repeat_times):
        if self.repeat_row.get_enable_expansion() and self.repeat_duration_button.get_selected() == 1:
            self.repeat_times_btn.set_value(repeat_times)

    def set_repeat_duration(self, repeat_until, repeat_times):
        if self.repeat_row.get_enable_expansion():
            if repeat_times != -1:
                self.repeat_times_btn.set_value(repeat_times)
                self.repeat_duration_button.set_selected(1)
            elif repeat_until > 0:
                self.repeat_duration_button.set_selected(2)
                self.repeat_until_calendar.select_day(GLib.DateTime.new_from_unix_local(repeat_until))
                self.repeat_times_btn.set_value(5)

        if repeat_until == 0:
            self.repeat_until_calendar.select_day(GLib.DateTime.new_now_local().add_days(5))

    def set_repeat_days(self, repeat_days):
        repeat_days_flag = info.RepeatDays(repeat_days)
        for btn, flag in (
            (self.mon_btn, info.RepeatDays.MON),
            (self.tue_btn, info.RepeatDays.TUE),
            (self.wed_btn, info.RepeatDays.WED),
            (self.thu_btn, info.RepeatDays.THU),
            (self.fri_btn, info.RepeatDays.FRI),
            (self.sat_btn, info.RepeatDays.SAT),
            (self.sun_btn, info.RepeatDays.SUN)
        ):
            btn.set_active(flag in repeat_days_flag)

    def day_changed(self, calendar = None, day = None):
        date = self.calendar.get_date()
        new_day = date.get_day_of_year()
        new_year = date.get_year()
        old_day = self.time.get_day_of_year()
        old_year = self.time.get_year()
        days = new_day - old_day
        years = new_year - old_year
        self.time = self.time.add_days(days)
        self.time = self.time.add_years(years)
        self.hour_changed()
        self.update_repeat_day()
        self.date_label.set_label(self.win.get_date_label(self.time, True))

    def do_save(self, data = None):
        try:
            options = self.get_options()

            if self.id is None:
                results = self.app.run_service_method(
                    'CreateReminder',
                    GLib.Variant(
                        '(sa{sv})',
                        (
                            info.app_id,
                            {
                                'title': GLib.Variant('s', options['title']),
                                'description': GLib.Variant('s', options['description']),
                                'due-date': GLib.Variant('u', options['due-date']),
                                'timestamp': GLib.Variant('u', options['timestamp']),
                                'important': GLib.Variant('u', options['important']),
                                'repeat-type': GLib.Variant('q', options['repeat-type']),
                                'repeat-frequency': GLib.Variant('q', options['repeat-frequency']),
                                'repeat-days': GLib.Variant('q', options['repeat-days']),
                                'repeat-times': GLib.Variant('n', options['repeat-times']),
                                'repeat-until': GLib.Variant('u', options['repeat-until']),
                                'list-id': GLib.Variant('s', options['list-id'])
                            }
                        )
                    )
                )
                self.id, options['created-timestamp'] = results.unpack()
            else:
                results = self.app.run_service_method(
                    'UpdateReminder',
                    GLib.Variant(
                        '(sa{sv})',
                        (
                            info.app_id,
                            {
                                'id': GLib.Variant('s', self.id),
                                'title': GLib.Variant('s', options['title']),
                                'description': GLib.Variant('s', options['description']),
                                'due-date': GLib.Variant('u', options['due-date']),
                                'timestamp': GLib.Variant('u', options['timestamp']),
                                'important': GLib.Variant('u', options['important']),
                                'repeat-type': GLib.Variant('q', options['repeat-type']),
                                'repeat-frequency': GLib.Variant('q', options['repeat-frequency']),
                                'repeat-days': GLib.Variant('q', options['repeat-days']),
                                'repeat-times': GLib.Variant('n', options['repeat-times']),
                                'repeat-until': GLib.Variant('u', options['repeat-until']),
                                'list-id': GLib.Variant('s', options['list-id'])
                            }
                        )
                    )
                )
                options['updated-timestamp'] = results.unpack()[0]

            self.options = options

            if self.reminder is not None:
                self.reminder.set_options(self.options)
            else:
                self.reminder = Reminder(self.win, self.options, self.id)
                self.win.reminders_list.append(self.reminder)
                self.win.reminder_lookup_dict[self.id] = self.reminder

            self.win.invalidate_filter()
            self.win.reminders_list.invalidate_sort()

            self.set_visible(False)
        except Exception as error:
            logger.exception(error)

    def set_ms(self):
        self.repeat_times_row.set_sensitive(False)
        self.repeat_row.set_sensitive(True)

        if self.repeat_type_button.get_visible():
            repeat_type = self.repeat_type_button.get_selected() + 1
            repeat_type -= 3
            if repeat_type > 0:
                self.ms_repeat_type_button.set_selected(repeat_type)

            self.repeat_type_button.set_visible(False)
            self.ms_repeat_type_button.set_visible(True)

    def set_notify(self, notify):
        self.repeat_times_row.set_sensitive(True)
        self.repeat_row.set_sensitive(True)

        if not notify and self.repeat_type_button.get_visible():
            repeat_type = self.repeat_type_button.get_selected() + 1
            repeat_type -= 3
            if repeat_type > 0:
                self.ms_repeat_type_button.set_selected(repeat_type)

            self.repeat_type_button.set_visible(False)
            self.ms_repeat_type_button.set_visible(True)
        elif not self.repeat_type_button.get_visible():
            repeat_type = self.ms_repeat_type_button.get_selected() + 3
            self.repeat_type_button.set_selected(repeat_type - 1)

            self.ms_repeat_type_button.set_visible(False)
            self.repeat_type_button.set_visible(True)

    @Gtk.Template.Callback()
    def repeat_day_changed(self, calendar = None, data = None):
        self.repeat_until_label.set_label(self.win.get_date_label(self.repeat_until_calendar.get_date(), True))

    @Gtk.Template.Callback()
    def repeat_duration_selected_changed(self, button = None, data = None):
        if self.repeat_duration_button.get_selected() == 0:
            self.repeat_times_box.set_visible(False)
            self.repeat_until_btn.set_visible(False)
        elif self.repeat_duration_button.get_selected() == 1:
            self.repeat_times_box.set_visible(True)
            self.repeat_until_btn.set_visible(False)
        elif self.repeat_duration_button.get_selected() == 2:
            self.repeat_times_box.set_visible(False)
            self.repeat_until_btn.set_visible(True)

    @Gtk.Template.Callback()
    def repeat_type_selected_changed(self, button, data = None):
        if button == self.repeat_type_button:
            repeat_type = self.repeat_type_button.get_selected() + 1
        elif button == self.ms_repeat_type_button:
            repeat_type = self.ms_repeat_type_button.get_selected() + 3

        if repeat_type == info.RepeatType.WEEK:
            self.week_repeat_row.set_visible(True)
            if self.get_repeat_days() == 0:
                repeat_days = 2**(self.time.get_day_of_week() - 1)
                self.set_repeat_days(repeat_days)
        else:
            self.week_repeat_row.set_visible(False)

    @Gtk.Template.Callback()
    def title_entry_changed(self, object = None):
        if self.title_entry.has_css_class('error'):
            self.title_entry.remove_css_class('error')

    @Gtk.Template.Callback()
    def task_list_visibility_changed(self, row = None, param = None):
        if not self.task_list_row.get_visible():
            self.task_list = 'local'
        if self.time_row.get_enable_expansion():
            if self.win.synced_lists[self.task_list]['user-id'] in self.win.ms_users.keys():
                self.set_ms()
            else:
                self.set_notify(self.notif_btn.get_active())
        else:
            self.repeat_row.set_sensitive(False)
            self.repeat_row.set_expanded(False)

    @Gtk.Template.Callback()
    def time_switched(self, switch, data = None):
        if self.time_row.get_enable_expansion():
            if self.win.synced_lists[self.task_list]['user-id'] in self.win.ms_users.keys():
                self.set_ms()
            else:
                self.set_notify(self.notif_btn.get_active())
        else:
            self.repeat_row.set_sensitive(False)
            self.repeat_row.set_expanded(False)

    @Gtk.Template.Callback()
    def show_leading_zeros(self, spin_button):
        spin_button.set_text(f'{spin_button.get_value_as_int():02d}')
        return True

    @Gtk.Template.Callback()
    def hour_output(self, spin_button):
        value = spin_button.get_value_as_int()
        if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR and value == 0:
            value = 12
        spin_button.set_text(f'{value:02d}')
        return True

    @Gtk.Template.Callback()
    def hour_input(self, spin_button, gpointer):
        new_value = int(spin_button.get_text())
        if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR and new_value == 12:
            new_value = 0
        double = c_double.from_address(hash(gpointer))
        double.value = float(new_value)
        return True

    @Gtk.Template.Callback()
    def on_am_pm_button_pressed(self, button = None):
        self.toggle_am_pm()

    @Gtk.Template.Callback()
    def minute_changed(self, adjustment = None):
        minutes = self.minute_adjustment.get_value() - self.time.get_minute()
        self.time = self.time.add_minutes(minutes)

    @Gtk.Template.Callback()
    def hour_changed(self, adjustment = None):
        value = self.hour_adjustment.get_value()
        old_value = self.time.get_hour()
        if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR:
            if self.pm:
                value += 12
            if value >= 12 and not self.pm:
                self.set_pm()
            elif value < 12 and self.pm:
                self.set_am()

        hours = value - old_value

        self.time = self.time.add_hours(hours)
        if value != self.time.get_hour():
            self.hour_adjustment.set_value(self.time.get_hour())
            if self.minute_adjustment.get_value() != self.time.get_minute():
                self.minute_adjustment.set_value(self.time.get_minute())

    @Gtk.Template.Callback()
    def wrap_minute(self, button):
        if button.get_value() == 0:
            new_value = self.hour_button.get_value() + 1
        else:
            new_value = self.hour_button.get_value() - 1

        lower, upper = self.hour_button.get_range()
        if new_value > upper:
            self.hour_button.set_value(lower)
            self.wrap_hour()
        elif new_value < lower:
            self.hour_button.set_value(upper)
            self.wrap_hour()
        self.hour_button.set_value(new_value)

    @Gtk.Template.Callback()
    def wrap_hour(self, button = None):
        if self.hour_button.get_adjustment().get_value() == 0:
            if not self.win.props.time_format == info.TimeFormat.TWELVE_HOUR or self.pm:
                self.time = self.time.add_days(1)
                self.update_calendar()
            if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR:
                self.toggle_am_pm()
        else:
            if not self.win.props.time_format == info.TimeFormat.TWELVE_HOUR or not self.pm:
                self.time = self.time.add_days(-1)
                self.update_calendar()
            if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR:
                self.toggle_am_pm()

    @Gtk.Template.Callback()
    def on_cancel(self, button = None):
        self.win.close_edit_win()

    @Gtk.Template.Callback()
    def on_save(self, button = None):
        if self.get_visible():
            if self.entry_check_empty():
                return

            self.do_save()
