# reminder.py - UI For each reminder
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
import ctypes
import datetime

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
from gettext import gettext as _
from math import floor

from remembrance import info

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/reminder_edit_window.ui')
class ReminderEditWindow(Adw.Window):
    __gtype_name__ = 'reminder_edit_window'

    title_entry = Gtk.Template.Child()
    description_entry = Gtk.Template.Child()
    task_list_row = Gtk.Template.Child()
    time_row = Gtk.Template.Child()
    date_button = Gtk.Template.Child()
    calendar = Gtk.Template.Child()
    hour_button = Gtk.Template.Child()
    hour_adjustment = Gtk.Template.Child()
    minute_adjustment = Gtk.Template.Child()
    am_pm_button = Gtk.Template.Child()
    repeat_type_button = Gtk.Template.Child()
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
    repeat_times_box = Gtk.Template.Child()
    repeat_until_calendar = Gtk.Template.Child()
    repeat_duration_button = Gtk.Template.Child()

    def __init__(self, reminder, **kwargs):
        super().__init__(**kwargs)
        self.task_list_row_connection = None
        self.win = reminder.win
        self.app = reminder.app
        self.set_transient_for(self.win)
        self.setup(reminder)
        self.win.connect('notify::time-format', lambda *args: self.time_format_updated())

    def setup(self, reminder):
        self.id = reminder.id
        self.reminder = reminder

        self.task_list = reminder.options['list']
        self.user_id = reminder.options['user-id']

        self.time_set = False
        self.repeat_days = reminder.options['repeat-days']
        self.set_time(reminder.options['timestamp'])
        self.time_format_updated()
        self.time_set = True

        self.set_task_list_dropdown()
        self.task_list_visibility_changed()

        self.set_repeat_type(reminder.options['repeat-type'])
        self.set_repeat_frequency(reminder.options['repeat-frequency'])
        self.repeat_days = 0 # this will get set again
        self.set_repeat_days(reminder.options['repeat-days'])
        self.set_repeat_duration(reminder.options['repeat-until'], reminder.options['repeat-times'])
        self.repeat_day_changed()

        if self.id is not None:
            self.title_entry.set_text(reminder.options['title'])
            self.description_entry.set_text(reminder.options['description'])
            self.set_title(_('Edit Reminder'))
        else:
            self.title_entry.set_text('')
            self.description_entry.set_text('')
            self.set_title(_('New Reminder'))

        self.repeat_duration_selected_changed()
        self.repeat_type_selected_changed()

    def get_options(self):
        options = self.reminder.options.copy()
        options['title'] = self.title_entry.get_text()
        options['description'] = self.description_entry.get_text()
        options['timestamp'] = self.get_timestamp() if self.time_row.get_enable_expansion() else 0

        options['list'] = self.task_list
        options['user-id'] = self.user_id

        options['repeat-type'] = 0 if not self.repeat_row.get_enable_expansion() or not self.repeat_row.get_sensitive() else self.repeat_type_button.get_selected() + 1

        if options['repeat-type'] != 0:
            self.frequency_btn.update()
            options['repeat-frequency'] = int(self.frequency_btn.get_value())
            self.repeat_times_btn.update()
            if self.repeat_duration_button.get_selected() == 0:
                options['repeat-times'] = -1
                options['repeat-until'] = 0
            elif self.repeat_duration_button.get_selected() == 1:
                options['repeat-times'] = int(self.repeat_times_btn.get_value())
                options['repeat-until'] = 0
            elif self.repeat_duration_button.get_selected() == 2:
                options['repeat-times'] = -1
                options['repeat-until'] = datetime.datetime(self.calendar.props.year, self.calendar.props.month + 1, self.calendar.props.day).timestamp()

            options['repeat-days'] = self.repeat_days
        else:
            now = floor(time.time())
            options['repeat-frequency'] = 1
            options['repeat-days'] = 0
            options['repeat-until'] = 0
            if options['timestamp'] > floor(time.time()):
                options['repeat-times'] = 1
            elif self.reminder.options['repeat-type'] != 0:
                options['repeat-times'] = 0

        return options

    def check_changed(self, options):
        return options != self.reminder.options

    def task_list_changed(self, row = None, param = None):
        self.task_list, self.user_id = self.win.task_list_ids[self.task_list_row.get_selected()]
        self.task_list_visibility_changed()

    def update_repeat_day(self):
        if self.repeat_row.get_enable_expansion():
            if self.repeat_days == 0 or self.repeat_days in info.RepeatDays.__members__.values():
                repeat_days = 2**(self.time.get_day_of_week() - 1)
                if self.repeat_days != repeat_days:
                    self.repeat_days = 0
                    self.set_repeat_days(repeat_days)

    def set_time(self, timestamp):
        self.time_row.set_enable_expansion(timestamp != 0)
        self.time = GLib.DateTime.new_now_local() if timestamp == 0 else GLib.DateTime.new_from_unix_local(timestamp)
        # Remove seconds from the time because it isn't important
        seconds = self.time.get_seconds()
        self.time = self.time.add_seconds(-(seconds))

        self.calendar.select_day(self.time)
        self.date_button.set_label(self.win.get_date_label(self.time))
        self.minute_adjustment.set_value(self.time.get_minute())

    def update_date_button_label(self):
        self.date_button.set_label(self.win.get_date_label(self.time))
        self.repeat_until_btn.set_label(self.win.get_date_label(self.time))

    def get_timestamp(self):
        return self.time.to_unix()

    def update_calendar(self):
        self.calendar.select_day(self.time)
        self.date_button.set_label(self.win.get_date_label(self.time))

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
        if self.win.props.time_format == info.TimeFormat.TWELVE_HOUR:
            self.am_pm_button.set_visible(True)
            self.hour_adjustment.set_upper(11)
            if self.time.get_hour() >= 12:
                self.am_pm_button.set_label(_('PM'))
                self.pm = True
                self.hour_adjustment.set_value(self.time.get_hour() - 12)
            else:
                self.am_pm_button.set_label(_('AM'))
                self.pm = False
                self.hour_adjustment.set_value(self.time.get_hour())
        elif self.win.props.time_format == info.TimeFormat.TWENTYFOUR_HOUR:
            self.am_pm_button.set_visible(False)
            self.hour_adjustment.set_upper(23)
            self.hour_adjustment.set_value(self.time.get_hour())

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
            index = self.win.task_list_ids.index((self.task_list, self.user_id))
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
            self.repeat_row.set_enable_expansion(True)
        else:
            self.repeat_row.set_enable_expansion(False)
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
                self.calendar.select_day(GLib.DateTime.new_from_unix_local(repeat_until))
                self.repeat_times_btn.set_value(5)

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

        self.day_changed()

    @Gtk.Template.Callback()
    def repeat_days_changed(self, button):
        for btn, flag in (
            (self.mon_btn, info.RepeatDays.MON),
            (self.tue_btn, info.RepeatDays.TUE),
            (self.wed_btn, info.RepeatDays.WED),
            (self.thu_btn, info.RepeatDays.THU),
            (self.fri_btn, info.RepeatDays.FRI),
            (self.sat_btn, info.RepeatDays.SAT),
            (self.sun_btn, info.RepeatDays.SUN)
        ):
            if button == btn:
                if button.get_active():
                    self.repeat_days += flag
                else:
                    self.repeat_days -= flag

    @Gtk.Template.Callback()
    def repeat_day_changed(self, calendar = None, data = None):
        self.repeat_until_btn.set_label(self.win.get_date_label(self.repeat_until_calendar.get_date()))

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
    def repeat_type_selected_changed(self, button = None, data = None):
        repeat_type = self.repeat_type_button.get_selected() + 1
        if repeat_type == info.RepeatType.WEEK:
            self.week_repeat_row.set_visible(True)
            self.update_repeat_day()
        else:
            self.week_repeat_row.set_visible(False)

    @Gtk.Template.Callback()
    def title_entry_changed(self, object = None):
        if self.title_entry.has_css_class('error'):
            self.title_entry.remove_css_class('error')

    @Gtk.Template.Callback()
    def task_list_visibility_changed(self, row = None, param = None):
        if not self.task_list_row.get_visible():
            self.task_list = self.user_id = 'local'
        if self.task_list_row.get_visible() and self.user_id != 'local':
            self.repeat_row.set_enable_expansion(False)
            self.repeat_row.set_sensitive(False)
            self.repeat_row.set_tooltip_text(_("Microsoft reminders currently don't support recurrence"))
        else:
            if self.time_row.get_enable_expansion():
                self.repeat_row.set_sensitive(True)
            else:
                self.repeat_row.set_sensitive(False)
                self.repeat_row.set_expanded(False)
            self.repeat_row.set_tooltip_text(None)

    @Gtk.Template.Callback()
    def time_switched(self, switch, data = None):
        if self.task_list_row.get_visible() and self.user_id != 'local':
            return
        if self.time_row.get_enable_expansion():
            self.repeat_row.set_sensitive(True)
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
        double = ctypes.c_double.from_address(hash(gpointer))
        double.value = float(new_value)
        return True

    @Gtk.Template.Callback()
    def on_am_pm_button_pressed(self, button = None):
        self.toggle_am_pm()

    @Gtk.Template.Callback()
    def minute_changed(self, adjustment = None):
        minutes = self.minute_adjustment.get_value() - self.time.get_minute()
        self.time = self.time.add_minutes(minutes)
        self.update_repeat_day()

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

            self.update_calendar()

        hours = value - old_value

        old_time = self.time
        self.time = self.time.add_hours(hours)
        if value != self.time.get_hour():
            self.hour_adjustment.set_value(self.time.get_hour())
            if self.minute_adjustment.get_value() != self.time.get_minute():
                self.minute_adjustment.set_value(self.time.get_minute())
        self.update_repeat_day()

    @Gtk.Template.Callback()
    def day_changed(self, calendar = None, day = None):
        date = self.calendar.get_date()
        new_day = date.get_day_of_year()
        old_day = self.time.get_day_of_year()
        days = new_day - old_day
        self.time = self.time.add_days(days)
        if self.time_set:
            self.hour_changed()
        self.date_button.set_label(self.win.get_date_label(self.time))
        self.update_repeat_day()

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
        else:
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
        if self.entry_check_empty():
            return

        options = self.get_options()
        if self.check_changed(options):
            if self.id is None:
                reminder_id = self.app.run_service_method(
                    'AddReminder',
                    GLib.Variant(
                        '(sa{sv})',
                        (
                            info.app_id, 
                            {
                                'title': GLib.Variant('s', options['title']),
                                'description': GLib.Variant('s', options['description']),
                                'timestamp': GLib.Variant('u', options['timestamp']),
                                'repeat-type': GLib.Variant('q', options['repeat-type']),
                                'repeat-frequency': GLib.Variant('q', options['repeat-frequency']),
                                'repeat-days': GLib.Variant('q', options['repeat-days']),
                                'repeat-times': GLib.Variant('n', options['repeat-times']),
                                'repeat-until': GLib.Variant('u', options['repeat-until']),
                                'list': GLib.Variant('s', options['list']),
                                'user-id': GLib.Variant('s', options['user-id'])
                            }
                        )
                    )
                )
                self.id = reminder_id.unpack()[0]
                self.win.reminder_lookup_dict[self.id] = self.reminder
                self.reminder.id = self.id
            else:
                self.app.run_service_method(
                    'UpdateReminder',
                    GLib.Variant(
                        '(sa{sv})',
                        (
                            info.app_id,
                            {
                                'id': GLib.Variant('s', self.id),
                                'title': GLib.Variant('s', options['title']),
                                'description': GLib.Variant('s', options['description']),
                                'timestamp': GLib.Variant('u', options['timestamp']),
                                'repeat-type': GLib.Variant('q', options['repeat-type']),
                                'repeat-frequency': GLib.Variant('q', options['repeat-frequency']),
                                'repeat-days': GLib.Variant('q', options['repeat-days']),
                                'repeat-times': GLib.Variant('n', options['repeat-times']),
                                'repeat-until': GLib.Variant('u', options['repeat-until']),
                                'old-timestamp': GLib.Variant('u', options['old-timestamp']),
                                'list': GLib.Variant('s', options['list']),
                                'user-id': GLib.Variant('s', options['user-id'])
                            }
                        )
                    )
                )

            self.reminder.set_options(options)

        self.set_visible(False)
        if not self.reminder.get_visible():
            self.reminder.set_visible(True)
