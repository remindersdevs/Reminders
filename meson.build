project(
    'remembrance',
    version: '0.1',
    meson_version: '>= 0.59',
    default_options: ['prefix=/usr']
)

app_name = 'Remembrance'
app_id = 'com.github.dgsasha.Remembrance'

gnome = import('gnome')
python = import('python').find_installation('python3')

subdir('data')
subdir('src')

gnome.post_install(
	glib_compile_schemas: true,
	gtk_update_icon_cache: true,
	update_desktop_database: true,
)