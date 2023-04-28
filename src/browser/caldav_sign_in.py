# caldav_sign_in.py
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

import logging

from remembrance import info
from gi.repository import Gtk, Adw, GLib

logger = logging.getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/caldav_sign_in.ui')
class CalDAVSignIn(Adw.Window):
    __gtype_name__ = 'caldav_sign_in'
    name_entry = Gtk.Template.Child()
    url_entry = Gtk.Template.Child()
    username_entry = Gtk.Template.Child()
    password_entry = Gtk.Template.Child()

    def __init__(self, preferences, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(preferences)
        self.app = preferences.app
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        self.present()

    def caldav_sign_in(self, name, url, username, password):
        try:
            self.app.run_service_method('CalDAVLogin', GLib.Variant('(ssss)', (name, url, username, password)), show_error_dialog=False)
        except Exception as error:
            if 'AuthorizationError' in str(error):
                self.password_entry.set_css_classes(['error'])
            if 'Invalid URL' in str(error):
                self.url_entry.set_css_classes(['error'])
            raise error

    @Gtk.Template.Callback()
    def text_changed(self, entry, data = None):
        if entry.has_css_class('error'):
            entry.remove_css_class('error')

    @Gtk.Template.Callback()
    def sign_in(self, button = None):
        name = self.name_entry.get_text().strip()
        url = self.url_entry.get_text().strip()
        username = self.username_entry.get_text().strip()
        password = self.password_entry.get_text().strip()
        if len(name) == 0:
            self.name_entry.set_css_classes(['error'])
            return
        if len(url) == 0:
            self.url_entry.set_css_classes(['error'])
            return
        if len(username) == 0:
            self.username_entry.set_css_classes(['error'])
            return
        if len(password) == 0:
            self.password_entry.set_css_classes(['error'])
            return
        self.caldav_sign_in(name, url, username, password)
        self.close()
