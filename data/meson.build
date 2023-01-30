desktop_file = install_data(
    'com.github.dgsasha.Remembrance.desktop',
    install_dir: get_option('datadir') / 'applications',
)

configure_file(
    input: 'com.github.dgsasha.Remembrance.service.in',
    output: 'com.github.dgsasha.Remembrance.service',
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/services',
    configuration: configuration_data({
        'bindir': get_option('prefix') / get_option('bindir'),
    }),
)

desktop_file = install_data(
    'autostart/com.github.dgsasha.Remembrance.desktop',
    install_dir: join_paths(get_option('sysconfdir'), 'xdg/autostart'),
)