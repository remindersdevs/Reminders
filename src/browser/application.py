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
import logging

from gi import require_version

require_version('Gdk', '4.0')
require_version('Gtk', '4.0')
require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from reminders import info
from reminders.browser.error_dialog import ErrorDialog
from reminders.browser.main_window import MainWindow
from reminders.browser.about import about_window
from reminders.browser.preferences import PreferencesWindow
from reminders.browser.shortcuts_window import ShortcutsWindow
from reminders.browser.export_lists_window import ExportListsWindow
from reminders.browser.import_lists_window import ImportListsWindow
from gettext import gettext as _
from pkg_resources import parse_version
from traceback import format_exception
from os import environ, sep, path

if info.on_windows:
    from time import sleep
    from subprocess import Popen, CREATE_NEW_CONSOLE

    import ctypes

    user32 = ctypes.windll.user32
    GetWindowRect = user32.GetWindowRect
    SetWindowPos = user32.SetWindowPos
    OffsetRect = user32.OffsetRect
    CopyRect = user32.CopyRect
    gdk_win32_surface_get_handle = ctypes.WinDLL('libgtk-4-1.dll').gdk_win32_surface_get_handle

# Always update this when new features are added that require the service to restart
MIN_SERVICE_VERSION = '5.0'

class Reminders(Adw.Application):
    '''Application for the frontend'''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.configure_logging()
        self.sandboxed = False
        self.preferences = None
        self.win = None
        self.error_dialog = None
        self.spinning_cursor = Gdk.Cursor.new_from_name('wait')
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
            GLib.OPTION_REMAINING,
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING_ARRAY,
            'URI',
            None
        )

    def do_command_line(self, command):
        commands = command.get_options_dict()
        no_activate = False
        action = None
        param = None

        if commands.contains('version'):
            print(info.version)
            sys.exit(0)

        self.restart = commands.contains('restart-service')

        files = commands.lookup_value(GLib.OPTION_REMAINING)
        imports = []
        if files:
            for file in files:
                # handling for windows URL protocol activation
                prefix = f'{info.app_id}:'
                if file.startswith(prefix):
                    args = file[len(prefix):]
                    args = args.split(';')
                    for arg in args:
                        if arg == 'no-activate':
                            no_activate = True
                        elif '=' in arg:
                            arg = arg.split('=', 1)
                            if arg[0] == 'action':
                                action = arg[1]
                            if arg[0] == 'param':
                                param = GLib.Variant('s', arg[1])
                    self.do_activate
                elif path.exists(file):
                    imports.append(file)

        if not no_activate:
            self.do_activate()

        if action is not None:
            self.activate_action(action, param)

        if len(imports) > 0:
            self.open_files(imports)

        return 0

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.refreshing = False

        if info.portals_enabled:
            require_version('Xdp', '1.0')
            from gi.repository import Xdp

            portal = Xdp.Portal()
            if portal.running_under_sandbox():
                self.sandboxed = True

        if self.sandboxed or info.on_windows:
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

        loaded_ver = parse_version(str(loaded_service_version))
        min_ver = parse_version(str(MIN_SERVICE_VERSION))
        installed_ver = parse_version(str(info.version))

        if self.restart or loaded_ver < min_ver:
            if min_ver <= installed_ver:
                try:
                    self.run_service_method(
                        'Quit',
                        None
                    )
                    self.connect_to_service()
                except Exception as error:
                    self.logger.exception(f"{error}: Couldn't quit {info.service_executable}")
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

        self.provider = Gtk.CssProvider()
        self.provider.load_from_resource('/io/github/remindersdevs/Reminders/stylesheet.css')

        self.connect_to_service()
        self.check_service_version()

        self.settings = Gio.Settings(info.base_app_id)
        self.win = MainWindow(self.page, self)
        self.settings.bind('width', self.win, 'default-width', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('height', self.win, 'default-height', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('is-maximized', self.win, 'maximized', Gio.SettingsBindFlags.DEFAULT)
        self.service.connect('g-signal::Error', self.error_cb)
        self.service.connect('g-signal::CompletedUpdated', self.reminder_completed_cb)
        self.service.connect('g-signal::RemindersCompleted', self.reminders_completed_cb)
        self.service.connect('g-signal::ReminderRemoved', self.reminder_deleted_cb)
        self.service.connect('g-signal::ReminderUpdated', self.reminder_updated_cb)
        self.service.connect('g-signal::ReminderShown', self.reminder_shown_cb)
        self.service.connect('g-signal::RemindersUpdated', self.reminders_updated_cb)
        self.service.connect('g-signal::RemindersRemoved', self.reminders_removed_cb)
        self.service.connect('g-signal::ListUpdated', self.list_updated_cb)
        self.service.connect('g-signal::ListRemoved', self.list_removed_cb)
        self.create_action('quit', self.quit_app, accels=['<Ctrl>q'])
        self.create_action('refresh', self.refresh_reminders, accels=['<Ctrl>r'])
        self.create_action('preferences', self.show_preferences, accels=['<control>comma'])
        self.create_action('shortcuts', self.show_shortcuts, accels=['<control>question'])
        self.create_action('export', self.export, accels=['<Ctrl>e'])
        self.create_action('import', self.import_lists, accels=['<Ctrl>i'])
        self.create_action('about', self.show_about)
        Gtk.StyleContext.add_provider_for_display(self.win.get_display(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win.present()

    def error_cb(self, proxy, sender_name, signal_name, parameters):
        error = parameters.unpack()[0]
        if self.error_dialog is not None:
            self.error_dialog.destroy()
            self.error_dialog = None
        self.error_dialog = ErrorDialog(self, _('Something went wrong'), _('Changes were not saved. This bug should be reported.'), error)
        self.refresh_reminders()

    def notification_clicked_cb(self, action, variant, data = None):
        self.page = 'past'
        self.settings.set_string('selected-list', 'all')
        self.do_activate()

    def notification_completed_cb(self, action, variant, data = None):
        reminder_id = variant.get_string()
        results = self.run_service_method(
            'UpdateCompleted',
            GLib.Variant('(ssb)', (info.app_id, reminder_id, True))
        )
        timestamp, completed_date = results.unpack()
        try:
            reminder = self.win.reminder_lookup_dict[reminder_id]
            reminder.options['updated-timestamp'] = timestamp
            reminder.options['completed-date'] = completed_date
            reminder.set_completed(True)
            self.win.selected_changed()
            self.win.invalidate_filter()
            self.win.reminders_list.invalidate_sort()
        except AttributeError:
            pass

    def list_updated_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, task_list = parameters.unpack()
        list_id = task_list['id']
        list_name = task_list['name']
        user_id = task_list['user-id']
        self.win.list_updated(user_id, list_id, list_name)
        if self.preferences is not None:
            self.preferences.list_updated(user_id, list_id, list_name)
        if app_id != info.app_id and self.win.edit_lists_window is not None:
            self.win.edit_lists_window.list_updated(user_id, list_id, list_name)

    def list_removed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, list_id = parameters.unpack()
        user_id = self.win.all_lists[list_id]['user-id']
        self.win.list_removed(list_id)
        if self.preferences is not None:
            self.preferences.list_removed(user_id, list_id)
        if app_id != info.app_id and self.win.edit_lists_window is not None:
            self.win.edit_lists_window.list_removed(user_id, list_id)

    def reminder_completed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder_id, completed, updated_timestamp, completed_date = parameters.unpack()
        if app_id != info.app_id:
            reminder = self.win.reminder_lookup_dict[reminder_id]
            reminder.options['updated-timestamp'] = updated_timestamp
            reminder.options['completed-date'] = completed_date
            reminder.set_completed(completed)
            self.win.selected_changed()
            self.win.invalidate_filter()
            self.win.reminders_list.invalidate_sort()

    def reminders_completed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder_ids, completed, updated_timestamp, completed_date = parameters.unpack()
        if app_id != info.app_id:
            for reminder_id in reminder_ids:
                reminder = self.win.reminder_lookup_dict[reminder_id]
                reminder.options['updated-timestamp'] = updated_timestamp
                reminder.options['completed-date'] = completed_date
                reminder.set_completed(completed)
            self.win.selected_changed()
            self.win.invalidate_filter()
            self.win.reminders_list.invalidate_sort()

    def reminder_shown_cb(self, proxy, sender_name, signal_name, parameters):
        reminder_id = parameters.unpack()[0]
        reminder = self.win.reminder_lookup_dict[reminder_id]
        reminder.refresh_time()

    def reminders_updated_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, new_reminders = parameters.unpack()
        if app_id != info.app_id:
            for new_reminder in new_reminders:
                reminder_id = new_reminder['id']
                if reminder_id in self.win.reminder_lookup_dict:
                    reminder = self.win.reminder_lookup_dict[reminder_id]
                    reminder.update(new_reminder)
                    if new_reminder['completed'] != reminder.completed:
                        reminder.set_completed(new_reminder['completed'])
                else:
                    self.win.display_reminder(**new_reminder)

            self.win.selected_changed()
            self.win.invalidate_filter()
            self.win.reminders_list.invalidate_sort()

    def reminders_removed_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, deleted_reminders = parameters.unpack()
        if app_id != info.app_id:
            for reminder_id in deleted_reminders:
                self.delete_reminder(reminder_id)

            self.win.invalidate_filter()

    def reminder_updated_cb(self, proxy, sender_name, signal_name, parameters):
        app_id, reminder = parameters.unpack()
        if app_id != info.app_id:
            reminder_id = reminder['id']
            if reminder_id in self.win.reminder_lookup_dict:
                self.win.reminder_lookup_dict[reminder_id].update(reminder)
            else:
                self.win.display_reminder(**reminder)

        self.win.selected_changed()
        self.win.invalidate_filter()
        self.win.reminders_list.invalidate_sort()

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
            self.win.invalidate_filter()

    def connect_to_service(self):
        if info.on_windows:
            # Can't autostart dbus services on windows
            if info.service_executable.endswith('exe'):
                Popen([environ['REMINDERS_PATH'] + sep + info.service_executable], creationflags=CREATE_NEW_CONSOLE)
            else:
                Popen([sys.executable, environ['REMINDERS_PATH'] + sep + info.service_executable], creationflags=CREATE_NEW_CONSOLE)
            self.found = False
            def cb():
                self.found = True
            timeout = GLib.timeout_add_seconds(10, self.timeout_error)
            context = GLib.MainContext.new()
            context.push_thread_default()
            watcher_id = self.watch(cb)
            while not self.found:
                sleep(0.5)
                context.iteration(True)
            context.pop_thread_default()
            GLib.source_remove(timeout)
            self.do_connect(watcher_id)
        else:
            self.do_connect()

    def timeout_error(self):
        self.logger.error('Failed to connect to service')
        sys.exit(1)

    def watch(self, cb):
        watcher_id = Gio.bus_watch_name(
            Gio.BusType.SESSION,
            info.service_id,
            Gio.BusNameWatcherFlags.NONE,
            lambda *args: cb(),
            None
        )
        return watcher_id

    def do_connect(self, watcher_id = None):
        if watcher_id is not None:
            Gio.bus_unwatch_name(watcher_id)
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
            self.logger.error('Failed to start proxy to connect to service')
            sys.exit(1)

    def run_service_method(self, method, parameters, sync = True, callback = None, retry = True, show_error_dialog = True):
        self.mark_busy()
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
            error_text = ''.join(format_exception(error))
            if 'The name is not activatable' in str(error):
                if show_error_dialog:
                    if self.error_dialog is not None:
                        self.error_dialog.destroy()
                        self.error_dialog = None
                    self.error_dialog = ErrorDialog(self, _('Reminders failed to start'), _('If this is your first time running Reminders, you will probably have to log out and log back in before using it. This is due to a bug in Flatpak.'), error_text)
                self.unmark_busy()
                raise error
            elif 'failed to execute' in str(error) or not retry: # method failed
                if show_error_dialog:
                    if self.error_dialog is not None:
                        self.error_dialog.destroy()
                        self.error_dialog = None
                    self.error_dialog = ErrorDialog(self, _('Something went wrong'), _('Changes were not saved. This bug should be reported.'), error_text)
                self.unmark_busy()
                raise error
            elif retry: # service was probably disconnected
                self.connect_to_service()
                retval = self.run_service_method(method, parameters, sync, callback, False)
        self.unmark_busy()
        return retval

    def create_action(self, name, callback, variant = None, accels = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        action.set_enabled(True)

        if accels is not None:
            self.set_accels_for_action('app.' + name, accels)

        self.add_action(action)

    def show_about(self, action, data):
        about_window(self.win)

    def show_shortcuts(self, action, data):
        ShortcutsWindow(self.win)

    def export(self, action, data):
        dialog = Gtk.FileDialog.new()

        dialog.select_folder(self.win, None, self.export_cb)

    def export_cb(self, dialog, result, data = None):
        try:
            folder = dialog.select_folder_finish(result)
        except:
            return

        ExportListsWindow(self, folder)

    def import_lists(self, action, data):
        dialog = Gtk.FileDialog.new()
        filters = Gio.ListStore.new(Gtk.FileFilter)
        file_filter = Gtk.FileFilter.new()
        if info.on_windows:
            file_filter.add_pattern('*.ics')
            file_filter.add_pattern('*.ical')
        else:
            file_filter.add_mime_type('text/calendar')
        filters.append(file_filter)
        dialog.set_filters(filters)
        dialog.open_multiple(self.win, None, self.open_cb)

    def open_cb(self, dialog, result, data = None):
        try:
            result = dialog.open_multiple_finish(result)
        except:
            return
        files = []
        for file in result:
            files.append(file.get_path())

        ImportListsWindow(self, files)

    def open_files(self, files):
        ImportListsWindow(self, files)

    def center_win_on_parent(self, window, data=None):
        ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
        ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
        pointer = ctypes.pythonapi.PyCapsule_GetPointer(window.get_native().get_surface().__gpointer__, None)
        parent_pointer = ctypes.pythonapi.PyCapsule_GetPointer(window.get_transient_for().get_native().get_surface().__gpointer__, None)
        gdk_win32_surface_get_handle.argtypes = [ctypes.c_void_p]
        window_handle = gdk_win32_surface_get_handle(pointer)
        parent_window_handle = gdk_win32_surface_get_handle(parent_pointer)

        RECT = (ctypes.c_long * 4)
        parent_rect = RECT()
        GetWindowRect(parent_window_handle, ctypes.byref(parent_rect))

        window_rect = RECT()
        GetWindowRect(window_handle, ctypes.byref(window_rect))

        parent_rect_copy = RECT()
        CopyRect(ctypes.byref(parent_rect_copy), ctypes.byref(parent_rect))

        OffsetRect(ctypes.byref(window_rect), ctypes.c_int(window_rect[0] * -1), ctypes.c_int(window_rect[1] * -1))
        OffsetRect(ctypes.byref(parent_rect_copy), ctypes.c_int(parent_rect_copy[0] * -1), ctypes.c_int(parent_rect_copy[1] * -1))
        OffsetRect(ctypes.byref(parent_rect_copy), ctypes.c_int(window_rect[2] * -1), ctypes.c_int(window_rect[3] * -1))

        new_x = parent_rect[0] + (parent_rect_copy[2] // 2)
        new_y = parent_rect[1] + (parent_rect_copy[3] // 2)

        SetWindowPos(window_handle, 0, ctypes.c_int(new_x), ctypes.c_int(new_y), 0, 0, 0x0001 | 0x0004)  # SWP_NOSIZE | SWP_NOZORDER

    def show_preferences(self, action, data):
        if self.preferences is None:
            self.preferences = PreferencesWindow(self)
            self.preferences.present()
            if info.on_windows:
                self.center_win_on_parent(self.preferences)
        else:
            self.preferences.set_visible(True)

    def configure_logging(self):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(info.app_executable)
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(info.app_log, 'w')
        self.logger.addHandler(handler)
        self.logger.addHandler(file_handler)

    def refresh_reminders(self, action = None, data = None):
        if not self.refreshing:
            self.start_spinners()
            self.run_service_method('Refresh', None, False, lambda *args: self.stop_spinners())

    def stop_spinners(self):
        self.win.spinner.stop()
        if self.preferences is not None:
            self.preferences.spinner.stop()
        self.refreshing = False

    def start_spinners(self):
        self.refreshing = True
        self.win.spinner.start()
        if self.preferences is not None:
            self.preferences.spinner.start()

    def quit_app(self, action, data):
        self.quit()

def main():
    try:
        app = Reminders(application_id=info.app_id, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        return app.run(sys.argv)
    except:
        sys.exit(1)
