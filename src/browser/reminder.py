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

from gi.repository import Gtk, Adw, GLib
from gettext import gettext as _

from remembrance import info

DEFAULT_TITLE = 'Title'
DEFAULT_DESC = 'Description'

TIME_FORMAT = {
    '12h': 0,
    '24h': 1
}

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/reminder.ui')
class Reminder(Adw.ExpanderRow):
    '''Ui for each reminder'''
    __gtype_name__ = 'reminder'

    title_entry = Gtk.Template.Child()
    description_entry = Gtk.Template.Child()
    time_switch_box = Gtk.Template.Child()
    time_switch = Gtk.Template.Child()
    done_button = Gtk.Template.Child()
    save_message = Gtk.Template.Child()
    time_box = None

    def __init__(self, app, reminder_id = None, timestamp = 0, default = False, completed = False, **kwargs):
        super().__init__(**kwargs)
        self.label = Gtk.Label()
        self.app = app
        self.time_enabled = (timestamp != 0)
        self.time_box = TimeBox(self, timestamp, self.app.settings)
        self.timestamp = timestamp
        self.saved_edits()

        self.completed = completed
        self.id = reminder_id

        if self.completed:
            self.done_button.set_label(_('Incomplete'))
            self.done_button.set_css_classes(['opaque', 'incomplete'])
        else:
            self.done_button.set_label(_('Complete'))
            self.done_button.set_css_classes(['opaque', 'complete'])

        self.time_switch.set_active(self.time_enabled)
        self.time_switch_box.append(self.time_box)
        self.time_box.set_sensitive(self.time_enabled)

        if default:
            self.set_title(DEFAULT_TITLE)
            self.set_subtitle(DEFAULT_DESC)
            self.unsaved_edits()
        else:
            self.title_entry.set_text(self.get_title())
            self.description_entry.set_text(self.get_subtitle())

        self.completed_icon = Gtk.Image(icon_name='object-select-symbolic', visible=False)
        self.add_action(self.completed_icon)
        self.completed_icon.set_visible(self.completed)

        if self.time_enabled:
            self.label.set_visible(True)
            self.label.set_label(self.time_box.get_long_label())
        else:
            self.label.set_visible(False)

        self.add_action(self.label)

        self.past_due = Gtk.Image(icon_name='task-past-due-symbolic', visible=False)
        self.add_action(self.past_due)

        self.refresh_time()

    def set_completed(self, completed):
        self.completed = completed

        if completed:
            self.done_button.set_label(_('Incomplete'))
            self.done_button.set_css_classes(['opaque', 'incomplete'])
            self.completed_icon.set_visible(True)
        else:
            self.done_button.set_label(_('Complete'))
            self.done_button.set_css_classes(['opaque', 'complete'])
            self.completed_icon.set_visible(False)

        self.refresh_time()
        self.changed()
        self.app.win.reminders_list.invalidate_sort()

    def refresh_time(self):
        if self.time_enabled and not self.completed:
            now = int(time.time())
            self.past_due.set_visible(self.timestamp <= now)
        else:
            self.past_due.set_visible(False)

    def update_label(self):
        self.label.set_label(self.time_box.get_long_label())
        self.time_box.update_date_button_label()

    def update_timestamp(self):
        self.time_enabled = self.time_switch.get_active()
        if self.time_enabled:
            self.label.set_visible(True)
            self.label.set_label(self.time_box.get_long_label())
            self.timestamp = self.time_box.get_timestamp()
        else:
            self.label.set_visible(False)
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
        if name is not None:
            if name in self.unsaved:
                self.unsaved.remove(name)
            if len(self.unsaved) != 0:
                return
        else:
            self.unsaved = []
        self.editing = False
        self.save_message.set_reveal_child(False)

    def unsaved_edits(self, name = None):
        if name is not None:
            if name not in self.unsaved:
                self.unsaved.append(name)
            else:
                return
        self.editing = True
        self.save_message.set_reveal_child(True)

    def check_time_enabled_saved(self):
        if self.time_enabled != self.time_switch.get_active():
            self.unsaved_edits('time-enabled')
        else:
            self.saved_edits('time-enabled')

    def check_time_saved(self):
        if self.time_box is not None and self.timestamp is not None:
            if self.time_box.get_timestamp() != self.timestamp:
                self.unsaved_edits('time')
            else:
                self.saved_edits('time')

    def update(self, title, description, timestamp):
        self.set_title(title)
        self.set_subtitle(description)
        self.timestamp = timestamp

        if not self.editing:
            self.time_enabled = (timestamp != 0)
            self.title_entry.set_text(title)
            self.description_entry.set_text(description)
            self.time_box.set_time(timestamp)
            self.time_switch.set_active(self.time_enabled)
            self.time_box.set_sensitive(self.time_enabled)
        else:
            self.check_time_saved()

    @Gtk.Template.Callback()
    def update_completed(self, button = None):
        if not self.completed:
            self.set_completed(True)
        else:
            self.set_completed(False)

        self.app.run_service_method(
            'UpdateCompleted',
            GLib.Variant('(ssb)', (info.app_id, self.id, self.completed))
        )
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
    def on_time_switch(self, switch, state):
        self.time_box.set_sensitive(state)
        self.check_time_enabled_saved()

    @Gtk.Template.Callback()
    def on_save(self, button):
        if self.entry_check_empty():
            return

        self.update_timestamp()
        self.set_title(self.title_entry.get_text())
        self.set_subtitle(self.description_entry.get_text())
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
                            'timestamp': GLib.Variant('u', self.timestamp)
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
                            'timestamp': GLib.Variant('u', self.timestamp)
                        }
                    )
                )
            )
        self.saved_edits()
        self.set_expanded(False)
        self.refresh_time()
        self.changed()
        self.get_parent().invalidate_sort()

    @Gtk.Template.Callback()
    def on_remove(self, button):
        if self.id is not None:
            confirm_dialog = Adw.MessageDialog(
                transient_for=self.app.win,
                heading=_('Remove reminder?'),
                body=_(f'This will remove the <b>{self.get_title()}</b> reminder.'),
                body_use_markup=True
            )
            confirm_dialog.add_response('cancel', _('Cancel'))
            confirm_dialog.add_response('remove', _('Remove'))
            confirm_dialog.set_default_response('cancel')
            confirm_dialog.set_response_appearance('remove', Adw.ResponseAppearance.DESTRUCTIVE)
            confirm_dialog.connect('response::remove', lambda *args: self.app.win.remove_reminder(self))
            confirm_dialog.present()
        else:
            self.app.win.remove_reminder(self)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/time_box.ui')
class TimeBox(Gtk.Box):
    '''Section of reminder for handling times'''
    __gtype_name__ = 'time_box'

    date_button = Gtk.Template.Child()
    calendar = Gtk.Template.Child()
    hour_button = Gtk.Template.Child()
    hour_adjustment = Gtk.Template.Child()
    minute_adjustment = Gtk.Template.Child()
    am_pm_button = Gtk.Template.Child()

    def __init__(self, reminder, timestamp, settings, **kwargs):
        super().__init__(**kwargs)

        self.parent_reminder = reminder

        self.set_time(timestamp)

        self.settings = settings
        self.set_time_format(timestamp)
        self.settings.connect('changed::time-format', self.set_time_format)

    def set_time(self, timestamp):
        self.time = GLib.DateTime.new_now_local() if timestamp == 0 else GLib.DateTime.new_from_unix_local(timestamp)
        # Remove seconds from the time because it isn't important
        seconds = self.time.get_seconds()
        self.time = self.time.add_seconds(-(seconds))

        self.calendar.select_day(self.time)
        self.date_button.set_label(self.time.format(self.get_date_label()))
        self.minute_adjustment.set_value(self.time.get_minute())

    def get_long_label(self):
        return self.time.format(f'{self.get_date_label(True)} {self.get_time_label()}')

    def update_date_button_label(self):
        self.date_button.set_label(self.time.format(self.get_date_label()))

    def get_date_label(self, long = False):
        reminder_day = self.time.get_day_of_year()
        reminder_week = self.time.get_week_of_year()
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
            date = '%d %b %Y'
        else:
            date = '%x'
        return date

    def get_time_label(self):
        if self.time_format == TIME_FORMAT['12h']:
            time = f"%I:%M {_('PM') if self.pm else _('AM')}"
        else:
            time = '%H:%M'
        return time

    def set_time_format(self, key = None, data = None):
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
        self.parent_reminder.label.set_label(self.get_long_label())

    def enable_12h(self):
        self.am_pm_button.set_visible(True)
        self.time_format = TIME_FORMAT['12h']
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
        self.time_format = TIME_FORMAT['24h']
        self.hour_adjustment.set_upper(23)
        self.hour_adjustment.set_value(self.time.get_hour())

    def get_timestamp(self):
        return self.time.to_unix()

    def update_calendar(self):
        self.calendar.select_day(self.time)
        self.date_button.set_label(self.time.format(self.get_date_label()))

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

    @Gtk.Template.Callback()
    def show_leading_zeros(self, spin_button):
        spin_button.set_text(f'{spin_button.get_value_as_int():02d}')
        return True

    @Gtk.Template.Callback()
    def hour_output(self, spin_button):
        value = spin_button.get_value_as_int()
        if self.time_format == TIME_FORMAT['12h'] and value == 0:
            value = 12
        spin_button.set_text(f'{value:02d}')
        return True

    @Gtk.Template.Callback()
    def hour_input(self, spin_button, gpointer):
        new_value = int(spin_button.get_text())
        if self.time_format == TIME_FORMAT['12h'] and new_value == 12:
            new_value = 0
        double = ctypes.c_double.from_address(hash(gpointer))
        double.value = float(new_value)
        return True

    @Gtk.Template.Callback()
    def on_am_pm_button_pressed(self, button = None):
        self.toggle_am_pm()
        self.hour_changed()

    @Gtk.Template.Callback()
    def minute_changed(self, adjustment = None):
        minutes = self.minute_adjustment.get_value() - self.time.get_minute()
        self.time = self.time.add_minutes(minutes)
        self.parent_reminder.check_time_saved()

    @Gtk.Template.Callback()
    def hour_changed(self, adjustment = None):
        value = self.hour_adjustment.get_value()
        old_value = self.time.get_hour()
        if self.time_format == TIME_FORMAT['12h']:
            if self.pm:
                value += 12
            if value >= 12 and not self.pm:
                self.set_pm()
            elif value < 12 and self.pm:
                self.set_am()

            self.update_calendar()

        hours = value - old_value

        self.time = self.time.add_hours(hours)
        self.parent_reminder.check_time_saved()

    @Gtk.Template.Callback()
    def day_changed(self, calendar):
        new_day = calendar.get_date().get_day_of_year()
        old_day = self.time.get_day_of_year()
        days = new_day - old_day
        self.time = self.time.add_days(days)
        self.date_button.set_label(self.time.format(self.get_date_label()))
        self.parent_reminder.check_time_saved()

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
            if not self.time_format == TIME_FORMAT['12h'] or self.pm:
                self.time = self.time.add_days(1)
                self.update_calendar()
            if self.time_format == TIME_FORMAT['12h']:
                self.toggle_am_pm()
        else:
            if not self.time_format == TIME_FORMAT['12h'] or not self.pm:
                self.time = self.time.add_days(-1)
                self.update_calendar()
            if self.time_format == TIME_FORMAT['12h']:
                self.toggle_am_pm()
