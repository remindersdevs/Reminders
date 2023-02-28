# application.py - Frontend application for Remembrance
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
import logging

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _

from remembrance import info
from remembrance.browser.main_window import MainWindow
from remembrance.browser.about import about_window
from remembrance.browser.preferences import PreferencesWindow

# Always update this when new features are added that require the service to restart
MIN_SERVICE_VERSION = 0.3

class Remembrance(Adw.Application):
    '''Application for the frontend'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.restart = False
        self.sandboxed = False
        self.page = 'all'
        self.unsaved_reminders = []
        self.add_main_option(
            'version', ord('v'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Print the version of the app'),
            None
        )
        self.add_main_option(
            'restart-service', ord('r'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Restart service before starting app'),
            None
        )
        self.add_main_option(
            'page', ord('p'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            _('Start on a different page'),
            '(upcoming|past|completed)',
        )

    def do_command_line(self, command):
        commands = command.get_options_dict()

        if commands.contains('restart-service'):
            self.restart = True

        if commands.contains('version'):
            print(info.version)
            sys.exit(0)

        if commands.contains('page'):
            value = commands.lookup_value('page').get_string()
            if value in ('upcoming', 'past', 'completed'):
                self.page = value
            else:
                print(f'{value} is not a valid page')

        self.do_activate()
        return 0

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.configure_logging()
        if info.portals_enabled:
            import gi
            gi.require_version('Xdp', '1.0')
            from gi.repository import Xdp

            portal = Xdp.Portal()
            if portal.running_under_sandbox():
                self.sandboxed = True

        if self.sandboxed:
            # xdg-desktop-portal will try to run the actions from the backend here when the notification is interacted with
            # for now, we can just add the action here if the app is sandboxed
            # later I will probably make the frontend of the app the owner of the notification to simplify things
            self.create_action('reminder-completed', self.notification_completed_cb, GLib.VariantType.new('s'))
            self.create_action('notification-clicked', self.notification_clicked_cb)

    def check_service_version(self):
        loaded_service_version = self.run_service_method(
            'GetVersion',
            None
        ).unpack()[0]
        if self.restart or loaded_service_version < MIN_SERVICE_VERSION:
            if MIN_SERVICE_VERSION <= info.service_version:
                try:
                    self.run_service_method(
                        'Quit',
                        None
                    )
                    self.connect_to_service()
                except Exception as error:
                    self.logger.error(f"{error}: Couldn't quit {info.service_executable}")
            else:
                self.logger.error(f'{info.service_executable} version is too low')
                sys.exit(1)

    def do_activate(self):
        Adw.Application.do_activate(self)

        if win := self.get_active_window():
            self.win = win
            self.win.activate_action(f'win.{self.page}', None)
            self.win.present()
            return

        self.connect_to_service()
        self.check_service_version()

        self.settings = Gio.Settings(info.base_app_id)
        self.win = MainWindow(self.page, application=self)
        self.service.connect('g-signal::CompletedUpdated', self.reminder_completed_cb)
        self.service.connect('g-signal::ReminderDeleted', self.reminder_deleted_cb)
        self.service.connect('g-signal::ReminderUpdated', self.reminder_updated_cb)
        self.service.connect('g-signal::RepeatUpdated', self.repeat_updated_cb)
        self.win.connect('close-request', self.on_close)
        self.create_action('quit', self.quit_app)
        self.create_action('preferences', self.show_preferences)
        self.create_action('about', self.show_about)
        self.provider = Gtk.CssProvider()
        self.provider.load_from_resource('/io/github/dgsasha/remembrance/stylesheet.css')
        Gtk.StyleContext.add_provider_for_display(self.win.get_display(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win.present()

    def notification_clicked_cb(self, action, variant, data = None):
        self.page = 'past'
        self.do_activate()

    def notification_completed_cb(self, action, variant, data = None):
        reminder_id = variant.get_string()
        self.run_service_method(
            'UpdateCompleted',
            GLib.Variant('(ssb)', (info.app_id, reminder_id, True))
        )
        try:
            self.win.reminder_lookup_dict[reminder_id].set_completed(True)
        except AttributeError:
            pass

    def reminder_completed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder_id, completed = parameters.unpack()
        if app_id != info.app_id:
            self.win.reminder_lookup_dict[reminder_id].set_completed(completed)

    def repeat_updated_cb(self, proxy, sender_name, signal_name, parameters):
        reminder_id, timestamp, old_timestamp, repeat_times = parameters.unpack()
        reminder = self.win.reminder_lookup_dict[reminder_id]
        reminder.update_repeat(timestamp, old_timestamp, repeat_times)

    def reminder_updated_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder = parameters.unpack()
        if app_id != info.app_id:
            try:
                self.win.reminder_lookup_dict[reminder['id']].update(
                    reminder['title'],
                    reminder['description'],
                    reminder['timestamp'],
                    reminder['repeat-type'],
                    reminder['repeat-frequency'],
                    reminder['repeat-days'],
                    reminder['repeat-until'],
                    reminder['repeat-times']
                )
            except KeyError:
                self.win.display_reminder(
                    reminder['id'],
                    reminder['title'],
                    reminder['description'],
                    reminder['timestamp'],
                    reminder['repeat-type'],
                    reminder['repeat-frequency'],
                    reminder['repeat-days'],
                    reminder['repeat-until'],
                    reminder['repeat-times']
                )

    def reminder_deleted_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder_id = parameters.unpack()
        if app_id != info.app_id:
            reminder = self.win.reminder_lookup_dict[reminder_id]
            self.win.reminders_list.remove(reminder)

    def connect_to_service(self):
        self.service = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            info.service_id,
            info.service_object,
            info.service_id,
            None
        )
        if self.service is not None:
            self.logger.info('Connected to service')
        else:
            self.logger.error('Faled to start proxy to connect to service')
            sys.exit(1)

    def run_service_method(self, method, parameters):
        try:
            retval = self.service.call_sync(
                method,
                parameters,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
        except GLib.GError:
            self.connect_to_service()
            retval = self.service.call_sync(
                method,
                parameters,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
        except:
            sys.exit(1)

        return retval

    def on_close(self, window = None):
        if len(self.unsaved_reminders) > 0:
            confirm_dialog = Adw.MessageDialog(
                transient_for=self.win,
                heading=_('You have unsaved changes'),
                body=_('Are you sure you want to close the window?'),
            )
            confirm_dialog.add_response('cancel', _('Cancel'))
            confirm_dialog.add_response('yes', _('Yes'))
            confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
            confirm_dialog.set_default_response('cancel')
            confirm_dialog.set_close_response('cancel')
            confirm_dialog.connect('response::cancel', lambda *args: self.cancel_close())
            confirm_dialog.connect('response::yes', lambda *args: self.win.destroy())
            confirm_dialog.present()
            return True
        else:
            self.win.destroy()

    def cancel_close(self):
        self.win.search_bar.set_search_mode(False)
        for reminder in self.unsaved_reminders:
            reminder.set_expanded(True)
        self.win.selected = self.win.all_row
        self.win.selected.emit('activate')

    def create_action(self, name, callback, variant = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        action.set_enabled(True)

        self.add_action(action)

    def show_about(self, action, data):
        win = about_window()
        win.set_transient_for(self.win)
        win.present()

    def show_preferences(self, action, data):
        win = PreferencesWindow(self)
        win.set_transient_for(self.win)
        win.present()

    def configure_logging(self):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(info.app_name)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def quit_app(self, action, data):
        self.quit()

def main():
    app = Remembrance(application_id=info.app_id, flags = Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
    return app.run(sys.argv)
