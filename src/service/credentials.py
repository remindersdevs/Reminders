# credentials.py
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

from reminders import info

if info.on_windows:
    from winsdk.windows.security.credentials import PasswordVault, PasswordCredential
else:
    from gi import require_version
    require_version('Secret', '1')
    from gi.repository import Secret

class Credentials():
    def __init__(self):
        if info.on_windows:
            self.vault = PasswordVault()
        else:
            self.schema = Secret.Schema.new(
                info.app_id,
                Secret.SchemaFlags.NONE,
                { 'name': Secret.SchemaAttributeType.STRING }
            )

    def add_password(self, username, password):
        if info.on_windows:
            self.vault.add(PasswordCredential(username, username, password))
        else:
            Secret.password_store_sync(
                self.schema,
                { 'name': username },
                None,
                username,
                password,
                None
            )

    def remove_password(self, username):
        if info.on_windows:
            self.vault.remove(self.vault.retrieve(username, username))
        else:
            Secret.password_clear(
                self.schema,
                { 'name': username },
                None,
                None
            )

    def lookup_password(self, username):
        if info.on_windows:
            return self.vault.retrieve(username, username).password
        else:
            return Secret.password_lookup_sync(
                self.schema,
                { 'name': username },
                None
            )
