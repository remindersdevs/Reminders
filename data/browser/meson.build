desktop_file = configure_file(
    input: 'io.github.retainerdevs.Retainer.desktop.in.in',
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
    input: 'io.github.retainerdevs.Retainer.service.in',
    output: '@0@.service'.format(app_id),
    install: true,
    install_dir: get_option('datadir') / 'dbus-1' / 'services',
    configuration: conf,
)
