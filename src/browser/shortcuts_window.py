# shortcuts_window.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gi.repository import Gtk

@Gtk.Template(resource_path='/io/github/retainerdevs/Retainer/ui/shortcuts_window.ui')
class ShortcutsWindow(Gtk.ShortcutsWindow):
    __gtype_name__ = 'ShortcutsWindow'

    def __init__(self, win, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))
        self.set_transient_for(win)

        self.present()
