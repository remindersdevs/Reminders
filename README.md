<div align="center">

![Reminders](data/icons/io.github.dgsasha.Remembrance.svg)
# Reminders, a simple reminder app for Linux

<a href="https://flathub.org/apps/details/io.github.dgsasha.Remembrance">
    <img src="https://flathub.org/assets/badges/flathub-badge-i-en.png" width="300px" height="100" alt="Download on Flathub"/>
</a>

![screenshot-dark](screenshot-dark.png)

![screenshot-light](screenshot-light.png)

</div>

## Features
- Set recurring reminders
- Schedule notifications
- Sort, filter, and search for reminders
- Mark reminders as important or complete
- Organize reminders using lists
- Optionally play a sound when notifications are sent
- Optionally sync with Microsoft To Do

## Translators
You can translate Reminders on [Weblate](https://hosted.weblate.org/engage/reminders/), or through GitHub pull requests.

## Manual installation

### Installing dependencies (Flatpak):
```
flatpak install flathub org.gnome.Sdk//44
```
```
flatpak install flathub org.gnome.Platform//44
```
You will also need `flatpak-builder`


### Building (Flatpak):
```
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.dgsasha.Remembrance.yml
```
```
flatpak run io.github.dgsasha.Remembrance.Devel --restart-service
```

### Dependencies (generic):
- `PyGObject`
- `Meson`
- `Libadwaita`
- `GLib`
- `GSound`
- `WebKitGTK`
- `python3-msal`
- `python3-requests`
- `python3-caldav`
- `python3-icalendar`
- `python3-setuptools`

### Building (generic):
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
- Add a debug mode and make it easier to get logs
- Make a GNOME Shell extension that lets you view your reminders
- Maybe integrate the search with GNOME Shell

If you want to contribute anything, just open a pull request. Depending on what you are going to contribute, you might want to [email me](mailto:dgsasha04@gmail.com) first. This will let me help you get started and it will also help me make sure that multiple people aren't working on the same feature without knowing it.

## Reminders DBus Service Documentation
The documentation can be found [here](REMEMBRANCE_SERVICE.md). You probably will want to select the tag for the latest release of Reminders when looking at the documentation.

## Copying
Reminders is licensed under the terms of the [GNU General Public License, version 3 or later](https://www.gnu.org/licenses/gpl-3.0.txt).
