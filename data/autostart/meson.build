configure_file(
    input: 'com.github.dgsasha.Remembrance.desktop.in',
    output: '@0@.desktop'.format(app_id),
    install: true,
    install_dir: join_paths(get_option('sysconfdir'), 'xdg/autostart'),
    configuration: conf,
)
