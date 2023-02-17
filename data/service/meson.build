conf = configuration_data()
conf.set('SERVICE_EXECUTABLE', service_executable)
conf.set('SERVICE_ID', service_id)
conf.set('APP_ID', app_id)
conf.set('LIBEXECDIR', get_option('prefix') / get_option('libexecdir'))

desktop = configure_file(
    input: 'com.github.dgsasha.Remembrance.Service.desktop.in',
    output: '@0@.desktop'.format(service_id),
    configuration: conf,
)

install_data(
    desktop,
    install_dir: get_option('sysconfdir') / 'xdg/autostart',
)

install_data(
    desktop,
    install_dir: get_option('datadir') / 'applications',
)

configure_file(
    input: 'com.github.dgsasha.Remembrance.Service.service.in',
    output: '@0@.service'.format(service_id),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/services',
    configuration: conf,
)