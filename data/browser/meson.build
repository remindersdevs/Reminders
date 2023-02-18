conf = configuration_data()
conf.set('APP_EXECUTABLE', app_executable)
conf.set('APP_ID', app_id)
conf.set('BINDIR', get_option('prefix') / get_option('bindir'))

configure_file(
    input: 'com.github.dgsasha.Remembrance.service.in',
    output: '@0@.service'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/services',
    configuration: conf,
)

appstream_file = configure_file(
    input: 'com.github.dgsasha.Remembrance.metainfo.xml.in.in',
    output: '@0@.metainfo.xml.in'.format(app_id),
    configuration: conf,
)

appstream = i18n.merge_file(
  input: appstream_file,
  output: '@0@.metainfo.xml'.format(app_id),
  po_dir: '../../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
    test(
        'Validate appstream file',
        appstreamcli,
        args: ['validate', '--no-net', appstream]
    )
endif

desktop_file = configure_file(
    input: 'com.github.dgsasha.Remembrance.desktop.in.in',
    output: '@0@.desktop.in'.format(app_id),
    configuration: conf,
)

desktop = i18n.merge_file(
  input: desktop_file,
  output: '@0@.desktop'.format(app_id),
  type: 'desktop',
  po_dir: '../../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
    test('Validate desktop file', desktop_utils,
        args: [desktop]
    )
endif

configure_file(
    input: 'com.github.dgsasha.Remembrance.gschema.xml.in',
    output: '@0@..gschema.xml'.format(app_id),
    install: true,
    install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas'),
    configuration: conf,
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
    test(
        'Validate schema file',
        compile_schemas,
        args: ['--strict', '--dry-run', meson.current_source_dir()]
    )
endif
