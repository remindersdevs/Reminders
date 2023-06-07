project(
    'retainer',
    version: '5.0',
    meson_version: '>= 0.59'
)

host_os = host_machine.system().to_lower()

on_windows = (
    host_os.contains('mingw') or
    host_os.contains('cygwin') or
    host_os.contains('windows')
)

dependency('glib-2.0')
dependency('pygobject-3.0')
dependency('libadwaita-1', version: '>=1.2')
dependency('gtk4',version: '>=4.10')

if not on_windows
    dependency('gsound')
    dependency('libsecret-1')
    dependency('webkitgtk-6.0')
endif

release_type = get_option('release-type')

app_file = meson.project_name()
app_executable = on_windows ? app_file + '.exe' : app_file

base_app_id = 'io.github.retainerdevs.Retainer'
devel_app_id = base_app_id + '.Devel'

base_path = '/io/github/retainerdevs/Retainer'
devel_path = base_path + '/Devel'

if release_type == 'Devel'
    app_id = devel_app_id
    path = devel_path
else
    app_id = base_app_id
    path = base_path
endif

service_file = app_file + '-service'
service_executable = on_windows ? service_file + '.exe' : service_file
service_id = app_id + '.Service'
service_interface = service_id
service_object = path + '/Service'

i18n = import('i18n')
python = import('python').find_installation('python3')

gnome = import('gnome')

data_dir = on_windows ? 'share' : get_option('prefix') / get_option('datadir')

exec = on_windows ? app_executable : get_option('prefix') / get_option('bindir') / app_executable
service_exec = on_windows ? service_executable : get_option('prefix') / get_option('bindir') / service_executable
conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('APP_EXECUTABLE', app_executable)
conf.set('BASE_APP_ID', base_app_id)
conf.set('APP_ID', app_id)
conf.set('PROJECT_NAME', meson.project_name())
conf.set('APP_OBJECT', path)
conf.set('SERVICE_ID', service_id)
conf.set('SERVICE_INTERFACE', service_interface)
conf.set('SERVICE_EXECUTABLE', service_executable)
conf.set('SERVICE_OBJECT', service_object)
conf.set('CLIENT_ID', get_option('client-id'))
conf.set('PYTHON_PATH', python.full_path())
conf.set('DATA_DIR', data_dir)
conf.set('LOCALE_DIR', data_dir / 'locale')
conf.set('SERVICE_EXEC', service_exec)
conf.set('EXEC', exec)
conf.set('ON_WINDOWS', on_windows ? 'True' : 'False')
conf.set('PORTALS_ENABLED', get_option('enable-portals') ? 'True' : 'False')

subdir('po')
subdir('data')
subdir('src')
subdir('windows')

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: not on_windows
)
