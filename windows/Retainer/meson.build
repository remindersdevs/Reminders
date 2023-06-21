if on_windows
    conf = configuration_data()
    conf.set('RETAINER', get_option('prefix') / get_option('bindir') / app_file)
    conf.set('RETAINER_SERVICE', get_option('prefix') / get_option('bindir') / service_file)
    conf.set('ICON', meson.source_root() / 'data' / 'icons' / 'windows' / app_id + '.ico')
    conf.set('VERSION', get_option('prefix') / 'tmp' / 'retainer.txt')
    conf.set('SERVICE_VERSION', get_option('prefix') / 'tmp' / 'retainer-service.txt')
    conf.set('LIB', get_option('prefix') / 'lib')
    conf.set('NAME', app_executable)
    conf.set('SERVICE_NAME', service_executable)

    retainer_spec = configure_file(
        input : 'Retainer.spec.in',
        output : 'Retainer.spec',
        configuration : conf
    )

    meson.add_install_script('freeze.py', retainer_spec, get_option('prefix'))
endif
