configure_file(
    input: 'info.py',
    output: 'info.py',
    configuration: conf,
    install: true,
    install_dir: python.get_install_dir() / meson.project_name()
)

install_data(
    '__init__.py',
    install_dir: python.get_install_dir() / meson.project_name()
)

subdir('service')
subdir('browser')
