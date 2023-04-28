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

from remembrance import info

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
