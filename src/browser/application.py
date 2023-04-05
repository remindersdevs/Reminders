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

import sys
import gi
import logging
import traceback

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _

from remembrance import info
from remembrance.browser.error_dialog import ErrorDialog
from remembrance.browser.main_window import MainWindow
from remembrance.browser.about import about_window
from remembrance.browser.preferences import PreferencesWindow

# Always update this when new features are added that require the service to restart
MIN_SERVICE_VERSION = 2.4

class Remembrance(Adw.Application):
    '''Application for the frontend'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.restart = False
        self.sandboxed = False
        self.preferences = None
        self.win = None
        self.page = 'all'
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
        self.provider = Gtk.CssProvider()
        self.provider.load_from_resource('/io/github/dgsasha/remembrance/stylesheet.css')

        if win := self.get_active_window():
            self.win = win
            self.win.activate_action(f'win.{self.page}', None)
            self.win.present()
            return

        self.connect_to_service()
        self.check_service_version()

        self.settings = Gio.Settings(info.base_app_id)
        self.win = MainWindow(self.page, self)
        self.settings.bind('width', self.win, 'default-width', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('height', self.win, 'default-height', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('is-maximized', self.win, 'maximized', Gio.SettingsBindFlags.DEFAULT)
        self.service.connect('g-signal::CompletedUpdated', self.reminder_completed_cb)
        self.service.connect('g-signal::ReminderDeleted', self.reminder_deleted_cb)
        self.service.connect('g-signal::ReminderUpdated', self.reminder_updated_cb)
        self.service.connect('g-signal::RepeatUpdated', self.repeat_updated_cb)
        self.service.connect('g-signal::Refreshed', self.refreshed_cb)
        self.service.connect('g-signal::ListUpdated', self.list_updated_cb)
        self.service.connect('g-signal::ListRemoved', self.list_removed_cb)
        self.create_action('quit', self.quit_app)
        self.create_action('refresh', self.refresh_reminders, accels=['<Ctrl>r'])
        self.create_action('preferences', self.show_preferences, accels=['<control>comma'])
        self.create_action('about', self.show_about)
        Gtk.StyleContext.add_provider_for_display(self.win.get_display(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win.present()

    def notification_clicked_cb(self, action, variant, data = None):
        self.page = 'past'
        self.settings.set_value('selected-task-list', GLib.Variant('(ss)', ('all', 'all')))
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

    def list_updated_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, user_id, list_id, list_name = parameters.unpack()
        self.win.list_updated(user_id, list_id, list_name)
        if self.preferences is not None:
            self.preferences.list_updated(user_id, list_id, list_name)
        if app_id != info.app_id and self.win.edit_lists_window is not None:
            self.win.edit_lists_window.list_updated(user_id, list_id, list_name)

    def list_removed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, user_id, list_id = parameters.unpack()
        self.win.list_removed(user_id, list_id)
        if self.preferences is not None:
            self.preferences.list_removed(user_id, list_id)
        if app_id != info.app_id and self.win.edit_lists_window is not None:
            self.win.edit_lists_window.list_removed(user_id, list_id)

    def reminder_completed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder_id, completed = parameters.unpack()
        if app_id != info.app_id:
            self.win.reminder_lookup_dict[reminder_id].set_completed(completed)

    def repeat_updated_cb(self, proxy, sender_name, signal_name, parameters):
        reminder_id, timestamp, old_timestamp, repeat_times = parameters.unpack()
        reminder = self.win.reminder_lookup_dict[reminder_id]
        reminder.update_repeat(timestamp, old_timestamp, repeat_times)

    def refreshed_cb(self, proxy, sender_name, signal_name, parameters):
        new_reminders, deleted_reminders = parameters.unpack()
        for new_reminder in new_reminders:
            reminder_id = new_reminder['id']
            if reminder_id in self.win.reminder_lookup_dict:
                reminder = self.win.reminder_lookup_dict[reminder_id]
                reminder.update(new_reminder)
                if new_reminder['completed'] != reminder.completed:
                    reminder.set_completed(new_reminder['completed'])
            else:
                self.win.display_reminder(**new_reminder)
        for reminder_id in deleted_reminders:
            self.delete_reminder(reminder_id)

    def reminder_updated_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder = parameters.unpack()
        if app_id != info.app_id:
            reminder_id = reminder['id']
            if reminder_id in self.win.reminder_lookup_dict:
                self.win.reminder_lookup_dict[reminder_id].update(reminder)
            else:
                self.win.display_reminder(**reminder)

    def delete_reminder(self, reminder_id):
        try:
            reminder = self.win.reminder_lookup_dict[reminder_id]

            self.win.reminders_list.remove(reminder)

            self.win.reminder_lookup_dict.pop(reminder_id)
        except:
            pass

    def reminder_deleted_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder_id = parameters.unpack()
        if app_id != info.app_id:
            self.delete_reminder(reminder_id)

    def connect_to_service(self):
        self.service = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            info.service_id,
            info.service_object,
            info.service_interface,
            None
        )
        if self.service is not None:
            self.logger.info('Connected to service')
        else:
            self.logger.error('Faled to start proxy to connect to service')
            sys.exit(1)

    def run_service_method(self, method, parameters, sync = True, callback = None, retry = True):
        try:
            if sync:
                retval = self.service.call_sync(
                    method,
                    parameters,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None
                )
            else:
                retval = self.service.call(
                    method,
                    parameters,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    callback,
                    None
                )
        except GLib.GError as error:
            error_text = ''.join(traceback.format_exception(error))
            if 'The name is not activatable' in str(error):
                error_dialog = ErrorDialog(self, _('Reminders failed to start'), _('You will probably have to log out and log back in before using Reminders, this is due to a bug in Flatpak.'), error_text)
                raise error
            elif 'failed to execute' in str(error) or not retry: # method failed
                error_dialog = ErrorDialog(self, _('Something went wrong'), _('Changes were not saved. This bug should be reported.'), error_text)
                raise error
            elif retry: # service was probably disconnected 
                self.connect_to_service()
                retval = self.run_service_method(method, parameters, sync, callback, False)
        return retval

    def create_action(self, name, callback, variant = None, accels = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        action.set_enabled(True)

        if accels is not None:
            self.set_accels_for_action('app.' + name, accels)

        self.add_action(action)

    def show_about(self, action, data):
        win = about_window()
        win.set_transient_for(self.win)
        win.present()

    def show_preferences(self, action, data):
        if self.preferences is None:
            self.preferences = PreferencesWindow(self)
            self.preferences.present()
        else:
            self.preferences.set_visible(True)

    def configure_logging(self):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(info.app_name)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def refresh_reminders(self, action = None, data = None):
        self.run_service_method('Refresh', None, False, lambda *args: self.win.spinner.stop())
        self.win.spinner.start()

    def quit_app(self, action, data):
        self.quit()

def main():
    try:
        app = Remembrance(application_id=info.app_id, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        return app.run(sys.argv)
    except:
        sys.exit(1)