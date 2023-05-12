# export_lists_window.py
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

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _

from reminders import info
from logging import getLogger

logger = getLogger(info.app_executable)

class ListRow(Adw.ActionRow):
    def __init__(self, *args, **kwargs):
        super().__init__(activatable = True, *args, **kwargs)
        self.check = Gtk.CheckButton.new()
        self.add_suffix(self.check)
        self.connect('activated', lambda *args: self.check.set_active(not self.check.get_active()))

@Gtk.Template(resource_path='/io/github/remindersdevs/Reminders/ui/export_lists_window.ui')
class ExportListsWindow(Adw.Window):
    __gtype_name__ = 'ExportListsWindow'

    lists = Gtk.Template.Child()

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.win = app.win
        self.rows = {}
        self.set_transient_for(self.win)

        for list_id, value in self.win.synced_lists.items():
            list_name = value['name']
            user_id = value['user-id']
            row = ListRow(title=list_name, subtitle=self.win.usernames[user_id])
            self.lists.append(row)
            self.rows[row] = list_id

        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>s'), Gtk.CallbackAction.new(lambda *args: self.on_save())))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        self.present()

        if info.on_windows:
            self.app.center_win_on_parent(self)

    def launch_folder(self, uri):
        Gio.AppInfo.launch_default_for_uri(uri, None)
        self.close()

    @Gtk.Template.Callback()
    def on_cancel(self, button = None):
        self.close()

    @Gtk.Template.Callback()
    def on_save(self, button = None):
        lists = []
        for row, list_id in self.rows.items():
            if row.check.get_active():
                lists.append(list_id)

        if len(lists) > 0:
            try:
                result = self.app.run_service_method('ExportLists', GLib.Variant('(as)', (lists,)))
                folder = result.unpack()[0]
                uri = GLib.filename_to_uri(folder, None)
                dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading=_('Success!'),
                    body=_('Do you want to open the folder?')
                )
                dialog.add_response('close', _('Close'))
                dialog.add_response('yes', _('Yes'))
                dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
                dialog.set_default_response('cancel')
                dialog.set_close_response('cancel')
                dialog.connect('response::close', lambda *args: self.close())
                dialog.connect('response::yes', lambda *args: self.launch_folder(uri))

                dialog.present()

                if info.on_windows:
                    self.app.center_win_on_parent(dialog)
            except Exception as error:
                logger.exception(error)
