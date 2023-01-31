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

import datetime
import time

from gi.repository import Gtk, Adw, GLib, GObject
from gettext import gettext as _

DEFAULT_TITLE = 'Title'
DEFAULT_DESC = 'Description'

@Gtk.Template(resource_path='/com/github/dgsasha/remembrance/ui/reminder.ui')
class Reminder(Adw.ExpanderRow):
    __gtype_name__ = 'reminder'

    title_entry = Gtk.Template.Child()
    description_entry = Gtk.Template.Child()
    time_box = Gtk.Template.Child()
    date_button = Gtk.Template.Child()
    calendar = Gtk.Template.Child()
    hour_adjustment = Gtk.Template.Child()
    minute_adjustment = Gtk.Template.Child()
    time_switch = Gtk.Template.Child()
    done_button = Gtk.Template.Child()
    save_message = Gtk.Template.Child()
    _completed = False

    def __init__(self, app, reminder_id, time_enabled = False, timestamp = 0, default = False, completed = False, **kwargs):
        super().__init__(**kwargs)
        self.saved_edits()
        self.time_enabled = time_enabled

        self.app = app
        self.countdown = None
        self.countdown_id = None
        self._completed = completed
        self.id = reminder_id

        if self._completed:
            self.done_button.set_label(_('Incomplete'))
            self.done_button.set_css_classes(['opaque', 'incomplete'])
        else:
            self.done_button.set_label(_('Complete'))
            self.done_button.set_css_classes(['opaque', 'complete'])

        if timestamp == 0:
            time = datetime.datetime.now()
        else:
            time = datetime.datetime.fromtimestamp(timestamp)

        time_zone = GLib.TimeZone.new_local()

        self.time = GLib.DateTime(
            time_zone,
            time.year,
            time.month,
            time.day,
            time.hour,
            time.minute,
            0 # seconds are not important here
        )

        self.timestamp = self.time.to_unix() if self.time_enabled else 0

        self.time_switch.set_active(self.time_enabled)
        self.time_box.set_sensitive(self.time_enabled)

        if default:
            self.set_title(DEFAULT_TITLE)
            self.set_subtitle(DEFAULT_DESC)
        else:
            self.title_entry.set_text(self.get_title())
            self.description_entry.set_text(self.get_subtitle())

        self.label = Gtk.Label()

        if self.time_enabled:
            self.label.set_visible(True)
            self.label.set_label(self.time.format(f'{self.get_date_label(True)} %H:%M'))
        else:
            self.label.set_visible(False)

        self.add_action(self.label)

        self.past_due = Gtk.Image(icon_name='task-past-due-symbolic', visible=False)
        self.add_action(self.past_due)

        self.refresh_time()

        self.date_button.set_label(self.time.format(self.get_date_label()))

        self.hour_adjustment.set_value(self.time.get_hour())
        self.minute_adjustment.set_value(self.time.get_minute())

    def get_date_label(self, long_month = False):
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
        elif long_month:
            date = '%d %B %Y'
        else:
            date = '%d %b %Y'
        return date

    def saved_edits(self):
        self.editing = False
        self.save_message.set_reveal_child(False)

    def unsaved_edits(self):
        self.editing = True
        self.save_message.set_reveal_child(True)

    def update_calendar(self):
        self.calendar.select_day(self.time)
        self.date_button.set_label(self.time.format(self.get_date_label()))

    def refresh_time(self):
        if self.time_enabled:
            now = int(time.time())
            self.past_due.set_visible(self.timestamp < now)

    def set_countdown(self):
        self.app.reminders.set_countdown(
            self.id,
            self.get_title(),
            self.get_subtitle(),
            self.timestamp,
            self.countdown_id
        )

    @GObject.Property(type=bool, default=False)
    def completed(self):
        return self._completed

    @Gtk.Template.Callback()
    def update_completed_property(self, button):
        if not self._completed:
            completed = True
            button.set_label(_('Incomplete'))
            self.done_button.set_css_classes(['opaque', 'incomplete'])
            if self.countdown_id is not None:
                GLib.Source.remove(self.countdown_id)
            self.app.withdraw_notification(self.id)
        else:
            completed = False
            button.set_label(_('Complete'))
            self.done_button.set_css_classes(['opaque', 'complete'])
            if self.time_enabled:
                self.set_countdown()

        self._completed = completed
        self.app.reminders.set_completed(self.id, self.completed)
        self.app.win.move_reminder(self)

    @Gtk.Template.Callback()
    def check_unsaved_edits(self, object = None):
        if self.title_entry.get_text() != self.get_title() or \
        self.description_entry.get_text() != self.get_subtitle() or \
        self.time_enabled != self.time_switch.get_active() or \
        (self.time_enabled and self.time.to_unix() != self.timestamp):
            self.unsaved_edits()
        else:
            self.saved_edits()

    @Gtk.Template.Callback()
    def on_time_switch(self, switch, state):
        self.time_box.set_sensitive(state)
        self.check_unsaved_edits()

    @Gtk.Template.Callback()
    def show_leading_zeros(self, spin_button):
        spin_button.set_text(f'{spin_button.get_value_as_int():02d}')
        return True

    @Gtk.Template.Callback()
    def minute_changed(self, adjustment):
        minutes = adjustment.get_value() - self.time.get_minute()
        self.time = self.time.add_minutes(minutes)
        self.check_unsaved_edits()

    @Gtk.Template.Callback()
    def hour_changed(self, adjustment):
        hours = adjustment.get_value() - self.time.get_hour()
        self.time = self.time.add_hours(hours)
        self.check_unsaved_edits()

    @Gtk.Template.Callback()
    def day_changed(self, calendar):
        new_day = calendar.get_date().get_day_of_year()
        old_day = self.time.get_day_of_year()
        days = new_day - old_day
        self.time = self.time.add_days(days)
        self.date_button.set_label(self.time.format(self.get_date_label()))
        self.check_unsaved_edits()

    @Gtk.Template.Callback()
    def wrap_minute(self, button):
        if button.get_adjustment().get_value() == 0:
            new_value = self.hour_adjustment.get_value() + 1
        else:
            new_value = self.hour_adjustment.get_value() - 1

        self.hour_adjustment.set_value(new_value)

    @Gtk.Template.Callback()
    def wrap_hour(self, button):
        if button.get_adjustment().get_value() == 0:
            self.time = self.time.add_days(1)
        else:
            self.time = self.time.add_days(-1)

        self.update_calendar()

    @Gtk.Template.Callback()
    def on_save(self, button):
        self.time_enabled = self.time_switch.get_active()
        if self.time_enabled:
            self.label.set_visible(True)
            self.label.set_label(self.time.format(f'{self.get_date_label(True)} %H:%M'))
            self.timestamp = self.time.to_unix()
        else:
            self.label.set_visible(False)
            self.timestamp = 0
        self.set_title(self.title_entry.get_text())
        self.set_subtitle(self.description_entry.get_text())
        self.app.reminders.remove_reminder(self.id)
        self.app.reminders.add_reminder(self.id, self.get_title(), self.get_subtitle(), self.time_enabled, self.timestamp)
        self.saved_edits()
        self.set_expanded(False)
        self.refresh_time()
        if self.time_enabled and not self.completed:
            self.set_countdown()
        elif self.countdown_id is not None:
            GLib.Source.remove(self.countdown_id)
        self.changed()
        self.get_parent().invalidate_sort()

    @Gtk.Template.Callback()
    def on_remove(self, button):
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
