dir = get_option('datadir') / 'icons' / 'hicolor'

if release_type == 'devel'
    install_data(
        'io.github.remindersdevs.Reminders.Devel.svg',
        rename: app_id + '.svg',
        install_dir: dir / 'scalable' / 'apps',
    )
else
    install_data(
        'io.github.remindersdevs.Reminders.svg',
        rename: app_id + '.svg',
        install_dir: dir / 'scalable' / 'apps',
    )
endif

install_data(
    'io.github.remindersdevs.Reminders-symbolic.svg',
    rename: app_id + '-symbolic.svg',
    install_dir: dir / 'symbolic' / 'apps',
)


