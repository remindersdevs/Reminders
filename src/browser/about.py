# about.py
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
from gi.repository import Adw, Gtk, GLib
from gettext import gettext as _

RELEASE_NOTES = '''
<ul>
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
    abt_win = Adw.AboutWindow(
        modal = True,
        transient_for=win,
        application_name = info.app_name,
        application_icon = info.app_id,
        license_type = Gtk.License.GPL_3_0,
        version = info.version,
        developer_name = _('Reminders Developers'),
        copyright = _('Copyright 2023 Reminders Developers'),
        website = 'https://github.com/remindersdevs/reminders',
        developers = ['dgsasha https://github.com/dgsasha'],
        issue_url = 'https://github.com/remindersdevs/reminders/issues',
        release_notes = RELEASE_NOTES,
        release_notes_version = info.version,
        debug_info = _(f'You can find application logs at {info.app_log} and {info.service_log}, submit these with your bug report.'),
        # Translators: Do not translate this, instead put your name and email here.
        # name <email>
        translator_credits = _("translator-credits")
    )
    abt_win.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Ctrl>w'), Gtk.CallbackAction.new(lambda *args: abt_win.close())))

    abt_win.present()

    if info.on_windows:
        win.app.center_win_on_parent(abt_win)
