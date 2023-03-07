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

from gi.repository import Gtk, Adw, GLib
from gettext import gettext as _
from math import floor

from remembrance import info
from remembrance.service.backend import RepeatType, RepeatDays
from enum import IntEnum

class TimeFormat(IntEnum):
    TWENTYFOUR_HOUR = 0
    TWELVE_HOUR = 1

DEFAULT_TITLE = _('Title')
DEFAULT_DESC = _('Description')

TIME_FORMAT = {
    '12h': 0,
    '24h': 1
}

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/reminder.ui')
class Reminder(Adw.ExpanderRow):
    '''Ui for each reminder'''
    __gtype_name__ = 'reminder'

    label_box = Gtk.Template.Child()
    time_label = Gtk.Template.Child()
    repeat_label = Gtk.Template.Child()
    title_entry = Gtk.Template.Child()
    description_entry = Gtk.Template.Child()
    time_expander_row = Gtk.Template.Child()
    done_button = Gtk.Template.Child()
    save_message = Gtk.Template.Child()
    discard_button = Gtk.Template.Child()
    time_row = None

    def __init__(
        self, app,
        reminder_id = None,
        timestamp = 0,
        default = False,
        completed = False,
        repeat_type = 0,
        repeat_frequency = 1,
        repeat_days = 0,
        repeat_until = 0,
        repeat_times = 1,
        old_timestamp = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.app = app
        self.repeat_type = repeat_type
        self.repeat_frequency = repeat_frequency
        self.repeat_days = repeat_days
        self.repeat_until = repeat_until
        self.repeat_times = repeat_times
        self.unsaved = []
        self.editing = False
        self.past = False

        self.id = reminder_id

        self.timestamp = timestamp
        self.old_timestamp = old_timestamp
        self.time_enabled = (timestamp != 0)
        self.time_row = TimeRow(self, timestamp, self.app.settings)
        self.set_time_label()

        if self.repeat_days == 0 or RepeatDays(self.repeat_days).bit_length() == 1:
            weekday = datetime.date.fromtimestamp(timestamp).weekday()
            self.repeat_days = 2**(weekday)

        self.completed = completed
        if self.id is None:
            self.discard_button.set_sensitive(False)
            self.done_button.set_sensitive(False)

        if self.completed:
            self.done_button.set_label(_('Incomplete'))
            self.done_button.set_css_classes(['opaque', 'incomplete'])
        else:
            self.done_button.set_label(_('Complete'))
            self.done_button.set_css_classes(['opaque', 'complete'])

        self.time_expander_row.set_enable_expansion(self.time_enabled)
        self.time_expander_row.add_row(self.time_row)        

        if default:
            self.set_title(DEFAULT_TITLE)
            self.set_subtitle(DEFAULT_DESC)
            self.unsaved_edits()
        else:
            self.title_entry.set_text(self.get_title())
            self.description_entry.set_text(self.get_subtitle())

        self.completed_icon = Gtk.Image(icon_name='object-select-symbolic')
        self.add_prefix(self.completed_icon)
        self.completed_icon_box = self.completed_icon.get_parent().get_parent()
        self.completed_icon_box.set_visible(self.completed)

        self.add_action(self.label_box)
        actions_box = self.label_box.get_parent()
        suffixes_box = actions_box.get_parent()
        actions_box.set_hexpand(True)
        actions_box.set_vexpand(False)
        suffixes_box.set_vexpand(True)
        actions_box.set_valign(Gtk.Align.FILL)
        actions_box.set_halign(Gtk.Align.END)
        self.update_label()

        self.past_due = Gtk.Image(icon_name='task-past-due-symbolic', visible=False)
        self.add_action(self.past_due)

        separator = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        self.add_action(separator)
        separator.set_halign(Gtk.Align.START)
        self.refresh_time()

    def set_time_label(self):
        if self.time_row is not None:
            timestamp = self.old_timestamp if self.past else self.timestamp
            time = GLib.DateTime.new_from_unix_local(timestamp)

        if timestamp != 0:
            self.time_label.set_visible(True)
            self.time_label.set_label(time.format(f'{self.time_row.get_date_label(True, time)} {self.time_row.get_time_label()}'))
        else:
            self.time_label.set_visible(False)

    def set_past(self, past):
        if self.past != past:
            self.past = past
            self.set_time_label()
            self.refresh_time()

    def update_repeat(self, timestamp, old_timestamp, repeat_times):
        self.set_timestamp(timestamp, old_timestamp)
        self.set_repeat_times(repeat_times)
        self.changed()
        self.get_parent().invalidate_sort()

    def set_repeat_times(self, times):
        self.repeat_times = times
        if not self.editing:
            self.time_row.repeat_times = self.repeat_times
            self.time_row.update_repeat_label()
        else:
            self.check_repeat_saved()
        self.update_repeat_label()

    def update_repeat_label(self):
        if self.repeat_type != 0:
            self.repeat_label.set_label(self.time_row.repeat_label.get_label())
            self.repeat_label.set_visible(True)
        else:
            self.repeat_label.set_visible(False)

    def update_label(self):
        self.set_time_label()
        self.update_repeat_label()

    def set_completed(self, completed):
        self.completed = completed

        if completed:
            self.done_button.set_label(_('Incomplete'))
            self.done_button.set_css_classes(['opaque', 'incomplete'])
            self.completed_icon_box.set_visible(True)
        else:
            self.done_button.set_label(_('Complete'))
            self.done_button.set_css_classes(['opaque', 'complete'])
            self.completed_icon_box.set_visible(False)

        self.refresh_time()
        self.app.win.reminders_list.invalidate_sort()

    def refresh_time(self):
        if self.past:
            self.past_due.set_visible(True)
        elif self.time_enabled and not self.completed:
            timestamp = self.timestamp
            now = floor(time.time())
            self.past_due.set_visible(timestamp <= now)
        else:
            self.past_due.set_visible(False)

    def update_day_label(self):
        self.set_time_label()
        self.time_row.update_date_button_label()

    def set_timestamp(self, timestamp, old_timestamp = None):
        if old_timestamp is not None and old_timestamp != self.old_timestamp:
            self.old_timestamp = old_timestamp
        if timestamp != self.timestamp:
            self.timestamp = timestamp
            if not self.editing:
                self.time_row.set_time(timestamp)
            else:
                self.check_time_saved()
        self.set_time_label()
        self.refresh_time()
        self.changed()

    def update_timestamp(self):
        self.time_enabled = self.time_expander_row.get_enable_expansion()
        if self.time_enabled:
            self.timestamp = self.time_row.get_timestamp()
        else:
            self.timestamp = 0

    def entry_check_empty(self):
        if len(self.title_entry.get_text()) == 0:
            if not self.title_entry.has_css_class('error'):
                self.title_entry.add_css_class('error')
            return True
        elif self.title_entry.has_css_class('error'):
            self.title_entry.remove_css_class('error')
        return False

    def saved_edits(self, name = None):
        # If a name is specified this method will only set that object as saved
        # If no name is specified it will set the whole reminder as saved
        if self.id is None and name is not None:
            return
        if name is not None:
            if name in self.unsaved:
                self.unsaved.remove(name)
            if len(self.unsaved) != 0:
                return
        else:
            self.unsaved = []
            # In case something weird happens with daylight savings time
            self.check_time_saved()
        self.editing = False
        self.save_message.set_reveal_child(False)
        if self in self.app.unsaved_reminders:
            self.app.unsaved_reminders.remove(self)

    def unsaved_edits(self, name = None):
        if name is not None:
            if name not in self.unsaved:
                self.unsaved.append(name)
            else:
                return
        self.editing = True
        self.save_message.set_reveal_child(True)
        if self not in self.app.unsaved_reminders:
            self.app.unsaved_reminders.append(self)

    def check_time_enabled_saved(self):
        if self.time_enabled != self.time_expander_row.get_enable_expansion():
            self.unsaved_edits('time-enabled')
        else:
            self.saved_edits('time-enabled')

    def check_time_saved(self):
        if self.time_row is not None and self.timestamp != 0:
            if self.time_row.get_timestamp() != self.timestamp:
                self.unsaved_edits('time')
            else:
                self.saved_edits('time')

    def check_repeat_saved(self):
        if self.time_row is not None:
            if self.time_row.repeat_frequency != self.repeat_frequency or \
            self.time_row.repeat_type != self.repeat_type or \
            self.time_row.repeat_days != self.repeat_days or \
            self.time_row.repeat_times != self.repeat_times or \
            self.time_row.repeat_until != self.repeat_until:
                self.unsaved_edits('repeat')
            else:
                self.saved_edits('repeat')

    def update(self, title, description, timestamp, repeat_type, repeat_frequency, repeat_days, repeat_until, repeat_times):
        self.set_title(title)
        self.set_subtitle(description)
        self.set_timestamp(timestamp)
        self.repeat_type = repeat_type
        self.repeat_days = repeat_days
        self.repeat_frequency = repeat_frequency
        self.repeat_until = repeat_until
        self.repeat_times = repeat_times

        if not self.editing:
            self.time_enabled = (timestamp != 0)
            self.title_entry.set_text(title)
            self.description_entry.set_text(description)
            self.time_row.set_time(timestamp)
            self.time_expander_row.set_enable_expansion(self.time_enabled)
            self.time_row.set_sensitive(self.time_enabled)
            self.time_row.update_repeat()
            self.changed()
        else:
            self.check_time_saved()
            self.check_repeat_saved()

        self.changed()
        self.get_parent().invalidate_sort()

    @Gtk.Template.Callback()
    def update_completed(self, button = None):
        if not self.completed:
            self.set_completed(True)
            if self.editing:
                self.app.win.selected = self.app.win.completed_row
                self.app.win.selected.emit('activate')
        else:
            self.set_completed(False)
            if self.editing:
                self.app.win.selected = self.app.win.all_row
                self.app.win.selected.emit('activate')

        self.app.run_service_method(
            'UpdateCompleted',
            GLib.Variant('(ssb)', (info.app_id, self.id, self.completed))
        )

        if not self.editing:
            self.set_expanded(False)

        self.changed()

    @Gtk.Template.Callback()
    def check_title_saved(self, object = None):
        if self.title_entry.has_css_class('error'):
            self.title_entry.remove_css_class('error')
        if self.title_entry.get_text() != self.get_title():
            self.unsaved_edits('title')
        else:
            self.saved_edits('title')

    @Gtk.Template.Callback()
    def check_description_saved(self, object = None):
        if self.description_entry.get_text() != self.get_subtitle():
            self.unsaved_edits('description')
        else:
            self.saved_edits('description')

    @Gtk.Template.Callback()
    def on_time_switch(self, switch, data = None):
        self.check_time_enabled_saved()

    @Gtk.Template.Callback()
    def discard_changes(self, button):
        self.title_entry.set_text(self.get_title())
        self.description_entry.set_text(self.get_subtitle())
        self.time_expander_row.set_enable_expansion(self.time_enabled)
        self.time_row.update_repeat()
        self.time_row.set_time(self.timestamp)
        self.saved_edits()

    @Gtk.Template.Callback()
    def on_save(self, button):
        if self.entry_check_empty():
            return

        self.update_timestamp()
        self.set_title(self.title_entry.get_text())
        self.set_subtitle(self.description_entry.get_text())
        self.repeat_type = self.time_row.repeat_type
        self.repeat_frequency = self.time_row.repeat_frequency
        self.repeat_days = self.time_row.repeat_days
        self.repeat_until = self.time_row.repeat_until
        self.update_label()

        if self.repeat_type == 0 and self.timestamp > floor(time.time()):
            self.time_row.repeat_times = 1

        self.repeat_times = self.time_row.repeat_times

        self.saved_edits()
        self.set_expanded(False)
        self.refresh_time()
        self.changed()
        self.get_parent().invalidate_sort()
        self.discard_button.set_sensitive(True)
        self.done_button.set_sensitive(True)

        if self.id is None:
            reminder_id = self.app.run_service_method(
                'AddReminder',
                GLib.Variant(
                    '(sa{sv})',
                    (
                        info.app_id, 
                        {
                            'title': GLib.Variant('s', self.get_title()),
                            'description': GLib.Variant('s', self.get_subtitle()),
                            'timestamp': GLib.Variant('u', self.timestamp),
                            'repeat-type': GLib.Variant('q', self.repeat_type),
                            'repeat-frequency': GLib.Variant('q', self.repeat_frequency),
                            'repeat-days': GLib.Variant('q', self.repeat_days),
                            'repeat-times': GLib.Variant('n', self.repeat_times),
                            'repeat-until': GLib.Variant('u', self.repeat_until)
                        }
                    )
                )
            )
            self.id = reminder_id.unpack()[0]
            self.app.win.reminder_lookup_dict[self.id] = self
        else:
            self.app.run_service_method(
                'UpdateReminder',
                GLib.Variant(
                    '(sa{sv})',
                    (
                        info.app_id,
                        {
                            'id': GLib.Variant('s', self.id),
                            'title': GLib.Variant('s', self.get_title()),
                            'description': GLib.Variant('s', self.get_subtitle()),
                            'timestamp': GLib.Variant('u', self.timestamp),
                            'repeat-type': GLib.Variant('q', self.repeat_type),
                            'repeat-frequency': GLib.Variant('q', self.repeat_frequency),
                            'repeat-days': GLib.Variant('q', self.repeat_days),
                            'repeat-times': GLib.Variant('n', self.repeat_times),
                            'repeat-until': GLib.Variant('u', self.repeat_until),
                            'old-timestamp': GLib.Variant('u', self.old_timestamp)
                        }
                    )
                )
            )

    @Gtk.Template.Callback()
    def on_remove(self, button):
        reminder = f'<b>{self.get_title()}</b>'
        confirm_dialog = Adw.MessageDialog(
            transient_for=self.app.win,
            heading=_('Remove reminder?'),
            body=_(f'This will remove the {reminder} reminder.'),
            body_use_markup=True
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('remove', _('Remove'))
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_response_appearance('remove', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.connect('response::remove', lambda *args: self.app.win.remove_reminder(self))
        confirm_dialog.present()

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/time_row.ui')
class TimeRow(Gtk.ListBoxRow):
    '''Section of reminder for handling times'''
    __gtype_name__ = 'time_row'

    date_label = Gtk.Template.Child()
    calendar = Gtk.Template.Child()
    hour_button = Gtk.Template.Child()
    hour_adjustment = Gtk.Template.Child()
    minute_adjustment = Gtk.Template.Child()
    am_pm_button = Gtk.Template.Child()
    repeat_label = Gtk.Template.Child()

    def __init__(self, reminder, timestamp, settings, **kwargs):
        super().__init__(**kwargs)
        self.hour_set = False
        self.parent_reminder = reminder

        self.update_repeat()
        self.set_time(timestamp)

        self.settings = settings
        self.set_time_format()
        self.hour_set = True
        self.settings.connect('changed::time-format', self.update_time_format)

    def update_repeat_day(self):
        if self.repeat_days == 0 or self.repeat_days in RepeatDays.__members__.values():
            repeat_days = 2**(self.time.get_day_of_week() - 1)
            if self.repeat_days != repeat_days:
                self.repeat_days = repeat_days
                self.update_repeat_label()

    def update_repeat_label(self):
        repeat_days_flag = RepeatDays(self.repeat_days)
        suffix = ''
        time = None
        if self.repeat_type == 0:
            self.repeat_label.set_label(_('Does not repeat'))
            return
        if self.repeat_type == RepeatType.MINUTE:
            if self.repeat_frequency == 1:
                type_name = _('minute')
            else:
                type_name = self.repeat_frequency + ' ' + _('minutes')
        elif self.repeat_type == RepeatType.HOUR:
            if self.repeat_frequency == 1:
                type_name = _('hour')
            else:
                type_name = self.repeat_frequency + ' ' + _('hours')
        elif self.repeat_type == RepeatType.DAY:
            if self.repeat_frequency == 1:
                type_name = _('day')
            else:
                type_name = self.repeat_frequency + ' ' + _('days')
        elif self.repeat_type == RepeatType.WEEK:
            days = []
            for day, flag in (
                # Translators: This is an abbreviation for Monday
                (_('M'), RepeatDays.MON),
                # Translators: This is an abbreviation for Tuesday
                (_('Tu'), RepeatDays.TUE),
                # Translators: This is an abbreviation for Wednesday
                (_('W'), RepeatDays.WED),
                # Translators: This is an abbreviation for Thursday
                (_('Th'), RepeatDays.THU),
                # Translators: This is an abbreviation for Friday
                (_('F'), RepeatDays.FRI),
                # Translators: This is an abbreviation for Saturday
                (_('Sa'), RepeatDays.SAT),
                # Translators: This is an abbreviation for Sunday
                (_('Su'), RepeatDays.SUN)
            ):
                if flag in repeat_days_flag:
                    days.append(day)

            if self.repeat_frequency == 1:
                type_name = _('week')
            else:
                type_name = str(self.repeat_frequency) + ' ' + _('weeks')
    
            suffix = f" ({','.join(days)})"
        
        if self.repeat_until > 0:
            date = GLib.DateTime.new_from_unix_local(self.repeat_until).format('%x')
            suffix += ' ' + _('until') + ' ' + date
        elif self.repeat_times == 1:
            # Translators: This is a noun, preceded by a number to represent the number of occurrences of something
            time = _('time')
        elif self.repeat_times != -1:
            # Translators: This is a noun, preceded by a number to represent the number of occurrences of something
            time = _('times')
        if time is not None:
            suffix += f' ({self.repeat_times} {time})'

        # Translators: This is a adjective, followed by a number to represent how often something occurs
        self.repeat_label.set_label(_('Every') + f' {type_name}{suffix}')

    def update_repeat(self):
        self.repeat_type = self.parent_reminder.repeat_type
        self.repeat_frequency = self.parent_reminder.repeat_frequency
        self.repeat_days = self.parent_reminder.repeat_days
        self.repeat_until = self.parent_reminder.repeat_until
        self.repeat_times = self.parent_reminder.repeat_times
        self.update_repeat_label()

    def set_time(self, timestamp):
        self.time = GLib.DateTime.new_now_local() if timestamp == 0 else GLib.DateTime.new_from_unix_local(timestamp)
        # Remove seconds from the time because it isn't important
        seconds = self.time.get_seconds()
        self.time = self.time.add_seconds(-(seconds))

        self.calendar.select_day(self.time)
        self.date_label.set_label(self.time.format(self.get_date_label()))
        self.minute_adjustment.set_value(self.time.get_minute())

    def update_date_button_label(self):
        self.date_label.set_label(self.time.format(self.get_date_label()))

    def get_date_label(self, long = False, time = None):
        time = self.time if time is None else time
        reminder_day = time.get_day_of_year()
        reminder_week = time.get_week_of_year()
        now = GLib.DateTime.new_now(GLib.TimeZone.new_local())
        today = now.get_day_of_year()
        week = now.get_week_of_year()

        if reminder_day == today:
            date = _('Today')
        elif reminder_day == today + 1:
            date = _('Tomorrow')
        elif reminder_day == today - 1:
            date = _('Yesterday')
        elif reminder_week == week:
            date = '%A'
        elif long:
            date = '%d %B %Y'
        else:
            date = '%x'
        return date

    def get_time_label(self):
        if self.time_format == TimeFormat.TWELVE_HOUR:
            time = f"%I:%M {_('PM') if self.pm else _('AM')}"
        else:
            time = '%H:%M'
        return time

    def set_time_format(self):
        setting = self.settings.get_enum('time-format')
        if setting == 0:
            if time.strftime('%p'):
                self.enable_12h()
            else:
                self.enable_24h()
        elif setting == 1:
            self.enable_12h()
        elif setting == 2:
            self.enable_24h()

    def update_time_format(self, key = None, data = None):
        self.set_time_format()
        self.parent_reminder.set_time_label()

    def enable_12h(self):
        self.am_pm_button.set_visible(True)
        self.time_format = TimeFormat.TWELVE_HOUR
        self.hour_adjustment.set_upper(11)
        if self.time.get_hour() >= 12:
            self.am_pm_button.set_label(_('PM'))
            self.pm = True
            self.hour_adjustment.set_value(self.time.get_hour() - 12)
        else:
            self.am_pm_button.set_label(_('AM'))
            self.pm = False
            self.hour_adjustment.set_value(self.time.get_hour())

    def enable_24h(self):
        self.am_pm_button.set_visible(False)
        self.time_format = TimeFormat.TWENTYFOUR_HOUR
        self.hour_adjustment.set_upper(23)
        self.hour_adjustment.set_value(self.time.get_hour())

    def get_timestamp(self):
        return self.time.to_unix()

    def update_calendar(self):
        self.calendar.select_day(self.time)
        self.date_label.set_label(self.time.format(self.get_date_label()))

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

    def close_request(self, window):
        values = window.return_values()
        self.repeat_type = values[0]
        if self.repeat_type == 0 and self.parent_reminder.repeat_type == 0:
            self.update_repeat()
        else:
            self.repeat_type, self.repeat_frequency, self.repeat_days, self.repeat_until, self.repeat_times = values
    
        self.update_repeat_label()
        self.parent_reminder.check_repeat_saved()

    @Gtk.Template.Callback()
    def launch_repeat_window(self, button):
        repeat_dialog = RepeatDialog(self)
        repeat_dialog.set_transient_for(self.parent_reminder.app.win)
        repeat_dialog.set_modal(True)
        repeat_dialog.present()

        repeat_dialog.connect('close-request', self.close_request)

    @Gtk.Template.Callback()
    def show_leading_zeros(self, spin_button):
        spin_button.set_text(f'{spin_button.get_value_as_int():02d}')
        return True

    @Gtk.Template.Callback()
    def hour_output(self, spin_button):
        value = spin_button.get_value_as_int()
        if self.time_format == TimeFormat.TWELVE_HOUR and value == 0:
            value = 12
        spin_button.set_text(f'{value:02d}')
        return True

    @Gtk.Template.Callback()
    def hour_input(self, spin_button, gpointer):
        new_value = int(spin_button.get_text())
        if self.time_format == TimeFormat.TWELVE_HOUR and new_value == 12:
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
        self.parent_reminder.check_time_saved()
        self.update_repeat_day()

    @Gtk.Template.Callback()
    def hour_changed(self, adjustment = None):
        value = self.hour_adjustment.get_value()
        old_value = self.time.get_hour()
        if self.time_format == TimeFormat.TWELVE_HOUR:
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
        self.parent_reminder.check_time_saved()
        self.update_repeat_day()

    @Gtk.Template.Callback()
    def day_changed(self, calendar = None, day = None):
        date = self.calendar.get_date()
        new_day = date.get_day_of_year()
        old_day = self.time.get_day_of_year()
        days = new_day - old_day
        self.time = self.time.add_days(days)
        if self.hour_set:
            self.hour_changed()
        self.date_label.set_label(self.time.format(self.get_date_label()))
        self.parent_reminder.check_time_saved()
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
            if not self.time_format == TimeFormat.TWELVE_HOUR or self.pm:
                self.time = self.time.add_days(1)
                self.update_calendar()
            if self.time_format == TimeFormat.TWELVE_HOUR:
                self.toggle_am_pm()
        else:
            if not self.time_format == TimeFormat.TWELVE_HOUR or not self.pm:
                self.time = self.time.add_days(-1)
                self.update_calendar()
            if self.time_format == TimeFormat.TWELVE_HOUR:
                self.toggle_am_pm()

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/repeat_dialog.ui')
class RepeatDialog(Adw.Window):
    '''Window for repeat settings'''
    __gtype_name__ = 'repeat_dialog'

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
    repeat_until_label = Gtk.Template.Child()
    repeat_times_box = Gtk.Template.Child()
    calendar = Gtk.Template.Child()
    repeat_duration_button = Gtk.Template.Child()

    def __init__(self, time_row, **kwargs):
        super().__init__(**kwargs)
        self.time_row = time_row
        self.setup()

    def setup(self):
        repeat_type = self.time_row.repeat_type
        repeat_frequency = self.time_row.repeat_frequency
        repeat_days = self.time_row.repeat_days
        repeat_until = self.time_row.repeat_until
        repeat_times = self.time_row.repeat_times

        enabled = repeat_type != 0

        if enabled:
            self.repeat_type_button.set_selected(repeat_type - 1)

        if enabled and repeat_times != -1:
            self.repeat_times_btn.set_value(repeat_times)
            self.repeat_duration_button.set_selected(1)
        elif enabled and repeat_until > 0:
            self.repeat_times_btn.set_value(5)
            self.repeat_duration_button.set_selected(2)
        else:
            self.repeat_times_btn.set_value(5)
            self.repeat_duration_button.set_selected(0)

        if repeat_until != 0:
            self.calendar.select_day(GLib.DateTime.new_from_unix_local(repeat_until))

        self.frequency_btn.set_value(repeat_frequency)
        self.repeat_duration_selected_changed()
        self.repeat_type_selected_changed()

        repeat_days_flag = RepeatDays(repeat_days)
        for btn, flag in (
            (self.mon_btn, RepeatDays.MON),
            (self.tue_btn, RepeatDays.TUE),
            (self.wed_btn, RepeatDays.WED),
            (self.thu_btn, RepeatDays.THU),
            (self.fri_btn, RepeatDays.FRI),
            (self.sat_btn, RepeatDays.SAT),
            (self.sun_btn, RepeatDays.SUN)
        ):
            btn.set_active(flag in repeat_days_flag)

        self.day_changed()
        self.repeat_row.set_enable_expansion(enabled)

        if enabled:
            self.repeat_row.set_expanded(True)

    def return_values(self):
        repeat_type = 0 if not self.repeat_row.get_enable_expansion() else self.repeat_type_button.get_selected() + 1
        repeat_frequency = int(self.frequency_btn.get_value())
        self.frequency_btn.update()
        self.repeat_times_btn.update()

        if repeat_type != 0:
            if self.repeat_duration_button.get_selected() == 0:
                repeat_times = -1
                repeat_until = 0
            elif self.repeat_duration_button.get_selected() == 1:
                repeat_times = int(self.repeat_times_btn.get_value())
                repeat_until = 0
            elif self.repeat_duration_button.get_selected() == 2:
                repeat_times = -1
                repeat_until = datetime.datetime(self.calendar.props.year, self.calendar.props.month + 1, self.calendar.props.day).timestamp()

            repeat_days = 0
            for btn, flag in (
                (self.mon_btn, RepeatDays.MON),
                (self.tue_btn, RepeatDays.TUE),
                (self.wed_btn, RepeatDays.WED),
                (self.thu_btn, RepeatDays.THU),
                (self.fri_btn, RepeatDays.FRI),
                (self.sat_btn, RepeatDays.SAT),
                (self.sun_btn, RepeatDays.SUN)
            ):
                if btn.get_active():
                    repeat_days += flag
        else:
            now = floor(time.time())
            repeat_frequency = 1
            repeat_days = 0
            repeat_until = 0
            repeat_times = 1 if now > self.time_row.get_timestamp() else 0

        return repeat_type, repeat_frequency, repeat_days, repeat_until, repeat_times

    @Gtk.Template.Callback()
    def day_changed(self, calendar = None, data = None):
        self.repeat_until_label.set_label(self.calendar.get_date().format('%d %b %Y'))

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
        self.week_repeat_row.set_visible(repeat_type == RepeatType.WEEK)
