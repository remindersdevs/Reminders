#!@PYTHON_PATH@
# Reminders - Set reminders and manage tasks
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

import sys
import gettext
import locale

from os import path, sep, environ
from gi.repository import Gio

LOCALE_DIR = '@LOCALE_DIR@'
DATA_DIR = '@DATA_DIR@'

if getattr(sys, 'frozen', False):
    REMINDERS_PATH = path.realpath(path.dirname(sys.executable))
else:
    REMINDERS_PATH = str(path.realpath(path.dirname(__file__)))

environ['REMINDERS_PATH'] = REMINDERS_PATH

if __name__ == '__main__':
    from reminders import info

    gresource_path = f'{DATA_DIR}{sep}{info.project_name}{sep}{info.project_name}.gresource'

    if not path.isabs(gresource_path):
        gresource_path = path.dirname(REMINDERS_PATH) + sep + gresource_path

    if not path.isabs(LOCALE_DIR):
        locale_dir = path.dirname(REMINDERS_PATH) + sep + LOCALE_DIR

    resource = Gio.Resource.load(gresource_path)
    resource._register()

    from reminders.browser.application import main

    try:
        locale.bindtextdomain(info.project_name, locale_dir)
        locale.textdomain(info.project_name)
    except:
        pass
    gettext.bindtextdomain(info.project_name, locale_dir)
    gettext.textdomain(info.project_name)

    sys.exit(main())
