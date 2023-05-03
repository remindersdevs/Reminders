from gi.repository import Gio

from reminders import info
from pathlib import Path

resource = Gio.Resource.load(f'{Path(__file__).parent.absolute()}/{info.app_executable}.gresource')
resource._register()
