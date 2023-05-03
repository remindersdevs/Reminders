info_conf = configuration_data()
info_conf.set('VERSION', meson.project_version())
info_conf.set('APP_EXECUTABLE', app_executable)
info_conf.set('BASE_APP_ID', base_app_id)
info_conf.set('APP_ID', app_id)
info_conf.set('PROJECT_NAME', meson.project_name())
info_conf.set('APP_OBJECT', path)

info_conf.set('SERVICE_ID', service_id)
info_conf.set('SERVICE_INTERFACE', service_interface)
info_conf.set('SERVICE_EXECUTABLE', service_executable)
info_conf.set('SERVICE_OBJECT', service_object)
info_conf.set('SERVICE_PATH', get_option('prefix') / get_option('libexecdir') / service_executable)

info_conf.set('PORTALS_ENABLED', get_option('enable-portals') ? 'True' : 'False')

info_conf.set('CLIENT_ID', get_option('client-id'))

info_conf.set('INTERFACES_DIR', get_option('prefix') / get_option('datadir') / 'dbus-1/interfaces')

configure_file(
    input: 'info.py',
    output: 'info.py',
    configuration: info_conf,
    install: true,
    install_dir: python.get_install_dir() / meson.project_name()
)

install_data(
    '__init__.py',
    install_dir: python.get_install_dir() / meson.project_name()
)

subdir('service')
subdir('browser')
