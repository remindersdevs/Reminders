# reminder.py
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

import time
import datetime

from gi.repository import Gtk, Adw, GLib
from gettext import gettext as _
from math import floor

from remembrance import info

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/reminder.ui')
class Reminder(Adw.ExpanderRow):
    '''Ui for each reminder'''
    __gtype_name__ = 'reminder'

    completed_icon = Gtk.Template.Child()
    separator = Gtk.Template.Child()
    past_due_icon = Gtk.Template.Child()
    label_box = Gtk.Template.Child()
    time_label = Gtk.Template.Child()
    repeat_label = Gtk.Template.Child()
    remove_button = Gtk.Template.Child()
    done_button = Gtk.Template.Child()
    edit_button = Gtk.Template.Child()
    done_btn_content = Gtk.Template.Child()

    def __init__(
        self,
        win,
        options,
        reminder_id = None,
        completed = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.win = win
        self.app = win.app
        self.id = reminder_id
        self.options = options
        self.set_title(options['title'])
        self.set_subtitle(options['description'])
        self.past = False

        self.completed_icon_box = self.completed_icon.get_parent().get_parent()
        self.set_completed(completed)

        actions_box = self.label_box.get_parent()
        suffixes_box = actions_box.get_parent()
        actions_box.set_hexpand(True)
        actions_box.set_vexpand(False)
        suffixes_box.set_vexpand(True)
        actions_box.set_valign(Gtk.Align.FILL)
        actions_box.set_halign(Gtk.Align.END)
        self.set_labels()

        self.refresh_time()

        self.win.connect('notify::time-format', lambda *args: self.set_time_label())

    def set_past(self, past):
        if self.past != past:
            self.past = past
            self.set_time_label()
            self.refresh_time()

    def set_timestamp(self, timestamp, old_timestamp = None):
        if old_timestamp is not None and old_timestamp != self.options['old-timestamp']:
            self.options['old-timestamp'] = old_timestamp
        if timestamp != self.options['timestamp']:
            self.options['timestamp'] = timestamp
        self.set_time_label()
        self.refresh_time()
        self.changed()

    def update(self, options):
        edit_win = self.win.reminder_edit_win
        if edit_win is not None and edit_win.id == self.id:
            if self.options['title'] != options['title']:
                edit_win.title_entry.set_text(options['title'])

            if self.options['description'] != options['description']:
                edit_win.description_entry.set_text(options['description'])

            if self.options['timestamp'] != options['timestamp']:
                edit_win.set_time(options['timestamp'])

            if self.options['repeat-type'] != options['repeat-type']:
                edit_win.set_repeat_type(options['repeat-type'])

            if self.options['repeat-frequency'] != options['repeat-frequency']:
                edit_win.set_repeat_frequency(options['repeat-frequency'])

            if self.options['repeat-days'] != options['repeat-days']:
                edit_win.set_repeat_days(options['repeat-days'])

            if self.options['repeat-times'] != options['repeat-times'] or self.options['repeat-until'] != options['repeat-until']:
                edit_win.set_repeat_duration(options['repeat-until'], options['repeat-times'])

            if self.options['list'] != options['list'] or self.options['user-id'] != options['user-id']:
                edit_win.task_list = options['list']
                edit_win.user_id = options['user-id']
                edit_win.set_task_list_dropdown_selected()
    
            self.edit_win.options = options.copy()

        self.set_options(options)

    def set_options(self, options):
        self.options = options.copy()

        self.set_title(self.options['title'])
        self.set_subtitle(self.options['description'])

        self.set_labels()
        self.refresh_time()
        self.changed()
        self.win.reminders_list.invalidate_sort()

    def update_repeat(self, timestamp, old_timestamp, repeat_times):
        self.set_repeat_times(repeat_times)
        self.set_timestamp(timestamp, old_timestamp)
        self.win.reminders_list.invalidate_sort()

    def set_repeat_times(self, times):
        if self.options['repeat-times'] != times:
            self.options['repeat-times'] = times
            self.set_repeat_label()
        edit_win = self.win.reminder_edit_win
        if edit_win is not None and edit_win.id == self.id:
            edit_win.set_repeat_times(times)

    def refresh_time(self):
        if self.past:
            self.past_due_icon.set_visible(True)
        elif self.options['timestamp'] != 0 and not self.completed:
            timestamp = self.options['timestamp']
            now = floor(time.time())
            self.past_due_icon.set_visible(timestamp <= now)
        else:
            self.past_due_icon.set_visible(False)

    def set_time_label(self):
        timestamp = self.options['old-timestamp'] if self.past else self.options['timestamp']
        if timestamp != 0:
            self.time_label.set_visible(True)
            self.separator.set_visible(True)
            self.time_label.set_label(self.win.get_datetime_label(timestamp))
        else:
            self.time_label.set_visible(False)
            self.separator.set_visible(False)

    def set_repeat_label(self):
        if self.options['repeat-type'] != 0:
            self.repeat_label.set_label(
                self.win.get_repeat_label(
                    self.options['repeat-type'],
                    self.options['repeat-frequency'],
                    self.options['repeat-days'],
                    self.options['repeat-until'],
                    self.options['repeat-times']
                )
            )
            self.repeat_label.set_visible(True)
        else:
            self.repeat_label.set_visible(False)

    def set_labels(self):
        self.set_time_label()
        self.set_repeat_label()

    def set_completed(self, completed):
        self.completed = completed

        if completed:
            self.done_btn_content.set_label(_('Incomplete'))
            self.done_btn_content.set_icon_name('window-close-symbolic')
            self.done_button.set_css_classes(['incomplete', 'rounded'])
            self.completed_icon_box.set_visible(True)
        else:
            self.done_btn_content.set_label(_('Complete'))
            self.done_btn_content.set_icon_name('object-select-symbolic')
            self.done_button.set_css_classes(['complete', 'rounded'])
            self.completed_icon_box.set_visible(False)

        self.refresh_time()
        self.win.reminders_list.invalidate_sort()

    @Gtk.Template.Callback()
    def update_completed(self, button = None):
        if not self.completed:
            self.set_completed(True)
        else:
            self.set_completed(False)

        self.app.run_service_method(
            'UpdateCompleted',
            GLib.Variant('(ssb)', (info.app_id, self.id, self.completed))
        )

        self.set_expanded(False)

        self.changed()

    @Gtk.Template.Callback()
    def on_remove(self, button):
        reminder = f'<b>{self.options["title"]}</b>'
        confirm_dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading=_('Remove reminder?'),
            body=_(f'This will remove {reminder} and cannot be undone.'),
            body_use_markup=True
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('remove', _('Remove'))
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_response_appearance('remove', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.connect('response::remove', lambda *args: self.win.remove_reminder(self))
        confirm_dialog.present()

    @Gtk.Template.Callback()
    def edit(self, button = None):
        self.win.new_edit_win(self)