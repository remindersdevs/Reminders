conf = configuration_data()
conf.set('APP_EXECUTABLE', app_executable)
conf.set('APP_NAME', app_name)
conf.set('APP_ID', app_id)
conf.set('BINDIR', get_option('prefix') / get_option('bindir'))

configure_file(
    input: 'com.github.dgsasha.Remembrance.service.in',
    output: '@0@.service'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/services',
    configuration: conf,
)

appstrean_file = configure_file(
    input: 'com.github.dgsasha.Remembrance.metainfo.xml.in',
    output: '@0@.metainfo.xml'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'metainfo',
    configuration: conf,
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
    test(
        'Validate appstream file',
        appstreamcli,
        args: ['validate', '--no-net', appstream_file]
    )
endif

configure_file(
    input: 'com.github.dgsasha.Remembrance.desktop.in',
    output: '@0@.desktop'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'applications',
    configuration: conf,
)

install_data(
    'com.github.dgsasha.Remembrance.gschema.xml',
    install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
    test(
        'Validate schema file',
        compile_schemas,
        args: ['--strict', '--dry-run', meson.current_source_dir()]
    )
endif
