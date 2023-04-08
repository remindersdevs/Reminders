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

from gi.repository import Gtk, Adw, GLib, Gio, Pango

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    '''Settings Window'''
    __gtype_name__ = 'PreferencesWindow'
    sound_switch = Gtk.Template.Child()
    sound_theme_switch = Gtk.Template.Child()
    time_format_row = Gtk.Template.Child()
    ms_sync_row = Gtk.Template.Child()
    add_account_row = Gtk.Template.Child()
    refresh_button = Gtk.Template.Child()
    refresh_time_row = Gtk.Template.Child()
    spinner = Gtk.Template.Child()

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.settings = app.settings
        self.set_transient_for(self.app.win)
        self.settings.bind('notification-sound', self.sound_switch, 'enable-expansion', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('included-notification-sound', self.sound_theme_switch, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.connect('changed::time-format', lambda *args: self.update_time_dropdown())
        self.settings.connect('changed::refresh-frequency', lambda *args: self.update_refresh_dropdown())
        self.settings.connect('changed::synced-task-lists', lambda *args: self.synced_lists_updated())
        self.update_time_dropdown()
        self.update_refresh_dropdown()
        self.time_format_row.connect('notify::selected', lambda *args: self.update_time_format())
        self.refresh_time_row.connect('notify::selected', lambda *args: self.update_refresh_time())
        self.app.service.connect('g-signal::MSSignedIn', self.signed_in_cb)
        self.app.service.connect('g-signal::MSSignedOut', self.signed_out_cb)
        self.refresh_button.connect('clicked', lambda *args: self.app.refresh_reminders())
        self.connect('close-request', self.on_close)
        self.synced = self.settings.get_value('synced-task-lists').unpack()
        self.user_rows = {}

        for user_id, email in self.app.win.emails.items():
            self.on_signed_in(user_id, email)
        self.synced_lists_updated()

    def synced_lists_updated(self, only_user_id = None):
        self.synced = self.settings.get_value('synced-task-lists').unpack()

        for user_id in self.synced.keys():
            if only_user_id is not None and user_id != only_user_id:
                continue
            if user_id not in self.user_rows:
                continue
            row = self.user_rows[user_id]
            if 'all' in self.synced[user_id]:
                row.all_check.set_active(True)
                return
            else:
                row.all_check.set_active(False)

            for list_id, check in row.task_list_checks.items():
                check.set_active(list_id in self.synced[user_id])

    def on_close(self, window, data = None):
        synced = {}
        for user_id, row in self.user_rows.items():
            if row.task_list_row.get_visible():
                row.update_synced()
                synced[user_id] = row.synced
        if self.synced != synced:
            self.synced = synced
            self.settings.set_value('synced-task-lists', GLib.Variant('a{sas}', self.synced))
        self.set_visible(False)
        return True

    def on_signed_in(self, user_id, email):
        names = self.app.win.all_task_list_names[user_id] if user_id in self.app.win.all_task_list_names else {}
        self.user_rows[user_id] = MSUserRow(self, user_id, email, names)
        self.ms_sync_row.add_row(self.user_rows[user_id])
        self.ms_sync_row.remove(self.add_account_row)
        self.ms_sync_row.add_row(self.add_account_row) # move to end

    def list_updated(self, user_id, list_id, list_name):
        if user_id in self.user_rows.keys():
            self.user_rows[user_id].task_list_updated(list_id, list_name)

    def list_removed(self, user_id, list_id):
        if user_id in self.user_rows.keys():
            self.user_rows[user_id].task_list_deleted(list_id)

    def on_signed_out(self, user_id):
        self.ms_sync_row.remove(self.user_rows[user_id])
        self.user_rows.pop(user_id)

    def update_refresh_dropdown(self):
        self.refresh_time_row.set_selected(self.settings.get_enum('refresh-frequency'))

    def update_refresh_time(self):
        self.settings.set_enum('refresh-frequency', self.refresh_time_row.get_selected())

    def update_time_dropdown(self):
        self.time_format_row.set_selected(self.settings.get_enum('time-format'))

    def update_time_format(self):
        self.settings.set_enum('time-format', self.time_format_row.get_selected())

    def signed_out_cb(self, proxy, sender_name, signal_name, parameters):
        user_id = parameters.unpack()[0]
        self.on_signed_out(user_id)

    def signed_in_cb(self, proxy, sender_name, signal_name, parameters):
        user_id, email = parameters.unpack()
        if user_id not in self.user_rows.keys():
            self.on_signed_in(user_id, email)
            self.user_rows[user_id].set_expanded(True)
            self.synced_lists_updated(user_id)

    @Gtk.Template.Callback()
    def sign_in(self, row = None):
        try:
            self.app.win.sign_in()
        except Exception as error:
            self.app.logger.error(error)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/ms_user_row.ui')
class MSUserRow(Adw.ExpanderRow):
    __gtype_name__ = 'user_row'
    task_list_grid = Gtk.Template.Child()
    all_check = Gtk.Template.Child()
    task_list_row = Gtk.Template.Child()

    def __init__(self, preferences, user_id, email, lists, **kwargs):
        super().__init__(**kwargs)
        self.preferences = preferences
        self.user_id = user_id
        self.column = 1
        self.task_lists = {'all': 'All'}
        self.task_list_checks = {}
        self.set_email(email)
        self.lists = lists
        self.synced = self.preferences.synced[self.user_id] if self.user_id in self.preferences.synced else []
        self.set_task_lists()

    def set_email(self, email):
        self.email = email
        self.set_title(email)

    def set_task_lists(self):
        if 'all' in self.synced:
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
            self.lists.pop[list_id]
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
        if list_id in self.synced:
            check.set_active(True)
        self.task_list_checks[list_id] = check
        self.task_list_grid.attach_next_to(check, None, pos, 1, 1)
        all_checked = self.all_check.get_active()
        check.set_sensitive(not all_checked)

    def update_synced(self):
        if self.all_check.get_active():
            self.synced = ['all']
        else:
            self.synced = []
            for list_id, check in self.task_list_checks.items():
                if check.get_active():
                    self.synced.append(list_id)

    @Gtk.Template.Callback()
    def sign_out(self, button = None):
        try:
            confirm_dialog = Adw.MessageDialog(
                transient_for=self.preferences,
                heading=_('Are you sure you want to sign out?'),
                body=_(f'This will sign out <b>{self.email}</b>'),
                body_use_markup=True
            )
            confirm_dialog.add_response('cancel', _('Cancel'))
            confirm_dialog.add_response('logout', _('Sign Out'))
            confirm_dialog.set_default_response('cancel')
            confirm_dialog.set_response_appearance('logout', Adw.ResponseAppearance.DESTRUCTIVE)
            confirm_dialog.connect('response::logout', lambda *args: self.preferences.app.win.sign_out(self.user_id))
            confirm_dialog.present()
        except Exception as error:
            self.preferences.app.logger.error(error)

    @Gtk.Template.Callback()
    def all_lists_selected(self, button = None, data = None):
        checked = self.all_check.get_active()
        for check in self.task_list_checks.values():
            check.set_sensitive(not checked)
