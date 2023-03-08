resources = files(
    'ui/error_dialog.ui',
    'ui/main_window.ui',
    'ui/preferences.ui',
    'ui/reminder.ui',
    'ui/repeat_dialog.ui',
    'ui/time_row.ui',
    'stylesheet.css'
)

gnome.compile_resources(
    app_executable,
    'remembrance.gresource.xml',
    install: true,
    install_dir: python.get_install_dir() / meson.project_name() / 'browser',
    dependencies: resources,
    gresource_bundle: true,
)
