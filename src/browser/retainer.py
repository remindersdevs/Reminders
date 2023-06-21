#!@PYTHON_PATH@
# Retainer - Set reminders and manage tasks
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import gettext
import locale

from os import path, sep, environ

LOCALE_DIR = '@LOCALE_DIR@'
DATA_DIR = '@DATA_DIR@'

if __name__ == '__main__':
    from retainer import info
    from retainer import create_logger
    from gi.repository import Gio

    create_logger(info.app_executable, info.app_log)

    def get_path():
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            file = sys.executable
        else:
            file = __file__

        return path.realpath(path.dirname(path.dirname(file)))

    if info.on_windows:
        from winsdk.windows.applicationmodel import Package
        try:
            INSTALL_DIR = Package.current.installed_location.path + sep + 'Retainer'
        except:
            INSTALL_DIR = get_path()
    else:
        INSTALL_DIR = get_path()

    environ['INSTALL_DIR'] = INSTALL_DIR
    if info.on_windows:
        environ['GSK_RENDERER'] = 'cairo'
        environ['GDK_DEBUG'] = 'gl-gles'
        environ['PANGOCAIRO_BACKEND'] = 'fc'
        environ['GTK_CSD'] = '0'
        environ['GDK_WIN32_IMMERSIVE_TITLEBAR'] = '1'

    gresource_path = f'{DATA_DIR}{sep}{info.project_name}{sep}{info.project_name}.gresource'

    if not path.isabs(gresource_path):
        gresource_path = INSTALL_DIR + sep + gresource_path

    if not path.isabs(LOCALE_DIR):
        locale_dir = INSTALL_DIR + sep + LOCALE_DIR

    resource = Gio.Resource.load(gresource_path)
    resource._register()

    from retainer.browser.application import main

    try:
        locale.bindtextdomain(info.project_name, locale_dir)
        locale.textdomain(info.project_name)
    except:
        pass
    gettext.bindtextdomain(info.project_name, locale_dir)
    gettext.textdomain(info.project_name)

    sys.exit(main())
