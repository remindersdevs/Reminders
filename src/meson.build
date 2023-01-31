conf = configuration_data()
conf.set('PYTHON_PATH', python.full_path())
conf.set('INSTALL_DIR', get_option('prefix') / python.get_install_dir() / meson.project_name())

info_conf = configuration_data()
info_conf.set('VERSION', meson.project_version())
info_conf.set('PROJECT_NAME', meson.project_name())
info_conf.set('APP_NAME', app_name)
info_conf.set('APP_ID', app_id)

source_files = files(
  '__init__.py',
  'main.py',
  'backend.py',
  'reminder.py',
  'about.py'
)

install_data(
    source_files,
    install_dir: get_option('prefix') / python.get_install_dir() / meson.project_name()
)

configure_file(
    input: 'info.py',
    output: 'info.py',
    configuration: info_conf,
    install: true,
    install_dir: get_option('prefix') / python.get_install_dir() / meson.project_name()
)

configure_file(
    input: 'remembrance.py',
    output: meson.project_name(),
    configuration: conf,
    install: true,
    install_dir: get_option('prefix') / get_option('bindir')
)

subdir('resources')