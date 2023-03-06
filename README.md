<div align="center">

![Reminders](data/icons/io.github.dgsasha.Remembrance.svg)
# Reminders, a simple reminder app for Linux

![screenshot-dark](screenshot-dark.png)

![screenshot-light](screenshot-light.png)

</div>

## Translators
You can translate Reminders on [Weblate](https://hosted.weblate.org/engage/reminders/)

## Installing dependencies (Flatpak):
```
flatpak install flathub org.gnome.Sdk//43
```

## Building (Flatpak):
```
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.dgsasha.Remembrance.yml
```
```
flatpak run io.github.dgsasha.Remembrance.Devel --restart-service
```

## Dependencies (generic):
- PyGObject
- Meson
- Libadwaita
- GLib
- GSound

## Building (generic):
```
meson build
```
```
ninja -C build install
```
```
remembrance --restart-service
```

## Todo
- Make a GNOME Shell extension that lets you view (and maybe edit) your reminders
- Maybe integrate the search with GNOME Shell
- Possibly add some more animations and UI improvements

## [DBus Service Documentation](REMEMBRANCE_SERVICE.md)

## Copying
Reminders is licensed under the terms of the [GNU General Public License, version 3 or later](https://www.gnu.org/licenses/gpl-3.0.txt).
