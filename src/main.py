# main.py - Main module for Remembrance
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

import sys
import gi
import random
import string

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _

from remembrance.reminder import Reminder
from remembrance.backend import Reminders
from remembrance.about import about_window
from remembrance import info

@Gtk.Template(resource_path='/com/github/dgsasha/remembrance/ui/main.ui')
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'application_window'

    main_box = Gtk.Template.Child()
    upcoming_reminders_list = Gtk.Template.Child()
    add_reminder = Gtk.Template.Child()
    completed_reminders_list = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.upcoming_placeholder = Adw.ActionRow(
            title=_('Press the plus button to add a reminder')
        )
        self.completed_placeholder = Adw.ActionRow(
            title=_('No reminders have been marked as complete')
        )
        self.app = self.get_application()
        self.upcoming_reminders_list.set_sort_func(self.sort_func)
        self.completed_reminders_list.set_sort_func(self.sort_func)

        self.reminder_lookup_dict = {}
        self.connect('close-request', self.on_close)

        dictionary = self.app.reminders.dict
        for reminder_id in dictionary:
            reminder = Reminder(
                self.app,
                reminder_id=reminder_id,
                title=dictionary[reminder_id]['title'],
                subtitle=dictionary[reminder_id]['description'],
                time_enabled=dictionary[reminder_id]['time-enabled'],
                timestamp=dictionary[reminder_id]['timestamp'],
                completed = dictionary[reminder_id]['completed']
            )
            if not dictionary[reminder_id]['completed']:
                self.upcoming_reminders_list.append(reminder)
            else:
                self.completed_reminders_list.append(reminder)

            self.reminder_lookup_dict[reminder_id] = reminder

        self.update_placeholder()

    def sort_func(self, row1, row2):
        if not hasattr(row1, 'timestamp') and not hasattr(row2, 'timestamp'):
            return 0
        if not hasattr(row1, 'timestamp'):
            return -1
        if not hasattr(row1, 'timestamp'):
            return 1
        if row1.timestamp == row2.timestamp:
            return 0
        if row1.timestamp < row2.timestamp:
            return -1
        return 1

    def update_placeholder(self):
        first_row = self.upcoming_reminders_list.get_row_at_index(0)
        if first_row is None:
            self.upcoming_reminders_list.append(self.upcoming_placeholder)
        elif first_row is self.upcoming_placeholder:
            self.upcoming_reminders_list.remove(self.upcoming_placeholder)

        first_row = self.completed_reminders_list.get_row_at_index(0)
        if first_row is None:
            self.completed_reminders_list.append(self.completed_placeholder)
        elif first_row is self.completed_placeholder:
            self.completed_reminders_list.remove(self.completed_placeholder)

    def move_reminder(self, reminder):
        if reminder.get_property('completed'):
            self.upcoming_reminders_list.remove(reminder)
            self.completed_reminders_list.append(reminder)
        else:
            self.completed_reminders_list.remove(reminder)
            self.upcoming_reminders_list.append(reminder)

        self.update_placeholder()

    def remove_reminder(self, reminder):
        self.app.withdraw_notification(reminder.id)

        if reminder.countdown_id is not None and not reminder.countdown:
            GLib.Source.remove(reminder.countdown_id)

        self.app.reminders.remove_reminder(reminder.id)

        if not reminder.get_property('completed'):
            self.upcoming_reminders_list.remove(reminder)
        else:
            self.completed_reminders_list.remove(reminder)

        self.update_placeholder()

    def _generate_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def do_generate_id(self):
        new_id = self._generate_id()
        while new_id in self.app.reminders.dict: # if for some reason it isn't unique
            new_id = self._generate_id()

        return new_id

    def on_close(self, window):
        unsaved = []
        for reminder in self.reminder_lookup_dict.values():
            if reminder.editing:
                unsaved.append(reminder)

        if len(unsaved) > 0:
            confirm_dialog = Adw.MessageDialog(
                transient_for=self,
                heading=_('You have unsaved changes'),
                body=_('Are you sure you want to close the window?'),
            )
            confirm_dialog.add_response('cancel', _('Cancel'))
            confirm_dialog.add_response('yes', _('Yes'))
            confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
            confirm_dialog.set_default_response('cancel')
            confirm_dialog.set_close_response('cancel')
            confirm_dialog.connect('response::cancel', lambda *args: self.cancel_close(unsaved))
            confirm_dialog.connect('response::yes', lambda *args: self.close_window())
            confirm_dialog.present()

            return True
        else:
            self.close_window()

    def close_window(self):
        self.destroy()

    def cancel_close(self, unsaved):
        for reminder in unsaved:
            reminder.set_expanded(True)

    @Gtk.Template.Callback()
    def new_reminder(self, button):
        reminder_id = self.do_generate_id()
        reminder = Reminder(
            self.app,
            reminder_id = reminder_id,
            default=True,
            expanded=True
        )

        self.upcoming_reminders_list.prepend(reminder)
        self.reminder_lookup_dict[reminder_id] = reminder
        self.update_placeholder()

class Remembrance(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register()
        self.create_action('reminder-completed', self.on_notification_completed)

        self.reminders = Reminders(self)

        self.connect('activate', self.on_activate)

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        action.set_enabled(True)

        self.add_action(action)

    def on_notification_completed(self, action, reminder_id):
        self.reminders.set_completed(reminder_id, True)

    def on_activate(self, app):
        self.win = self.props.active_window
        if not self.win:
            self.win = MainWindow(application=app)
        self.create_action('about', self.show_about)
        self.create_action('quit', self.quit_app)
        provider = Gtk.CssProvider()
        provider.load_from_resource('/com/github/dgsasha/remembrance/stylesheet.css')
        Gtk.StyleContext.add_provider_for_display(self.win.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win.present()

    def show_about(self, action, data):
        win = about_window(self.win)
        win.present()

    def quit_app(self, action, data):
        self.quit()

def main():
    app = Remembrance(application_id=info.app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
    return app.run(sys.argv)
