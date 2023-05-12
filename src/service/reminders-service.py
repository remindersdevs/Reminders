#!@PYTHON_PATH@
# reminders-service.py
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

from os import environ, path, sep

LOCALE_DIR = '@LOCALE_DIR@'
DATA_DIR = '@DATA_DIR@'

if getattr(sys, 'frozen', False):
    SERVICE_PATH = path.realpath(path.dirname(sys.executable))
else:
    SERVICE_PATH = str(path.realpath(path.dirname(__file__)))

environ['SERVICE_PATH'] = SERVICE_PATH

if __name__ == '__main__':
    from reminders import info

    xml_path = f'{DATA_DIR}{sep}{info.project_name}{sep}{info.service_interface}.xml'

    if not path.isabs(xml_path):
        xml_path = path.dirname(SERVICE_PATH) + sep + xml_path

    environ['REMINDERS_SERVICE_XML'] = xml_path

    from reminders.service.application import main

    if not path.isabs(LOCALE_DIR):
        locale_dir = path.dirname(SERVICE_PATH) + sep + LOCALE_DIR

    try:
        locale.bindtextdomain(info.project_name, locale_dir)
        locale.textdomain(info.project_name)
    except:
        pass
    gettext.bindtextdomain(info.project_name, locale_dir)
    gettext.textdomain(info.project_name)

    sys.exit(main())
