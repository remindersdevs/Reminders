conf = configuration_data()
conf.set('SERVICE_EXECUTABLE', service_executable)
conf.set('SERVICE_ID', service_id)
conf.set('SERVICE_INTERFACE', service_interface)
conf.set('VERSION', meson.project_version())
conf.set('APP_ID', app_id)
conf.set('LIBEXECDIR', get_option('prefix') / get_option('libexecdir'))

desktop_file = configure_file(
    input: 'io.github.dgsasha.Remembrance.Service3.desktop.in.in',
    output: '@0@.desktop.in'.format(service_id),
    configuration: conf,
)

desktop = i18n.merge_file(
    input: desktop_file,
    output: '@0@.desktop'.format(service_id),
    type: 'desktop',
    po_dir: '../../po',
    install: true,
    install_dir: get_option('sysconfdir') / 'xdg/autostart',
)

meson.add_install_script(
    'cp',
    get_option('prefix') / get_option('sysconfdir') / 'xdg/autostart' / '@0@.desktop'.format(service_id),
    get_option('prefix') / get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
    test('Validate desktop file', desktop_utils,
        args: [desktop]
    )
endif

configure_file(
    input: 'io.github.dgsasha.Remembrance.Service3.service.in',
    output: '@0@.service'.format(service_id),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/services',
    configuration: conf,
)

install_data(
    'notification.ogg',
    install_dir: get_option('datadir') / 'sounds' / app_executable,
)

configure_file(
    input: 'io.github.dgsasha.Remembrance.Service3.Reminders.xml.in',
    output: '@0@.xml'.format(service_interface),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1/interfaces',
    configuration: conf,
)
