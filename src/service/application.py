# application.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from gi.repository import Gio, GLib
from retainer import info
from retainer.service.backend import Reminders
from os import environ, sep
from logging import getLogger
from traceback import format_exception

logger = getLogger(info.service_executable)

INTERFACE_XML = f'''
<node>
    <interface name='{info.service_interface}'>
        <method name='GetPrivateAddress'>
            <arg type='s' name='dbus-address' direction='out'/>
        </method>
    </interface>
</node>
'''

class RetainerService(Gio.Application):
    '''Background service for working with reminders'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.sandboxed = False
            self.portal = None

            logger.info(f'Starting {info.service_executable} version {info.version}')
            self.settings = Gio.Settings(info.base_app_id)

            if info.portals_enabled:
                from gi import require_version
                require_version('Xdp', '1.0')
                from gi.repository import Xdp

                self.portal = Xdp.Portal()
                self.portal.request_background(
                    None, None,
                    [environ['INSTALL_DIR'] + sep + 'bin' + sep + info.service_executable],
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

            self.setup_server()

        except Exception as error:
            self.quit()
            logger.exception(error)
            raise error

    def setup_server(self):
        if info.on_windows:
            try:
                from winsdk.windows.storage import ApplicationData
                tmp_dir = ApplicationData.current.temporary_folder.path
            except:
                tmp_dir = GLib.get_tmp_dir()
        else:
            tmp_dir = GLib.get_tmp_dir()

        self.server = Gio.DBusServer.new_sync(
            f'unix:tmpdir={tmp_dir}',
            Gio.DBusServerFlags.NONE if info.on_windows else Gio.DBusServerFlags.AUTHENTICATION_REQUIRE_SAME_USER,
            Gio.dbus_generate_guid(),
            None,
            None
        )
        if self.server is None:
            logger.error(f'Failed to create dbus server')
            sys.exit(1)
        self.server.start()
        self.reminders = Reminders(self)
        logger.info(f'Started private dbus server at {self.server.get_client_address()}')

    def do_dbus_register(self, connection: Gio.DBusConnection, object_path: str) -> bool:
        if Gio.Application.do_dbus_register(self, connection, object_path):
            node_info = Gio.DBusNodeInfo.new_for_xml(INTERFACE_XML)
            connection.register_object(
                info.service_object,
                node_info.interfaces[0],
                self._on_method_call,
                None,
                None
            )
            return True
        return False

    def _on_method_call(self, connection, sender, path, interface, method, parameters, invocation):
        try:
            if method == 'GetPrivateAddress':
                invocation.return_value(GLib.Variant('(s)', (self.server.get_client_address(),)))
        except Exception as error:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed', f'{error} - Method {method} failed to execute\n{"".join(format_exception(error))}')

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

    def quit_service(self, action, data):
        self.quit()

def main():
    try:
        app = RetainerService(
            application_id=info.service_id,
            flags=Gio.ApplicationFlags.IS_SERVICE
        )
        return app.run()
    except Exception as error:
        sys.exit(error)
