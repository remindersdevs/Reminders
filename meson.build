project(
    'remembrance',
    version: '1.3',
    meson_version: '>= 0.59',
    default_options: ['prefix=/usr']
)

dependency('glib-2.0')
dependency('pygobject-3.0')
dependency('libadwaita-1')
dependency('gsound')

devel = get_option('devel')

service_version = '1.2'

app_executable = 'remembrance'

base_app_id = 'io.github.dgsasha.Remembrance'
devel_app_id = base_app_id + '.Devel'

app_id = devel ?  devel_app_id : base_app_id

base_path = '/io/github/dgsasha/Remembrance'
path = devel ? base_path + '/Devel' : base_path

service_executable = 'remembrance-service'
service_id = app_id + '.Service1'
service_interface = service_id + '.Reminders'
service_object = path + '/Service1'

i18n = import('i18n')
localedir = get_option('localedir')
gnome = import('gnome')
python = import('python').find_installation('python3')

subdir('po')
subdir('data')
subdir('src')

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
