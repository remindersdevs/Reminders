<div align="center">

![Reminders](data/icons/io.github.dgsasha.Remembrance.svg)
# Reminders, a simple reminder app for Linux

![screenshot-dark](screenshot-dark.png)

![screenshot-light](screenshot-light.png)

</div>

## Download
You can download reminders on [Flathub](https://flathub.org/apps/details/io.github.dgsasha.Remembrance)

## Translators
You can translate Reminders on [Weblate](https://hosted.weblate.org/engage/reminders/)

## Installing dependencies (Flatpak):
```
flatpak install flathub org.gnome.Sdk//43
```
You will also need `flatpak-builder`


## Building (Flatpak):
```
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.dgsasha.Remembrance.yml
```
```
flatpak run io.github.dgsasha.Remembrance.Devel --restart-service
```

## Dependencies (generic):
- `PyGObject`
- `Meson`
- `Libadwaita`
- `GLib`
- `GSound`

## Building (generic):
```
meson build -Ddevel=true
```
```
ninja -C build install
```
```
remembrance --restart-service
```

## Todo
- Possibly allow syncing with Microsoft To Do
- Make a GNOME Shell extension that lets you view (and maybe edit) your reminders
- Maybe integrate the search with GNOME Shell
- Possibly add some more animations and UI improvements

If you want to contribute anything, just open a pull request. Depending on what you are going to contribute, you might want to [email me](mailto:dgsasha04@gmail.com) first. This will let me help you get started and it will also help me make sure that multiple people aren't working on the same feature without knowing it.

## [DBus Service Documentation](REMEMBRANCE_SERVICE.md)

## Copying
Reminders is licensed under the terms of the [GNU General Public License, version 3 or later](https://www.gnu.org/licenses/gpl-3.0.txt).
