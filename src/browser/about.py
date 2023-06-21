# about.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from retainer import info
from gi.repository import Adw, Gtk
from gettext import gettext as _
from os.path import isfile

RELEASE_NOTES = '''
<ul>
    <li>Windows port</li>
    <li>UI improvements</li>
    <li>Added support for making the week start on sunday</li>
    <li>Added indicators that show how many incomplete reminders are in each list/group</li>
    <li>Added support for syncing with CalDAV servers</li>
    <li>Added support for selecting multiple reminders in one click by holding shift</li>
    <li>Added support for dragging and dropping reminders between lists</li>
    <li>Added support for importing and exporting ical/ics files</li>
    <li>Added more multithreading to significantly speed up certain operations</li>
    <li>Added support for syncing recurring reminders with Microsoft To Do</li>
    <li>Added support for creating monthly and yearly repeating reminders</li>
    <li>Version numbers are now handled in a logical way (as in they aren't just doubles)</li>
    <li>Microsoft sign in window now appears in the app instead of in the browser</li>
    <li>Significantly improve how recurring reminders function</li>
    <li>Fix date/time text wrapping awkwardly</li>
    <li>Improvements to handling of network errors</li>
    <li>Fix some other minor issues</li>
    <li>Bump API version</li>
</ul>
'''

def about_window(win):
    if isfile(info.app_log):
        with open(info.app_log, 'r') as f:
            app_log = f.read()
    else:
        app_log = ''

    if isfile(info.service_log):
        with open(info.service_log, 'r') as f:
            service_log = f.read()
    else:
        service_log = ''

    abt_win = Adw.AboutWindow(
        modal = True,
        transient_for=win,
        application_name = info.app_name,
        application_icon = info.app_id,
        license_type = Gtk.License.GPL_3_0,
        version = info.version,
        developer_name = _('Retainer Developers'),
        copyright = _('Copyright 2023 Retainer Developers'),
        website = 'https://github.com/remindersdevs/reminders',
        developers = ['dgsasha https://github.com/dgsasha'],
        issue_url = 'https://github.com/remindersdevs/reminders/issues',
        release_notes = RELEASE_NOTES,
        release_notes_version = info.version,
        debug_info = app_log + '\n\n' + service_log,
        # Translators: Do not translate this, instead put your name and email here.
        # name <email>
        translator_credits = _("translator-credits")
    )
    abt_win.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: abt_win.close())))

    abt_win.present()
