resources = files(
    'ui/caldav_sign_in.ui',
    'ui/dnd_reminder.ui',
    'ui/edit_lists_window.ui',
    'ui/error_dialog.ui',
    'ui/export_lists_window.ui',
    'ui/import_lists_window.ui',
    'ui/main_window.ui',
    'ui/microsoft_sign_in.ui',
    'ui/move_reminders_window.ui',
    'ui/preferences.ui',
    'ui/preferences_user_row.ui',
    'ui/reminder.ui',
    'ui/reminder_edit_window.ui',
    'ui/shortcuts_window.ui',
    'ui/task_list_row.ui',
    'stylesheet.css'
)

gnome.compile_resources(
    app_executable,
    'reminders.gresource.xml',
    install: true,
    install_dir: python.get_install_dir() / meson.project_name() / 'browser',
    dependencies: resources,
    gresource_bundle: true,
)
