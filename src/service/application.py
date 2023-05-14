# application.py
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
import sys

from gi.repository import Gio, GLib
from reminders import info
from reminders.service.backend import Reminders
from os import environ, sep
from gettext import gettext as _

class RemindersService(Gio.Application):
    '''Background service for working with reminders'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.configure_logging()
        try:
            self.sandboxed = False
            self.portal = None

            self.logger.info(f'Starting {info.service_executable} version {info.version}')
            self.settings = Gio.Settings(info.base_app_id)

            if info.portals_enabled:
                from gi import require_version
                require_version('Xdp', '1.0')
                from gi.repository import Xdp

                self.portal = Xdp.Portal()
                self.portal.request_background(
                    None, None,
                    [environ['SERVICE_PATH'] + sep + info.service_executable],
                    Xdp.BackgroundFlags.AUTOSTART,
                    None,
                    None,
                    None
                )
                if self.portal.running_under_sandbox():
                    self.sandboxed = True

            if not self.sandboxed and not info.on_windows:
                # xdg-desktop-portal will try to run the actions on the frontend when the notification is interacted with
                # for this reason, we only need the actions here if we are not sandboxed
                self.create_action('reminder-completed', self.notification_completed_cb, GLib.VariantType.new('s'))
                self.create_action('notification-clicked', self.launch_browser, None)

            self.create_action('quit', self.quit_service, None)

            self.reminders = Reminders(self)
        except Exception as error:
            self.quit()
            self.logger.exception(error)
            raise error

    def do_startup(self):
        Gio.Application.do_startup(self)
        self.reminders.start_countdowns()
        self.hold()

    def do_activate(self):
        Gio.Application.do_activate(self)

    def create_action(self, name, callback, variant = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        self.add_action(action)

    def launch_browser(self, action = None, variant = None):
        self.do_launch_browser()

    def do_launch_browser(self):
        browser = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            info.app_id,
            info.app_object,
            'org.gtk.Actions',
            None
        )

        browser.call_sync(
            'Activate',
            GLib.Variant('(sava{sv})', ('notification-clicked', None, None)),
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )

    def notification_completed_cb(self, action, variant, data = None):
        reminder_id = variant.get_string()
        self.reminders.set_completed(info.service_id, reminder_id, True)

    def configure_logging(self):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(info.service_executable)
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(info.service_log, 'w')
        self.logger.addHandler(handler)
        self.logger.addHandler(file_handler)

    def quit_service(self, action, data):
        self.quit()

def main():
    try:
        app = RemindersService(
            application_id=info.service_id,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        return app.run(sys.argv)
    except Exception as error:
        sys.exit(error)
