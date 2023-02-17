resources = files(
    'ui/main.ui',
    'ui/reminder.ui',
    'ui/preferences.ui',
    'ui/time_box.ui'
)

gnome.compile_resources(
    app_executable,
    'remembrance.gresource.xml',
    install: true,
    install_dir: python.get_install_dir() / meson.project_name() / 'browser',
    dependencies: resources,
    gresource_bundle: true,
)