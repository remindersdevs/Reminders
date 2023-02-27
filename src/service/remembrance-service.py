#!@PYTHON_PATH@
# Remembrance service - Backend for Remembrance
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

locale_dir = '@LOCALE_DIR@'

if __name__ == '__main__':
    from remembrance import info
    from remembrance.service.application import main

    locale.bindtextdomain(info.app_executable, locale_dir)
    locale.textdomain(info.app_executable)
    gettext.bindtextdomain(info.app_executable, locale_dir)
    gettext.textdomain(info.app_executable)

    sys.exit(main())