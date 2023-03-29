# edit_lists_window.py
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
from gettext import gettext as _

DEFAULT_LIST_TITLE = _('New List')

@Gtk.Template(resource_path='/io/github/dgsasha/remembrance/ui/edit_lists_window.ui')
class EditListsWindow(Adw.Window):
    __gtype_name__ = 'edit_lists_window'

    box = Gtk.Template.Child()

    def __init__(self, win, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_transient_for(win)
        self.users = {}
        self.win = win

        for user_id, value in win.task_list_names.items():
            if user_id in self.win.emails.keys() or user_id == 'local':
                self.users[user_id] = ListGroup(win, user_id, value)
                self.box.append(self.users[user_id])

    def list_updated(self, user_id, list_id, list_name):
        if user_id in self.users.keys():
            self.users[user_id].add_child(list_name, list_id)
        else:
            self.users[user_id] = ListGroup(self.win, user_id, {list_id: list_name})

    def list_removed(self, user_id, list_id):
        if user_id in self.users.keys():
            self.users[user_id].list_removed(list_id)
            if len(self.users[user_id].lists.keys()) == 0:
                self.box.remove(self.users[user_id])
                self.users.pop(user_id)

class ListGroup(Adw.PreferencesGroup):
    def __init__(self, win, user_id, lists, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.win = win
        self.user_id = user_id
        self.set_title(_('Local') if user_id == 'local' else win.emails[user_id])
        self.lists = {}
        for list_id, list_name in lists.items():
            self.add_child(list_name, list_id)

        new_list_btn = Gtk.Button()
        content = Adw.ButtonContent(icon_name='list-add-symbolic', label=_('New List'))
        new_list_btn.set_child(content)
        new_list_btn.add_css_class('flat')
        new_list_btn.connect('clicked', lambda *args: self.add_child(focus = True))
        self.set_header_suffix(new_list_btn)

    def add_child(self, list_name = None, list_id = None, focus = False):
        if list_id in self.lists.keys():
            self.lists[list_id].set_text(list_name)
        else:
            child = ListRow(self, self.win, self.user_id, list_name, list_id)
            self.add(child)
            if focus:
                child.grab_focus()
            if list_id is not None:
                self.lists[list_id] = child

    def list_removed(self, list_id = None):
        if list_id in self.lists.keys():
            self.remove(self.lists[list_id])
            self.lists.pop(list_id)

    def remove_child(self, child, user_id, list_id):
        if list_id is not None:
            self.win.delete_list(user_id, list_id)
            self.lists.pop(list_id)
        self.remove(child)

class ListRow(Adw.EntryRow):
    def __init__(self, group, win, user_id, list_name = None, list_id = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = group
        self.user_id = user_id
        self.list_id = list_id
        self.set_title(_('What should the list be called?'))
        self.win = win
        self.list_name = list_name
        self.set_text(DEFAULT_LIST_TITLE if list_name is None else list_name)
        self.save_button = Gtk.Button.new_from_icon_name('object-select-symbolic')
        self.save_button.set_valign(Gtk.Align.CENTER)
        self.save_button.add_css_class('circular')
        self.save_button.add_css_class('suggested-action')
        self.save_button.connect('clicked', lambda *args: self.update())
        self.add_suffix(self.save_button)
        self.delete_button = Gtk.Button.new_from_icon_name('edit-delete-symbolic')
        self.delete_button.set_valign(Gtk.Align.CENTER)
        self.delete_button.add_css_class('circular')
        self.delete_button.add_css_class('destructive-action')
        self.delete_button.connect('clicked', lambda *args: self.delete())
        self.add_suffix(self.delete_button)
        self.connect('changed', lambda *args: self.check_saved())
        self.check_saved()
        self.delete_button.set_sensitive(not self.list_id in ('ms-tasks', 'local'))

    def update(self):
        list_name = self.get_text()
        count = 0
        while list_name in self.win.task_list_names[self.user_id].values():
            count += 1
            list_name = f'{self.get_text()} ({count})' 
        self.list_id = self.win.update_list(self.user_id, list_name, self.list_id)
        self.list_name = list_name
        self.save_button.set_sensitive(False)
        self.delete_button.set_sensitive(not self.list_id in ('ms-tasks', 'local'))
        self.group.lists[self.list_id] = self
        self.set_text(self.list_name)

    def delete(self):
        list_name = f'<b>{self.get_text()}</b>'
        confirm_dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading=_('Remove list?'),
            body=_(f'This will remove {list_name} and cannot be undone.'),
            body_use_markup=True
        )
        confirm_dialog.add_response('cancel', _('Cancel'))
        confirm_dialog.add_response('remove', _('Remove'))
        confirm_dialog.set_default_response('cancel')
        confirm_dialog.set_response_appearance('remove', Adw.ResponseAppearance.DESTRUCTIVE)
        confirm_dialog.connect('response::remove', lambda *args: self.group.remove_child(self, self.user_id, self.list_id))
        confirm_dialog.present()

    def check_saved(self):
        self.save_button.set_sensitive(len(self.get_text()) != 0 and self.get_text() != self.list_name)