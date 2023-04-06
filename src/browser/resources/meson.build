resources = files(
    'ui/edit_lists_window.ui',
    'ui/error_dialog.ui',
    'ui/main_window.ui',
    'ui/ms_user_row.ui',
    'ui/preferences.ui',
    'ui/reminder.ui',
    'ui/reminder_edit_window.ui',
    'ui/shortcuts_window.ui',
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
