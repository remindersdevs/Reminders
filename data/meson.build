conf = configuration_data()
conf.set('PROJECT_NAME', meson.project_name())
conf.set('APP_NAME', app_name)
conf.set('APP_ID', app_name)
conf.set('BINDIR', get_option('prefix') / get_option('bindir'))

configure_file(
    input: 'com.github.dgsasha.Remembrance.service.in',
    output: '@0@.service'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/services',
    configuration: conf,
)

configure_file(
    input: 'com.github.dgsasha.Remembrance.desktop.in',
    output: '@0@.desktop'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'applications',
    configuration: conf,
)

subdir('autostart')
subdir('icons')
