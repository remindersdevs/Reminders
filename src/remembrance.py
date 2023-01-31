#!@PYTHON_PATH@
# Remembrance - A reminder app for Linux
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
from gi.repository import Gio
from remembrance import info

install_dir = '@INSTALL_DIR@'

resource = Gio.Resource.load(f'{install_dir}/{info.project_name}.gresource')
resource._register()

if __name__ == '__main__':
    from remembrance import main

    sys.exit(main.main())