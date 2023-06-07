# credentials.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from retainer import info

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
