# info.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from gettext import gettext as _
from enum import IntFlag, IntEnum, auto
from os import sep, mkdir
from os.path import isdir

from gi.repository import GLib

on_windows = @ON_WINDOWS@

if on_windows:
    try:
        from winsdk.windows.storage import ApplicationData
        user_data_dir = ApplicationData.current.local_folder.path
    except:
        user_data_dir = GLib.get_user_data_dir()
else:
    user_data_dir = GLib.get_user_data_dir()

version = '@VERSION@'
app_name = _('Retainer')
project_name = '@PROJECT_NAME@'
base_app_id = '@BASE_APP_ID@'
app_id = '@APP_ID@'
app_executable = '@APP_EXECUTABLE@'
app_object = '@APP_OBJECT@'

service_executable = '@SERVICE_EXECUTABLE@'
service_id = '@SERVICE_ID@'
service_interface = '@SERVICE_INTERFACE@'
service_object = '@SERVICE_OBJECT@'

win_id = app_id[len('io.github.'):].lower()
win_service_id = service_id[len('io.github.'):].lower()

client_id = '@CLIENT_ID@'

data_dir = f'{user_data_dir}{sep}{project_name}'

if not isdir(data_dir):
    mkdir(data_dir)

app_log = f'{data_dir}{sep}{project_name}.log'
service_log = f'{data_dir}{sep}{project_name}-service.log'

portals_enabled = @PORTALS_ENABLED@ if not on_windows else False

reminder_defaults = {
    'title': '',
    'description': '',
    'due-date': 0,
    'timestamp': 0,
    'shown': False,
    'completed': False,
    'important': False,
    'repeat-type': 0,
    'repeat-frequency': 1,
    'repeat-days': 0,
    'repeat-until': 0,
    'repeat-times': -1,
    'created-timestamp': 0,
    'updated-timestamp': 0,
    'completed-timestamp': 0,
    'completed-date': 0,
    'list-id': 'local',
    'uid': ''
}

class TimeFormat(IntEnum):
    TWENTYFOUR_HOUR = 0
    TWELVE_HOUR = 1

class RepeatType(IntEnum):
    DISABLED = 0
    MINUTE = 1
    HOUR = 2
    DAY = 3
    WEEK = 4
    MONTH = 5
    YEAR = 6

class RepeatDays(IntFlag):
    MON = auto()
    TUE = auto()
    WED = auto()
    THU = auto()
    FRI = auto()
    SAT = auto()
    SUN = auto()
