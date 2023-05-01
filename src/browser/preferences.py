# preferences.py
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

from gettext import gettext as _

from remembrance import info
from remembrance.browser.caldav_sign_in import CalDAVSignIn
from remembrance.browser.microsoft_sign_in import MicrosoftSignIn

from gi.repository import Gtk, Adw, GLib, Gio, Pango
from logging import getLogger

logger = getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    '''Settings Window'''
    __gtype_name__ = 'PreferencesWindow'
    sound_switch = Gtk.Template.Child()
    sound_theme_switch = Gtk.Template.Child()
    time_format_row = Gtk.Template.Child()
    ms_sync_row = Gtk.Template.Child()
    caldav_sync_row = Gtk.Template.Child()
    ms_add_account = Gtk.Template.Child()
    caldav_add_account = Gtk.Template.Child()
    refresh_button = Gtk.Template.Child()
    refresh_time_row = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    week_switch = Gtk.Template.Child()

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.settings = app.settings
        self.set_transient_for(self.app.win)
        self.settings.bind('week-starts-sunday', self.week_switch, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('notification-sound', self.sound_switch, 'enable-expansion', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('included-notification-sound', self.sound_theme_switch, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.connect('changed::time-format', lambda *args: self.update_time_dropdown())
        self.settings.connect('changed::refresh-frequency', lambda *args: self.update_refresh_dropdown())
        self.settings.connect('changed::synced-lists', lambda *args: self.synced_lists_updated())
        self.update_time_dropdown()
        self.update_refresh_dropdown()
        self.time_format_row.connect('notify::selected', lambda *args: self.update_time_format())
        self.refresh_time_row.connect('notify::selected', lambda *args: self.update_refresh_time())
        self.refresh_button.connect('clicked', lambda *args: self.app.refresh_reminders())
        self.connect('close-request', self.on_close)
        self.synced = self.settings.get_value('synced-lists').unpack()
        self.user_rows = {}

        for user_id, username in self.app.win.ms_users.items():
            self.on_ms_signed_in(user_id, username)
        for user_id, username in self.app.win.caldav_users.items():
            self.on_caldav_signed_in(user_id, username)

        self.synced_lists_updated()
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

    def username_updated(self, user_id, username):
        if user_id in self.user_rows.keys():
            self.user_rows[user_id].set_username(username)

    def synced_lists_updated(self, only_user_id = None):
        self.synced = self.settings.get_value('synced-lists').unpack()

        for user_id, row in self.user_rows.items():
            if only_user_id is not None and user_id != only_user_id:
                continue
            all_synced = user_id in self.synced
            row.all_check.set_active(all_synced)
            for list_id, check in row.task_list_checks.items():
                check.set_active(list_id in self.synced and not all_synced)

    def on_close(self, window, data = None):
        synced = []
        for row in self.user_rows.values():
            if row.task_list_row.get_visible():
                synced += row.get_synced()
        if self.synced != synced:
            self.synced = synced
            try:
                self.app.run_service_method('SetSyncedLists', GLib.Variant('(as)', (self.synced,)), False)
            except Exception as error:
                logger.exception(error)

        self.set_visible(False)
        return True

    def on_ms_signed_in(self, user_id, username):
        lists = {}
        for list_id, value in self.app.win.all_lists.items():
            if value['user-id'] == user_id:
                lists[list_id] = value['name']
        self.user_rows[user_id] = PreferencesUserRow(self, user_id, username, lists)
        self.ms_sync_row.add_row(self.user_rows[user_id])
        self.ms_sync_row.remove(self.ms_add_account)
        self.ms_sync_row.add_row(self.ms_add_account) # move to end

    def on_caldav_signed_in(self, user_id, username):
        lists = {}
        for list_id, value in self.app.win.all_lists.items():
            if value['user-id'] == user_id:
                lists[list_id] = value['name']
        self.user_rows[user_id] = PreferencesUserRow(self, user_id, username, lists, True)
        self.caldav_sync_row.add_row(self.user_rows[user_id])
        self.caldav_sync_row.remove(self.caldav_add_account)
        self.caldav_sync_row.add_row(self.caldav_add_account) # move to end

    def list_updated(self, user_id, list_id, list_name):
        if user_id in self.user_rows.keys():
            self.user_rows[user_id].task_list_updated(list_id, list_name)

    def list_removed(self, user_id, list_id):
        if user_id in self.user_rows.keys():
            self.user_rows[user_id].task_list_deleted(list_id)

    def on_signed_out(self, user_id):
        row = self.user_rows[user_id]
        row.get_parent().remove(row)
        self.user_rows.pop(user_id)

    def update_refresh_dropdown(self):
        self.refresh_time_row.set_selected(self.settings.get_enum('refresh-frequency'))

    def update_refresh_time(self):
        self.settings.set_enum('refresh-frequency', self.refresh_time_row.get_selected())

    def update_time_dropdown(self):
        self.time_format_row.set_selected(self.settings.get_enum('time-format'))

    def update_time_format(self):
        self.settings.set_enum('time-format', self.time_format_row.get_selected())

    def ms_signed_in(self, user_id, username):
        if user_id not in self.user_rows.keys():
            self.on_ms_signed_in(user_id, username)
            self.user_rows[user_id].set_expanded(True)
            self.synced_lists_updated(user_id)

    def caldav_signed_in(self, user_id, username):
        if user_id not in self.user_rows.keys():
            self.on_caldav_signed_in(user_id, username)
            self.user_rows[user_id].set_expanded(True)
            self.synced_lists_updated(user_id)

    @Gtk.Template.Callback()
    def ms_sign_in(self, row = None):
        MicrosoftSignIn(self)

    @Gtk.Template.Callback()
    def caldav_sign_in(self, row = None):
        CalDAVSignIn(self)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/preferences_user_row.ui')
class PreferencesUserRow(Adw.ExpanderRow):
    __gtype_name__ = 'PreferencesUserRow'
    task_list_grid = Gtk.Template.Child()
    all_check = Gtk.Template.Child()
    task_list_row = Gtk.Template.Child()
    username_row = Gtk.Template.Child()
    save_btn = Gtk.Template.Child()

    def __init__(self, preferences, user_id, username, lists, caldav = False, **kwargs):
        super().__init__(**kwargs)
        self.preferences = preferences
        self.user_id = user_id
        self.column = 1
        self.task_lists = {'all': 'All'}
        self.task_list_checks = {}
        self.set_username(username)
        self.lists = lists
        self.set_task_lists()
        if caldav:
            self.username_row.set_visible(True)

    def set_username(self, username):
        self.username = username
        self.set_title(username)
        self.username_row.set_text(username)

    def set_task_lists(self):
        if self.user_id in self.preferences.synced:
            self.all_check.set_active(True)
        else:
            self.all_check.set_active(False)

        for check in self.task_list_checks.values():
            self.task_list_grid.remove(check)
        self.task_list_checks = {}

        self.column = 1
        for list_id, label in self.lists.items():
            self.add_check(list_id, label)

    def task_list_updated(self, list_id, list_name):
        self.lists[list_id] = list_name
        if list_id in self.task_list_checks.keys():
            self.task_list_checks[list_id].set_label(list_name)
        else:
            self.add_check(list_id, list_name)

    def task_list_deleted(self, list_id):
        if list_id in self.lists.keys():
            self.lists.pop(list_id)
        self.set_task_lists()

    def add_check(self, list_id, label):
        if self.column < 4:
            self.column += 1
            pos = Gtk.PositionType.RIGHT
        else:
            self.column = 0
            pos = Gtk.PositionType.BOTTOM

        label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, label=label)
        check = Gtk.CheckButton()
        check.set_child(label)
        check.set_hexpand(True)

        self.task_list_checks[list_id] = check
        self.task_list_grid.attach_next_to(check, None, pos, 1, 1)
        all_checked = self.all_check.get_active()
        check.set_sensitive(not all_checked)
        if not all_checked and list_id in self.preferences.synced:
            check.set_active(True)

    def get_synced(self):
        if self.all_check.get_active():
            synced = [self.user_id]
        else:
            synced = []
            for list_id, check in self.task_list_checks.items():
                if check.get_active():
                    synced.append(list_id)

        return synced

    @Gtk.Template.Callback()
    def save_username(self, button = None):
        username = self.username_row.get_text().strip()
        try:
            self.preferences.app.run_service_method('CalDAVUpdateDisplayName', GLib.Variant('(ss)', (self.user_id, username)))
        except Exception as error:
            logger.exception(error)
        self.set_username(username)
        self.check_saved()

    @Gtk.Template.Callback()
    def check_saved(self, button = None):
        unsaved = self.username_row.get_text() != self.username
        self.save_btn.set_sensitive(unsaved)

    @Gtk.Template.Callback()
    def sign_out(self, button = None):
        try:
            confirm_dialog = Adw.MessageDialog(
                transient_for=self.preferences,
                heading=_('Are you sure you want to sign out?'),
                body=_(f'This will sign out <b>{self.username}</b>'),
                body_use_markup=True
            )
            confirm_dialog.add_response('cancel', _('Cancel'))
            confirm_dialog.add_response('logout', _('Sign Out'))
            confirm_dialog.set_default_response('cancel')
            confirm_dialog.set_response_appearance('logout', Adw.ResponseAppearance.DESTRUCTIVE)
            confirm_dialog.connect('response::logout', lambda *args: self.preferences.app.win.sign_out(self.user_id))
            confirm_dialog.present()
        except Exception as error:
            logger.exception(error)

    @Gtk.Template.Callback()
    def all_lists_selected(self, button = None, data = None):
        checked = self.all_check.get_active()
        for check in self.task_list_checks.values():
            check.set_sensitive(not checked)
