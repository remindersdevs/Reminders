conf = configuration_data()
conf.set('PYTHON_PATH', python.full_path())
conf.set('LOCALE_DIR', get_option('prefix') / get_option('localedir'))

source_files = files(
  '__init__.py',
  'backend.py',
  'countdowns.py',
  'application.py',
  'ms_to_do.py',
  'queue.py'
)

install_data(
    source_files,
    install_dir: python.get_install_dir() / meson.project_name() / 'service'
)

configure_file(
    input: 'remembrance-service.py',
    output: service_executable,
    configuration: conf,
    install: true,
    install_dir: get_option('prefix') / get_option('libexecdir')
)
