# export_lists_window.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _

from retainer import info
from logging import getLogger

if info.on_windows:
    from winsdk.windows.system import Launcher
    from winsdk.windows.foundation import Uri

logger = getLogger(info.app_executable)

class ListRow(Adw.ActionRow):
    def __init__(self, *args, **kwargs):
        super().__init__(activatable = True, *args, **kwargs)
        self.check = Gtk.CheckButton.new()
        self.add_suffix(self.check)
        self.connect('activated', lambda *args: self.check.set_active(not self.check.get_active()))

@Gtk.Template(resource_path='/io/github/retainerdevs/Retainer/ui/export_lists_window.ui')
class ExportListsWindow(Gtk.Window):
    __gtype_name__ = 'ExportListsWindow'

    lists = Gtk.Template.Child()
    main = Gtk.Template.Child()

    def __init__(self, app, folder, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.win = app.win
        self.rows = {}
        self.folder = folder
        self.set_transient_for(self.win)

        for list_id, value in self.win.synced_lists.items():
            list_name = value['name']
            user_id = value['user-id']
            row = ListRow(title=list_name, subtitle=self.win.usernames[user_id])
            self.lists.append(row)
            self.rows[row] = list_id

        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>s'), Gtk.CallbackAction.new(lambda *args: self.on_save())))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        if info.on_windows:
            self.set_titlebar(None)
            sep = Gtk.Separator()
            sep.add_css_class('titlebar-separator')
            self.main.prepend(sep)

        self.present()

    def launch_folder(self, uri):
        if info.on_windows:
            Launcher.launch_uri_async(Uri(uri))
        else:
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
                self.app.run_service_method('ExportLists', GLib.Variant('(sas)', (self.folder.get_path(), lists)))
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
                dialog.connect('response::yes', lambda *args: self.launch_folder(self.folder.get_uri()))

                dialog.present()
            except Exception as error:
                logger.exception(error)
