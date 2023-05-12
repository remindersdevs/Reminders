# error_dialog.py
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

from gi.repository import Gtk, Adw, GLib

from reminders import info

@Gtk.Template(resource_path='/io/github/remindersdevs/Reminders/ui/error_dialog.ui')
class ErrorDialog(Adw.Window):
    __gtype_name__ = 'ErrorDialog'

    body = Gtk.Template.Child()
    error = Gtk.Template.Child()

    def __init__(self, app, title: str, body: str, error: str, parent_window = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title(title)
        self.body.set_label(body)
        self.error.set_buffer(Gtk.TextBuffer(text=error))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        if app.win is not None:
            if parent_window is None:
                parent_window = app.win
                if app.preferences is not None and app.preferences.is_visible():
                    parent_window = app.preferences
                elif app.win.reminder_edit_win is not None and app.win.reminder_edit_win.is_visible():
                    parent_window = app.win.reminder_edit_win
                elif app.win.edit_lists_window is not None and app.win.edit_lists_window.is_visible():
                    parent_window = app.win.edit_lists_window
            self.set_transient_for(parent_window)
            self.set_modal(True)

            self.present()

            if info.on_windows:
                app.center_win_on_parent(self)
        else:
            Gtk.StyleContext.add_provider_for_display(self.get_display(), app.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.set_application(app)
            self.present()

