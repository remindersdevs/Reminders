# caldav_sign_in.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gi import require_version

from retainer import info

require_version('WebKit', '6.0')
from gi.repository import Gtk, Adw, WebKit

from logging import getLogger

logger = getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/retainerdevs/Retainer/ui/microsoft_sign_in.ui')
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

        self.web.load_uri(url)
        self.main.append(self.web)

        self.present()
