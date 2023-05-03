<div align="center">

![Reminders](data/icons/io.github.remindersdevs.Reminders.svg)
# Reminders, an open source reminder/to-do app

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
- Optionally sync with CalDAV servers
- Import and export ical/ics files

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
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.remindersdevs.Reminders.yml
```
```
flatpak run io.github.remindersdevs.Reminders.Devel --restart-service
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
- Windows port (Need to look into dbus support on Windows)
- Add a debug mode and make it easier to get logs
- Maybe make a GNOME Shell extension that lets you view your reminders (This probably will never happen)
- Maybe integrate the search with GNOME Shell (Also probably not happening)

If you want to contribute anything, just open a pull request. Depending on what you are going to contribute, you might want to [email me](mailto:dgsasha04@gmail.com) first. This will let me help you get started and it will also help me make sure that multiple people aren't working on the same feature without knowing it.

## Reminders DBus Service Documentation
The documentation can be found [here](REMINDERS_SERVICE.md). You probably will want to select the tag for the latest release of Reminders when looking at the documentation.

## Copying
Reminders is licensed under the terms of the [GNU General Public License, version 3 or later](https://www.gnu.org/licenses/gpl-3.0.txt).
