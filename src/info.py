from ast import literal_eval
from gettext import gettext as _
from enum import IntFlag, IntEnum, auto
from platform import system
from os import sep, mkdir
from os.path import isdir

from gi.repository import GLib

version = '@VERSION@'
app_name = _('Reminders')
project_name = '@PROJECT_NAME@'
base_app_id = '@BASE_APP_ID@'
app_id = '@APP_ID@'
app_executable = '@APP_EXECUTABLE@'
app_object = '@APP_OBJECT@'

service_executable = '@SERVICE_EXECUTABLE@'
service_id = '@SERVICE_ID@'
service_interface = '@SERVICE_INTERFACE@'
service_object = '@SERVICE_OBJECT@'

client_id = '@CLIENT_ID@'

data_dir = f'{GLib.get_user_data_dir()}{sep}{project_name}'

if not isdir(data_dir):
    mkdir(data_dir)

app_log = f'{data_dir}{sep}{project_name}.log'
service_log = f'{data_dir}{sep}{project_name}-service.log'

old_data_dir = f'{GLib.get_user_data_dir()}{sep}remembrance'

on_windows = system() == 'Windows'

portals_enabled = literal_eval('@PORTALS_ENABLED@') if not on_windows else False

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
