# dnd_reminder.py
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

from gi.repository import Gtk, Adw

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/dnd_reminder.ui')
class DNDReminder(Adw.ActionRow):
    __gtype_name__ = 'DNDReminder'

    completed_icon = Gtk.Template.Child()
    separator = Gtk.Template.Child()
    past_due_icon = Gtk.Template.Child()
    label_box = Gtk.Template.Child()
    time_label = Gtk.Template.Child()
    repeat_label = Gtk.Template.Child()
    important_icon = Gtk.Template.Child()

    def __init__(
        self,
        time_label,
        repeat_label,
        past_due,
        completed,
        important,
        **kwargs
    ):
        super().__init__(**kwargs)
        prefix_box = self.completed_icon.get_parent()
        self.completed_icon.set_visible(completed)
        self.important_icon.set_visible(important and not self.completed_icon.get_visible())
        prefix_box.set_visible(self.completed_icon.get_visible() or self.important_icon.get_visible())

        if time_label is not None:
            self.time_label.set_label(time_label)
            self.time_label.set_visible(True)
        else:
            self.separator.set_visible(False)

        if repeat_label is not None:
            self.repeat_label.set_label(repeat_label)
            self.repeat_label.set_visible(True)

        self.past_due_icon.set_visible(past_due)

        actions_box = self.label_box.get_parent()
        suffixes_box = actions_box.get_parent()
        actions_box.set_hexpand(True)
        actions_box.set_vexpand(False)
        suffixes_box.set_vexpand(True)
        actions_box.set_valign(Gtk.Align.FILL)
        actions_box.set_halign(Gtk.Align.END)

        self.set_size_request(self.get_allocated_width(), -1)
        self.add_css_class('card')
        self.add_css_class('dnd-reminder')
