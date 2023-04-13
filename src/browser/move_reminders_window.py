# move_reminders_window.py
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

from gi.repository import Gtk, Adw, GLib
from gettext import gettext as _

from remembrance import info

logger = logging.getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/move_reminders_window.ui')
class MoveRemindersWindow(Adw.Window):
    __gtype_name__ = 'move_reminders_window'

    lists = Gtk.Template.Child()

    def __init__(self, win, reminders, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_transient_for(win)
        self.reminders = reminders
        self.win = win
        self.rows = {}
        selected = (reminders[0].options['user-id'], reminders[0].options['list-id'])
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>s'), Gtk.CallbackAction.new(lambda *args: self.on_save())))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        for user_id, value in self.win.task_list_names.items():
            if user_id in self.win.emails.keys() or user_id == 'local':
                for list_id, list_name in value.items():
                    row = Adw.ActionRow(title=list_name, subtitle=_('Local') if user_id == 'local' else self.win.emails[user_id], activatable=False)
                    self.lists.append(row)
                    self.rows[row] = (user_id, list_id)
                    if user_id == selected[0] and list_id == selected[1]:
                        self.lists.select_row(row)

        self.present()

    def do_save(self):
        try:
            selected = self.lists.get_selected_rows()[0]
            options = {}
            options['user-id'], options['list-id'] = self.rows[selected]
            for reminder in self.reminders:
                if reminder.get_sensitive() and reminder.options['list-id'] != options['list-id'] or reminder.options['user-id'] != options['user-id']:
                    results = self.win.app.run_service_method(
                        'UpdateReminder',
                        GLib.Variant(
                            '(sa{sv})',
                            (
                                info.app_id,
                                {
                                    'id': GLib.Variant('s', reminder.id),
                                    'list-id': GLib.Variant('s', options['list-id']),
                                    'user-id': GLib.Variant('s', options['user-id'])
                                }
                            )
                        )
                    )
                    options['updated-timestamp'] = results.unpack()[0]
                    reminder.options.update(options)
                    reminder.changed()
            self.win.reminders_list.invalidate_sort()
            self.close()
        except Exception as error:
            logger.error(error)

    @Gtk.Template.Callback()
    def on_cancel(self, button = None):
        self.close()

    @Gtk.Template.Callback()
    def on_save(self, button = None):

        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Are you sure you want to move the selected reminders?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.do_save())
        confirm_dialog.present()