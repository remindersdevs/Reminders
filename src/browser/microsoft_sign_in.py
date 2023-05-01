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

import gi

from remembrance import info

gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Adw, WebKit

from logging import getLogger

logger = getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/microsoft_sign_in.ui')
class MicrosoftSignIn(Adw.Window):
    __gtype_name__ = 'MicrosoftSignIn'

    main = Gtk.Template.Child()

    def __init__(self, preferences, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(preferences)
        self.app = preferences.app
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        self.web = WebKit.WebView()
        self.web.set_vexpand(True)
        url = self.app.run_service_method('MSGetLoginURL', None).unpack()[0]

        self.app.service.connect('g-signal::MSSignedIn', lambda *args: self.destroy())

        self.web.load_uri(url)
        self.main.append(self.web)
        self.present()
