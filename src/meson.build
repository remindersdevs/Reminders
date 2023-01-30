conf = configuration_data()
conf.set('PYTHON_PATH', python.full_path())
conf.set('INSTALL_DIR', python.get_install_dir() / 'remembrance')

source_files = files(
  '__init__.py',
  'main.py',
  'backend.py',
  'reminder.py'
)

install_data(
    source_files,
    install_dir: python.get_install_dir() / 'remembrance'
)

configure_file(
    input: 'remembrance.py',
    output: 'remembrance',
    configuration: conf,
    install: true,
    install_dir: get_option('bindir')
)

subdir('resources')