from remembrance import info
from gi.repository import Adw, Gtk
from gettext import gettext as _

def about_window(win):
    return Adw.AboutWindow(
        transient_for = win,
        modal = True,
        application_name = info.app_name,
        application_icon = info.app_id,
        license_type = Gtk.License.GPL_3_0,
        version = info.version,
        developer_name = 'Sasha Hale',
        copyright = _('Copyright 2023 Sasha Hale'),
        website = 'https://github.com/dgsasha/remembrance',
        developers = ['Sasha Hale https://github.com/dgsasha'],
        issue_url = 'https://github.com/dgsasha/remembrance/issues',
    )