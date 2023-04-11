project(
    'remembrance',
    version: '3.3',
    meson_version: '>= 0.59',
    default_options: ['prefix=/usr']
)

dependency('glib-2.0')
dependency('pygobject-3.0')
dependency('libadwaita-1')
dependency('gsound')

release_type = get_option('release-type')

service_version = '3.2'

app_executable = 'remembrance'

base_app_id = 'io.github.dgsasha.Remembrance'
beta_app_id = base_app_id + '.Beta'
devel_app_id = base_app_id + '.Devel'

base_path = '/io/github/dgsasha/Remembrance'
beta_path = base_path + '/Beta'
devel_path = base_path + '/Devel'

if release_type == 'beta'
    app_id = beta_app_id
    path = beta_path
elif release_type == 'devel'
    app_id = devel_app_id
    path = devel_path
else
    app_id = base_app_id
    path = base_path
endif

service_executable = 'remembrance-service'
service_id = app_id + '.Service2'
service_interface = service_id + '.Reminders'
service_object = path + '/Service2'

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
