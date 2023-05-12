source_files = files(
  '__init__.py',
  'backend.py',
  'caldav.py',
  'countdowns.py',
  'icalendar.py',
  'application.py',
  'ms_to_do.py',
  'queue.py',
  'reminder.py'
)

install_data(
    source_files,
    install_dir: python.get_install_dir() / meson.project_name() / 'service'
)

configure_file(
    input: 'reminders-service.py',
    output: service_file,
    configuration: conf,
    install: true,
    install_dir: get_option('prefix') / get_option('bindir')
)
