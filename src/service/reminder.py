# reminder.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from retainer import info

class Reminder(dict):
    def __init__(self, *args, **kwargs):
        self.defaults = info.reminder_defaults

        for key, value in self.defaults.items():
            self[key] = value

        super().__init__(*args, **kwargs)

    def set_default(self, key):
        if key in self.defaults.keys():
            self[key] = self.defaults[key]
        else:
            raise KeyError('Invalid key')

    def __setitem__(self, key, val):
        if not isinstance(key, str):
            raise ValueError('Wrong type for key')
        if key in self.defaults.keys():
            needs = type(self.defaults[key])
        else:
            raise KeyError('Invalid key')
        if not isinstance(val, needs):
            try:
                val = needs(val)
            except:
                raise ValueError(f'Wrong type for value {key}')

        super().__setitem__(key, val)

    def copy(self):
        return type(self)(super().copy())
