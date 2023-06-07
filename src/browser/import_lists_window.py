# import_lists_window.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gi.repository import Gtk, Adw, GLib
from gettext import gettext as _
from retainer import info
from retainer.browser.error_dialog import ErrorDialog
from traceback import format_exception
from logging import getLogger

logger = getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/retainerdevs/Retainer/ui/import_lists_window.ui')
class ImportListsWindow(Gtk.Window):
    __gtype_name__ = 'ImportListsWindow'

    expander = Gtk.Template.Child()
    task_list_row = Gtk.Template.Child()
    main = Gtk.Template.Child()

    def __init__(self, app, files, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.win = app.win
        self.files = files

        self.set_transient_for(self.win)

        self.task_list_row.set_model(self.win.string_list)

        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>s'), Gtk.CallbackAction.new(lambda *args: self.on_save())))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        if info.on_windows:
            self.set_titlebar(None)
            sep = Gtk.Separator()
            sep.add_css_class('titlebar-separator')
            self.main.prepend(sep)

        self.present()

    def do_save(self):
        if self.expander.get_enable_expansion():
            task_list = self.win.task_list_ids[self.task_list_row.get_selected()]
        else:
            task_list = 'auto'

        try:
            self.app.run_service_method('ImportLists', GLib.Variant('(ass)', (self.files, task_list)), show_error_dialog=False)
            self.close()
        except Exception as error:
            error_text = ''.join(format_exception(error))
            logger.exception(error)
            self.app.error_dialog = ErrorDialog(self, _("Couldn't import lists"), _('Check that you are importing a valid iCalendar file.'), error_text, parent_window=self)

    @Gtk.Template.Callback()
    def on_cancel(self, button = None):
        self.close()

    @Gtk.Template.Callback()
    def on_save(self, button = None):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Are you sure you want to import the lists?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.do_save())

        confirm_dialog.present()
