# Remembrance, a reminder app for Linux
This is a work in progress, so be warned that it is not only unstable, but also incomplete.
There will be bugs and there is also a small risk of the app deleting it's own data if something goes wrong, so don't use it for anything serious.

![screenshot](screenshot.png)

## Dependencies:
- PyGObject
- Meson
- Libadwaita
- GLib

## Building:
```
meson build
```
```
ninja -C build install
```

## Todo:
- Make an app icon
- Add an about page
- Add a settings page
- Properly handle and log errors
- Add support recurring reminders
- Improve the UI and give it a more unique style
- Add support for AM/PM time
- Add support for translations
- Only show notification after saving changes if necessary

Email me at dgsasha04@gmail.com if you want to contribute.