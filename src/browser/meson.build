conf = configuration_data()
conf.set('PYTHON_PATH', python.full_path())
conf.set('LOCALE_DIR', get_option('prefix') / get_option('localedir'))

source_files = files(
  '__init__.py',
  'about.py',
  'application.py',
  'caldav_sign_in.py',
  'calendar.py',
  'dnd_reminder.py',
  'edit_lists_window.py',
  'error_dialog.py',
  'export_lists_window.py',
  'import_lists_window.py',
  'main_window.py',
  'microsoft_sign_in.py',
  'move_reminders_window.py',
  'preferences.py',
  'reminder.py',
  'reminder_edit_window.py',
  'shortcuts_window.py'
)

install_data(
    source_files,
    install_dir: python.get_install_dir() / meson.project_name() / 'browser'
)

configure_file(
    input: 'reminders.py',
    output: app_executable,
    configuration: conf,
    install: true,
    install_dir: get_option('prefix') / get_option('bindir')
)

subdir('resources')
