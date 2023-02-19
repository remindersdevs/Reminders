# Remembrance preferences window
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

from gi.repository import Gtk, Adw, Gio

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    '''Settings Window'''
    __gtype_name__ = 'PreferencesWindow'
    time_format_row = Gtk.Template.Child()
    completed_last_row = Gtk.Template.Child()
    completed_reversed_switch = Gtk.Template.Child()

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.settings = app.settings
        self.settings.connect('changed::time-format', lambda *args : self.update_dropdown())
        self.update_dropdown()
        self.time_format_row.connect('notify::selected', lambda *args : self.update_time_format())
        self.settings.bind('completed-last', self.completed_last_row, 'enable-expansion', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('completed-reversed', self.completed_reversed_switch, 'active', Gio.SettingsBindFlags.DEFAULT)

    def update_dropdown(self):
        self.time_format_row.set_selected(self.settings.get_enum('time-format'))

    def update_time_format(self):
        self.settings.set_enum('time-format', self.time_format_row.get_selected())
