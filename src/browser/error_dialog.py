# error_dialog.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gi.repository import Gtk, Adw

from retainer import info

@Gtk.Template(resource_path='/io/github/retainerdevs/Retainer/ui/error_dialog.ui')
class ErrorDialog(Gtk.Window):
    __gtype_name__ = 'ErrorDialog'

    body = Gtk.Template.Child()
    error = Gtk.Template.Child()
    main = Gtk.Template.Child()

    def __init__(self, app, title: str, body: str, error: str, parent_window = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title(title)
        self.body.set_label(body)
        self.error.set_buffer(Gtk.TextBuffer(text=error))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        if info.on_windows:
            self.set_titlebar(None)
            sep = Gtk.Separator()
            sep.add_css_class('titlebar-separator')
            self.main.prepend(sep)

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
        else:
            self.set_application(app)
            self.present()

