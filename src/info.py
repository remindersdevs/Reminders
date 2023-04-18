from ast import literal_eval
from gettext import gettext as _
from enum import IntFlag, IntEnum, auto

from gi.repository import GLib

version = '@VERSION@'
app_name = _('Reminders')
base_app_id = '@BASE_APP_ID@'
app_id = '@APP_ID@'
app_executable = '@APP_EXECUTABLE@'
app_path = '@APP_PATH@'

service_executable = '@SERVICE_EXECUTABLE@'
service_id = '@SERVICE_ID@'
service_interface = '@SERVICE_INTERFACE@'
service_object = '@SERVICE_OBJECT@'
service_path = '@SERVICE_PATH@'

service_version = float('@VERSION@')

portals_enabled = literal_eval('@PORTALS_ENABLED@')

client_id = '@CLIENT_ID@'

data_dir = f'{GLib.get_user_data_dir()}/{app_executable}'

class TimeFormat(IntEnum):
    TWENTYFOUR_HOUR = 0
    TWELVE_HOUR = 1

class RepeatType(IntEnum):
    DISABLED = 0
    MINUTE = 1
    HOUR = 2
    DAY = 3
    WEEK = 4

class RepeatDays(IntFlag):
    MON = auto()
    TUE = auto()
    WED = auto()
    THU = auto()
    FRI = auto()
    SAT = auto()
    SUN = auto()
