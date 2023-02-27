conf = configuration_data()
conf.set('PYTHON_PATH', python.full_path())
conf.set('LOCALE_DIR', get_option('prefix') / get_option('localedir'))

source_files = files(
  '__init__.py',
  'application.py',
  'main_window.py',
  'reminder.py',
  'about.py',
  'preferences.py'
)

install_data(
    source_files,
    install_dir: python.get_install_dir() / meson.project_name() / 'browser'
)

configure_file(
    input: 'remembrance.py',
    output: app_executable,
    configuration: conf,
    install: true,
    install_dir: get_option('prefix') / get_option('bindir')
)

subdir('resources')