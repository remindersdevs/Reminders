dir = get_option('datadir') / 'icons' / 'hicolor'

if release_type == 'Devel'
    install_subdir(
        'io.github.retainerdevs.Retainer.Devel',
        install_dir: dir,
        strip_directory: true
    )
else
    install_subdir(
        'io.github.retainerdevs.Retainer',
        install_dir: dir,
        strip_directory: true
    )
endif
