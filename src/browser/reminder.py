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
import logging

from gi.repository import Gtk, Adw, GLib, Gdk
from gettext import gettext as _
from math import floor

from remembrance import info
from remembrance.browser.dnd_reminder import DNDReminder

logger = logging.getLogger(info.app_executable)

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
    important_icon = Gtk.Template.Child()

    def __init__(
        self,
        win,
        options,
        reminder_id = None,
        completed = False,
        **kwargs
    ):
        self.win = win
        self.app = win.app
        super().__init__(**kwargs)
        self.id = reminder_id
        self.options = options
        self.selected = False
        self.no_strikethrough = False

        self.prefix_box = self.completed_icon.get_parent().get_parent()
        self.set_completed(completed)
        self.set_important()
        self.set_text()

        self.set_enable_expansion(self.win.reminders_list.get_property('selection-mode') != Gtk.SelectionMode.MULTIPLE)

        actions_box = self.label_box.get_parent()
        suffixes_box = actions_box.get_parent()
        actions_box.set_hexpand(True)
        actions_box.set_vexpand(False)
        suffixes_box.set_vexpand(True)
        actions_box.set_valign(Gtk.Align.FILL)
        actions_box.set_halign(Gtk.Align.END)
        self.set_labels()

        # This is kinda silly but I really only want the rows to be able to be selected by clicking on the header
        # Otherwise bad things happen
        header = suffixes_box.get_parent().get_parent().get_parent()
        clicked_gesture = Gtk.GestureClick()
        clicked_gesture.connect('pressed', self.pressed)
        clicked_gesture.connect('released', self.released)

        header.add_controller(clicked_gesture)

        reminder_clicked = Gtk.GestureClick()
        reminder_clicked.connect('released', self.reminder_released)
        self.add_controller(reminder_clicked)

        long_press_gesture = Gtk.GestureLongPress.new()
        long_press_gesture.connect('pressed', self.long_pressed)
        header.add_controller(long_press_gesture)

        self.win.connect('notify::time-format', lambda *args: self.set_time_label())

        drag_source = Gtk.DragSource()
        drag_source.connect('drag-begin', self.drag_begin)
        drag_source.connect('drag-cancel', self.drag_cancel)
        drag_source.connect('drag-end', self.drag_end)
        drag_source.set_content(Gdk.ContentProvider.new_for_value(self.id))
        drag_source.set_actions(Gdk.DragAction.MOVE)
        self.add_controller(drag_source)

    def drag_begin(self, drag_source, drag):
        icon = Gtk.DragIcon.get_for_drag(drag)
        icon.set_child(
            DNDReminder(
                self.time_label.get_label() if self.time_label.get_visible() else None,
                self.repeat_label.get_label() if self.time_label.get_visible() else None,
                self.past_due_icon.get_visible(),
                self.completed,
                self.options['important'],
                title = self.get_title(),
                subtitle = self.get_subtitle()
            )
        )
        self.hide()

    def drag_end(self, drag_source, drag, delete_data):
        if not delete_data:
            self.show()

    def drag_cancel(self, drag_source, drag, reason):
        self.show()

    def set_text(self):
        self.set_title(f'<span strikethrough=\'{"true" if self.completed and not self.no_strikethrough else "false"}\'>{self.options["title"]}</span>')
        if len(self.options['description']) > 0:
            self.set_subtitle(f'<span strikethrough=\'{"true" if self.completed and not self.no_strikethrough else "false"}\'>{self.options["description"]}</span>')
        else:
            self.set_subtitle('')

    def pressed(self, gesture, n_pressed, x, y):
        if gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK:
            self.win.set_selecting(True)

        if gesture.get_current_event_state() & Gdk.ModifierType.SHIFT_MASK:
            if self.win.reminders_list.get_property('selection-mode') == Gtk.SelectionMode.MULTIPLE:
                self.select_between()
                self.selected = False
                self.win.last_selected_row = self
                return

        self.win.last_selected_row = self

        if self.win.reminders_list.get_property('selection-mode') == Gtk.SelectionMode.MULTIPLE:
            if not self in self.win.reminders_list.get_selected_rows():
                self.set_selectable(True)
                self.win.reminders_list.select_row(self)
                self.selected = False
            else:
                self.selected = True

    def select_between(self):
        if self.win.last_selected_row is None:
            return
        count = 0
        selecting = False
        set_selecting_false = False
        while True:
            row = self.win.reminders_list.get_row_at_index(count)
            if row is None:
                break
            elif (row is self.win.last_selected_row or row is self) and self.win.last_selected_row is not self:
                if not selecting:
                    selecting = True
                else:
                    set_selecting_false = True
            if selecting:
                row.set_selectable(True)
                self.win.reminders_list.select_row(row)
            else:
                self.win.reminders_list.unselect_row(row)
                row.set_selectable(False)

            if set_selecting_false:
                set_selecting_false = False
                selecting = False
            count += 1

    def long_pressed(self, gesture, x, y):
        if self.win.reminders_list.get_property('selection-mode') != Gtk.SelectionMode.NONE:
            return

        self.win.set_selecting(True)

        if self.win.reminders_list.get_property('selection-mode') == Gtk.SelectionMode.MULTIPLE:
            if not self in self.win.reminders_list.get_selected_rows():
                self.set_selectable(True)
                self.win.reminders_list.select_row(self)
                self.selected = False
            else:
                self.selected = True

    def released(self, gesture, n_pressed, x, y):
        if gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK:
            self.win.set_selecting(True)

    def reminder_released(self, gesture, n_pressed, x, y):
        if self.win.reminders_list.get_property('selection-mode') == Gtk.SelectionMode.MULTIPLE:
            if self.selected:
                self.win.reminders_list.unselect_row(self)
                self.set_selectable(False)
                self.selected = False

    def set_no_strikethrough(self, no_strikethrough):
        if self.no_strikethrough != no_strikethrough:
            self.no_strikethrough = no_strikethrough
            if self.completed:
                self.set_text()

    def update(self, options):
        edit_win = self.win.reminder_edit_win
        if edit_win is not None and edit_win.id == self.id:
            if self.options['title'] != options['title']:
                edit_win.title_entry.set_text(options['title'])

            if self.options['description'] != options['description']:
                edit_win.description_entry.set_text(options['description'])

            if self.options['timestamp'] != options['timestamp'] or self.options['due-date'] != options['due-date']:
                edit_win.set_time(options['timestamp'], options['due-date'])

            if self.options['repeat-type'] != options['repeat-type']:
                edit_win.set_repeat_type(options['repeat-type'])

            if self.options['repeat-frequency'] != options['repeat-frequency']:
                edit_win.set_repeat_frequency(options['repeat-frequency'])

            if self.options['repeat-days'] != options['repeat-days']:
                edit_win.set_repeat_days(options['repeat-days'])

            if self.options['repeat-times'] != options['repeat-times'] or self.options['repeat-until'] != options['repeat-until']:
                edit_win.set_repeat_duration(options['repeat-until'], options['repeat-times'])

            if self.options['list-id'] != options['list-id'] or self.options['user-id'] != options['user-id']:
                edit_win.task_list = options['list-id']
                edit_win.user_id = options['user-id']
                edit_win.set_task_list_dropdown_selected()

            if self.options['important'] != options['important']:
                edit_win.set_important(options['important'])

            edit_win.options = options.copy()

        self.set_options(options)

    def set_options(self, options):
        self.options.update(options)

        self.set_text()
        self.set_important()
        self.set_labels()
        self.refresh_time()
        self.win.invalidate_filter()

    def set_repeat_times(self, times):
        if self.options['repeat-times'] != times:
            self.options['repeat-times'] = times
            self.set_repeat_label()
        edit_win = self.win.reminder_edit_win
        if edit_win is not None and edit_win.id == self.id:
            edit_win.set_repeat_times(times)

    def refresh_time(self):
        if self.options['timestamp'] != 0 and not self.completed:
            timestamp = self.options['timestamp']
            now = floor(time.time())
            self.past_due_icon.set_visible(timestamp <= now)
        elif self.options['due-date'] != 0 and not self.completed:
            timestamp = self.options['due-date']
            self.past_due_icon.set_visible(datetime.datetime.fromtimestamp(self.options['due-date'], tz=datetime.timezone.utc).date() < datetime.date.today())
        else:
            self.past_due_icon.set_visible(False)

    def set_time_label(self):
        timestamp = 0
        if self.options['timestamp'] != 0:
            timestamp = self.options['timestamp']

        if timestamp != 0:
            self.time_label.set_visible(True)
            self.separator.set_visible(True)
            self.time_label.set_label(self.win.get_datetime_label(timestamp))
        elif self.options['due-date'] != 0:
            self.time_label.set_visible(True)
            self.separator.set_visible(True)
            self.time_label.set_label(self.win.get_date_label(GLib.DateTime.new_from_unix_utc(self.options['due-date'])))
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

    def set_important(self):
        self.important_icon.set_visible(self.options['important'] and not self.completed_icon.get_visible())
        self.prefix_box.set_visible(self.completed_icon.get_visible() or self.important_icon.get_visible())

    def set_completed(self, completed):
        self.completed = completed

        self.completed_icon.set_visible(completed)
        self.important_icon.set_visible(self.options['important'] and not self.completed_icon.get_visible())

        if completed:
            self.done_btn_content.set_label(_('Incomplete'))
            self.done_btn_content.set_icon_name('window-close-symbolic')
            self.done_button.set_css_classes(['incomplete', 'rounded'])
        else:
            self.done_btn_content.set_label(_('Complete'))
            self.done_btn_content.set_icon_name('object-select-symbolic')
            self.done_button.set_css_classes(['complete', 'rounded'])

        self.prefix_box.set_visible(self.completed_icon.get_visible() or self.important_icon.get_visible())

        if not self.no_strikethrough:
            self.set_text()
        self.refresh_time()
        self.win.invalidate_filter()

    def remove(self):
        try:
            if self.id is not None:
                self.app.run_service_method(
                    'RemoveReminder',
                    GLib.Variant('(ss)', (info.app_id, self.id))
                )
                if self.id in self.win.reminder_lookup_dict:
                    self.win.reminder_lookup_dict.pop(self.id)
            self.win.reminders_list.remove(self)
            self.invalidate_filter()
        except Exception as error:
            logger.exception(error)

    def do_update_completed(self):
        try:
            if not self.completed:
                self.set_completed(True)
            else:
                self.set_completed(False)

            results = self.app.run_service_method(
                'UpdateCompleted',
                GLib.Variant('(ssb)', (info.app_id, self.id, self.completed))
            )
            self.options['updated-timestamp'] = results.unpack()[0]

            self.win.reminders_list.invalidate_sort()
        except Exception as error:
            logger.exception(error)

    @Gtk.Template.Callback()
    def expanded_cb(self, row, pspec):
        if self.get_expanded():
            if self.win.expanded is not None:
                self.win.expanded.set_expanded(False)
            self.win.expanded = self
        elif self.win.expanded == self:
                self.win.expanded = None

    @Gtk.Template.Callback()
    def update_completed(self, button = None):
        self.do_update_completed()

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
        confirm_dialog.connect('response::remove', lambda *args: self.remove())
        confirm_dialog.present()

    @Gtk.Template.Callback()
    def edit(self, button = None):
        self.win.new_edit_win(self)
