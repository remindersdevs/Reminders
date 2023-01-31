resources = files(
    'ui/main.ui',
    'ui/reminder.ui'
)

gnome.compile_resources(
    meson.project_name(),
    'remembrance.gresource.xml',
    install: true,
    install_dir: get_option('prefix') / python.get_install_dir() / meson.project_name(),
    dependencies: resources,
    gresource_bundle: true,
)