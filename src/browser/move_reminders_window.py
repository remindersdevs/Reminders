# move_reminders_window.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gi.repository import Gtk, Adw, GLib

from retainer import info
from gettext import gettext as _
from logging import getLogger

logger = getLogger(info.app_executable)

@Gtk.Template(resource_path='/io/github/retainerdevs/Retainer/ui/move_reminders_window.ui')
class MoveRemindersWindow(Gtk.Window):
    __gtype_name__ = 'MoveRemindersWindow'

    lists = Gtk.Template.Child()
    main = Gtk.Template.Child()

    def __init__(self, win, reminders, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_transient_for(win)
        self.reminders = reminders
        self.win = win
        self.rows = {}
        selected = reminders[0].options['list-id']
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>s'), Gtk.CallbackAction.new(lambda *args: self.on_save())))
        self.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: self.close())))

        for list_id, value in self.win.synced_lists.items():
            list_name = value['name']
            user_id = value['user-id']
            row = Adw.ActionRow(title=list_name, subtitle=self.win.usernames[user_id], activatable=False)
            self.lists.append(row)
            self.rows[row] = list_id
            if list_id == selected:
                self.lists.select_row(row)

        if info.on_windows:
            self.set_titlebar(None)
            sep = Gtk.Separator()
            sep.add_css_class('titlebar-separator')
            self.main.prepend(sep)

        self.present()

    def do_save(self):
        try:
            selected = self.lists.get_selected_rows()[0]
            variants = []
            options = {}
            for reminder in self.reminders:
                options[reminder.id] = reminder.options.copy()
                opts = options[reminder.id]
                opts['list-id'] = self.rows[selected]
                if reminder.get_sensitive() and reminder.options['list-id'] != opts['list-id']:
                    if self.win.synced_lists[opts['list-id']]['user-id'] in self.win.ms_users.keys():
                        if opts['repeat-type'] in (1, 2):
                            opts['repeat-type'] = 0
                            opts['repeat-frequency'] = 1
                            opts['repeat-days'] = 0
                        opts['repeat-until'] = 0
                        opts['repeat-times'] = -1

                    variants.append({
                        'id': GLib.Variant('s', reminder.id),
                        'repeat-type': GLib.Variant('q', opts['repeat-type']),
                        'repeat-frequency': GLib.Variant('q', opts['repeat-frequency']),
                        'repeat-days': GLib.Variant('q', opts['repeat-days']),
                        'repeat-times': GLib.Variant('n', opts['repeat-times']),
                        'repeat-until': GLib.Variant('t', opts['repeat-until']),
                        'list-id': GLib.Variant('s', opts['list-id'])
                    })
                results = self.win.app.run_service_method(
                    'UpdateReminderv',
                    GLib.Variant(
                        '(saa{sv})',
                        (
                            info.app_id,
                            variants
                        )
                    )
                )
            updated_reminder_ids, timestamp = results.unpack()
            for reminder_id in updated_reminder_ids:
                reminder = self.win.reminder_lookup_dict[reminder_id]
                options[reminder_id]['updated-timestamp'] = timestamp
                reminder.options.update(options[reminder_id])
                reminder.set_repeat_label()
            self.close()
        except Exception as error:
            logger.exception(error)

        self.win.invalidate_filter()
        self.win.reminders_list.invalidate_sort()

    @Gtk.Template.Callback()
    def on_cancel(self, button = None):
        self.close()

    @Gtk.Template.Callback()
    def on_save(self, button = None):
        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_('Are you sure you want to move the currently selected reminder(s)?')
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('yes', _('Yes'))
        confirm_dialog.set_response_appearance('yes', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_close_response('cancel')
        confirm_dialog.connect('response::yes', lambda *args: self.do_save())

        confirm_dialog.present()
