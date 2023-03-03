# main_window.py - Main Window for Remembrance
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

import datetime
import threading
import time
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from gettext import gettext as _
from difflib import SequenceMatcher

from remembrance import info
from remembrance.browser.reminder import Reminder

class Calendar(threading.Thread):
    '''Updates date labels when day changes'''
    def __init__(self, app):
        self.app = app
        self.time = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.countdown_id = 0
        super().__init__(target=self.run_countdown)
        self.start()

    def bus_callback(self, obj, result):
        proxy = obj.new_for_bus_finish(result)
        proxy.connect("g-signal", self.on_signal_received)

    def on_signal_received(self, proxy, sender, signal, parameters):
        if signal == "PrepareForSleep" and parameters[0]:
            self.app.logger.info('Resuming from sleep')
            self.run_countdown(False)

    def on_countdown_done(self):
        for reminder in self.app.win.reminder_lookup_dict.values():
            reminder.update_day_label()
        self.countdown_id = 0
        self.run_countdown()
        return False

    def remove_countdown(self):
        GLib.Source.remove(self.countdown_id)

    def run_countdown(self, new_day = True):
        try:
            if new_day:
                self.time = self.time + datetime.timedelta(days=1)
                self.timestamp = self.time.timestamp()

            if self.countdown_id != 0:
                GLib.Source.remove(self.countdown_id)
                self.countdown_id = 0

            now = int(time.time())
            self.wait = self.timestamp - now
            if self.timestamp > 0:
                self.countdown_id = GLib.timeout_add_seconds(self.wait, self.on_countdown_done)
            else:
                self.on_countdown_done()
        except Exception as error:
            self.app.logger.error(f'{error}: Failed to set timeout to refresh date labels')

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/main.ui')
class MainWindow(Adw.ApplicationWindow):
    '''Main application Window'''
    __gtype_name__ = 'application_window'

    page_label = Gtk.Template.Child()
    app_menu_button = Gtk.Template.Child()
    main_box = Gtk.Template.Child()
    reminders_list = Gtk.Template.Child()
    sidebar_list = Gtk.Template.Child()
    add_reminder = Gtk.Template.Child()
    all_row = Gtk.Template.Child()
    upcoming_row = Gtk.Template.Child()
    past_row = Gtk.Template.Child()
    completed_row = Gtk.Template.Child()
    sort_button = Gtk.Template.Child()
    flap = Gtk.Template.Child()
    flap_button_revealer = Gtk.Template.Child()
    search_revealer = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()

    def __init__(self, page: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.placeholder = Adw.ActionRow(
            title=_('Press the plus button below to add a reminder')
        )

        self.search_placeholder = Adw.ActionRow(
            title=_('No reminders match your search')
        )
        self.set_title(info.app_name)
        self.set_icon_name(info.app_id)

        self.app = self.get_application()

        self.create_action('all', lambda *args: self.all_reminders())
        self.create_action('upcoming', lambda *args: self.upcoming_reminders())
        self.create_action('past', lambda *args: self.past_reminders())
        self.create_action('completed', lambda *args: self.completed_reminders())
        self.create_action('search', lambda *args: self.search_revealer.set_reveal_child(True), accels=['<Ctrl>f'])
        self.search_entry.connect('stop-search', lambda *args: self.search_revealer.set_reveal_child(False))
        self.settings_create_action('sort')
        self.settings_create_action('descending-sort')
        self.app.settings.connect('changed::sort', self.set_sort)
        self.app.settings.connect('changed::descending-sort', self.set_sort_direction)
        self.activate_action('win.' + page, None)

        self.set_completed_last()
        self.set_completed_reversed()
        self.app.settings.connect('changed::completed-last', self.set_completed_last)
        self.app.settings.connect('changed::completed-reversed', self.set_completed_reversed)

        self.descending_sort = self.app.settings.get_boolean('descending-sort')
        self.sort = self.app.settings.get_enum('sort')
        self.sort_button.set_icon_name('view-sort-descending-symbolic' if self.descending_sort else 'view-sort-ascending-symbolic')

        self.reminders_list.set_placeholder(self.placeholder)
        self.reminders_list.set_sort_func(self.sort_func)

        self.reminder_lookup_dict = {}
        self.calendar = Calendar(self.app)

        reminders = self.app.run_service_method(
            'ReturnReminders',
            None
        )

        if reminders:
            reminders = reminders.unpack()
            for reminder in reminders:
                for dictionary in reminder:
                    self.display_reminder(
                        dictionary['id'],
                        dictionary['title'],
                        dictionary['description'],
                        dictionary['timestamp'],
                        dictionary['repeat-type'],
                        dictionary['repeat-frequency'],
                        dictionary['repeat-days'],
                        dictionary['completed'],
                        dictionary['repeat-until'],
                        dictionary['repeat-times'],
                        dictionary['old-timestamp']
                    )

    def set_completed_last(self, key = None, data = None):
        self.completed_last = self.app.settings.get_boolean('completed-last')
        self.reminders_list.invalidate_sort()

    def set_completed_reversed(self, key = None, data = None):
        self.completed_reversed = self.app.settings.get_boolean('completed-reversed')
        self.reminders_list.invalidate_sort()

    def set_sort(self, key = None, data = None):
        self.sort = self.app.settings.get_enum('sort')
        self.reminders_list.invalidate_sort()

    def set_sort_direction(self, key = None, data = None):
        self.descending_sort = self.app.settings.get_boolean('descending-sort')
        self.sort_button.set_icon_name('view-sort-descending-symbolic' if self.descending_sort else 'view-sort-ascending-symbolic')
        self.reminders_list.invalidate_sort()

    def display_reminder(
        self,
        reminder_id: str,
        title: str,
        description: str,
        timestamp: int,
        repeat_type: int = 0,
        repeat_frequency: int = 1,
        repeat_days: int = 0,
        completed: bool = False,
        repeat_until: int = 0,
        repeat_times: int = 0,
        old_timestamp: int = 0
    ):
        reminder = Reminder(
            self.app,
            reminder_id=reminder_id,
            title=title,
            subtitle=description,
            timestamp=timestamp,
            completed=completed,
            repeat_type=repeat_type,
            repeat_frequency=repeat_frequency,
            repeat_days=repeat_days,
            repeat_until=repeat_until,
            repeat_times=repeat_times,
            old_timestamp=old_timestamp
        )

        self.reminders_list.append(reminder)

        self.reminder_lookup_dict[reminder_id] = reminder

    def create_action(self, name, callback, variant = None, accels = None):
        action = Gio.SimpleAction.new(name, variant)
        action.connect('activate', callback)
        if accels is not None:
            self.app.set_accels_for_action('win.' + name, accels)
        self.add_action(action)

    def settings_create_action(self, name):
        action = self.app.settings.create_action(name)
        self.add_action(action)

    def all_filter(self, reminder):
        reminder.set_past(False)
        if not reminder.is_sensitive():
            reminder.set_sensitive(True)
        return True

    def upcoming_filter(self, reminder):
        now = int(time.time())
        if reminder.timestamp == 0 or (reminder.timestamp > now and not reminder.completed):
            retval = True
            reminder.set_past(False)
        else:
            retval = False
        if reminder.is_sensitive() is not retval:
            reminder.set_sensitive(retval)
        return retval

    def past_filter(self, reminder):
        now = int(time.time())
        if reminder.old_timestamp != 0 and (reminder.old_timestamp < now and not reminder.completed):
            retval = True
            reminder.set_past(True)
        else:
            retval = False
        if reminder.is_sensitive() is not retval:
            reminder.set_sensitive(retval)
        return retval

    def completed_filter(self, reminder):
        if reminder.completed:
            retval = True
            reminder.set_past(False)
        else:
            retval = False
        if reminder.is_sensitive() is not retval:
            reminder.set_sensitive(retval)
        return retval

    def sort_func(self, row1, row2):
        # sort by timestamp from lowest to highest, showing completed reminders last
        # insensitive rows first as a part of fixing https://gitlab.gnome.org/GNOME/gtk/-/issues/5309
        try:
            if (not row1.is_sensitive() and row2.is_sensitive()):
                return -1
            if (row1.is_sensitive() and not row2.is_sensitive()):
                return 1
            if self.completed_last:
                if (not row1.completed and row2.completed):
                    return -1
                if (row1.completed and not row2.completed):
                    return 1

            if self.sort == 0: # time
                if row1.timestamp == row2.timestamp:
                    return 0

                # if reminders are completed reverse order
                if self.completed_last and self.completed_reversed and row1.completed:
                    should_reverse = (not self.descending_sort)
                else:
                    should_reverse = self.descending_sort

                if row1.timestamp < row2.timestamp:
                    return 1 if should_reverse else -1
                # if row1.timestamp > row2.timestamp
                return -1 if should_reverse else 1

            elif self.sort == 1: # alphabetical
                name1 = (row1.get_title() + row1.get_subtitle()).lower()
                name2 = (row2.get_title() + row2.get_subtitle()).lower()
                if name1 == name2:
                    return 0
                if name1 < name2:
                    return 1 if self.descending_sort else -1
                # if name1 > name2
                return -1 if self.descending_sort else 1
        except:
            return 0

    def remove_reminder(self, reminder):
        if reminder.id is not None:
            self.app.run_service_method(
                'RemoveReminder',
                GLib.Variant('(ss)', (info.app_id, reminder.id))
            )
        if reminder in self.app.unsaved_reminders:
            self.app.unsaved_reminders.remove(reminder)
        self.reminders_list.remove(reminder)

    def all_reminders(self):
        if not self.all_row.is_selected():
            self.sidebar_list.select_row(self.all_row)
        self.reminders_list.set_filter_func(self.all_filter)
        self.page_label.set_label(_('All Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.all_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def upcoming_reminders(self):
        if not self.upcoming_row.is_selected():
            self.sidebar_list.select_row(self.upcoming_row)
        self.reminders_list.set_filter_func(self.upcoming_filter)
        self.page_label.set_label(_('Upcoming Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.upcoming_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def past_reminders(self):
        if not self.past_row.is_selected():
            self.sidebar_list.select_row(self.past_row)
        self.reminders_list.set_filter_func(self.past_filter)
        self.page_label.set_label(_('Past Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.past_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def completed_reminders(self):
        if not self.completed_row.is_selected():
            self.sidebar_list.select_row(self.completed_row)
        self.reminders_list.set_filter_func(self.completed_filter)
        self.page_label.set_label(_('Completed Reminders'))
        self.reminders_list.invalidate_sort()
        self.selected = self.completed_row
        if self.flap.get_folded():
            self.flap.set_reveal_flap(False)

    def stop_search(self):
        self.search_entry.set_text('')
        self.flap.set_fold_policy(Adw.FlapFoldPolicy.AUTO)
        self.sidebar_list.set_sensitive(True)
        self.reminders_list.set_placeholder(self.placeholder)
        self.reminders_list.set_sort_func(self.sort_func)
        self.selected.emit('activate')

    def search_filter(self, reminder):
        retval = True
        text = self.search_entry.get_text().lower()
        words = text.split()
        reminder_text = reminder.get_title().lower() + ' ' + reminder.get_subtitle().lower()

        for word in words:
            if word not in reminder_text:
                retval = False

        if retval:
            reminder.set_past(False)

        if reminder.is_sensitive() is not retval:
            reminder.set_sensitive(retval)

        return retval

    def search_sort_func(self, row1, row2):
        if (not row1.is_sensitive() and row2.is_sensitive()):
            return -1
        if (row1.is_sensitive() and not row2.is_sensitive()):
            return 1
        text = self.search_entry.get_text().lower()
        row1_text = row1.get_title().lower() + ' ' + row1.get_subtitle().lower()
        row2_text = row2.get_title().lower() + ' ' + row2.get_subtitle().lower()

        row1_ratio = SequenceMatcher(a=text, b=row1_text).ratio()
        row2_ratio = SequenceMatcher(a=text, b=row2_text).ratio()

        if row1_ratio == row2_ratio:
            return 0
        elif row1_ratio < row2_ratio:
            return 1
        else:
            return -1

    def start_search(self):
        self.searching = True

        self.reminders_list.set_placeholder(self.search_placeholder)
        self.reminders_list.set_filter_func(self.search_filter)
        self.reminders_list.set_sort_func(self.search_sort_func)

    @Gtk.Template.Callback()
    def show_flap_button(self, flap = None, data = None):
        if self.search_revealer.get_reveal_child():
            self.flap_button_revealer.set_reveal_child(False)
        else:
            self.flap_button_revealer.set_reveal_child(self.flap.get_folded())

    @Gtk.Template.Callback()
    def search_enabled_cb(self, entry, data):
        self.show_flap_button()
        if self.search_revealer.get_reveal_child():
            self.search_changed_cb()
            self.search_entry.grab_focus()
            self.flap.set_fold_policy(Adw.FlapFoldPolicy.ALWAYS)
            self.flap.set_reveal_flap(False)
        else:
            self.stop_search()

    @Gtk.Template.Callback()
    def search_changed_cb(self, entry = False):
        text = self.search_entry.get_text()
        if len(text) > 0:
            if not self.searching:
                self.start_search()
            self.reminders_list.invalidate_filter()
            self.reminders_list.invalidate_sort()
            self.page_label.set_label(_(f"Searching '{text}'"))
        else:
            self.searching = False
            self.reminders_list.set_filter_func(self.all_filter)
            self.reminders_list.set_sort_func(self.sort_func)
            self.page_label.set_label(_('Start typing to search'))

    @Gtk.Template.Callback()
    def new_reminder(self, button):
        self.selected = self.all_row
        self.selected.emit('activate')
        reminder = Reminder(
            self.app,
            default=True,
            expanded=True
        )
        self.reminders_list.append(reminder)
