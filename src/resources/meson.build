resources = files(
    'ui/main.ui',
    'ui/reminder.ui'
)

gnome.compile_resources(
    'remembrance',
    'remembrance.gresource.xml',
    install: true,
    install_dir: python.get_install_dir() / 'remembrance',
    dependencies: resources,
    gresource_bundle: true,
)