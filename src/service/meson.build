conf = configuration_data()
conf.set('PYTHON_PATH', python.full_path())

source_files = files(
  '__init__.py',
  'backend.py',
  'application.py'
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