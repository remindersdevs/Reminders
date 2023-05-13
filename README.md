<div align="center">

![Reminders](data/icons/io.github.remindersdevs.Reminders.svg)
# Reminders, a cross platform and open source reminder app

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

### Building (Windows):
You need at least Windows 10 to install Reminders, but you can probably build it on older versions of Windows

Install [MSYS2](https://www.msys2.org/)

Install [.NET SDK](https://dotnet.microsoft.com/en-us/download)

Install [WiX Toolset](https://wixtoolset.org/docs/intro/)
```
dotnet tool install --global wix --version 4.0.0
```

MSYS2 will be used to build the app in a unix environment (Arch based), and all of the dependencies will be automatically installed. .NET and WiX are used to build the installer. MSI installers go in ./out, but you can run the exes directly in ./build, just move them to ./build/reminders/bin before running them. You need to install the app once to get notifications working though.

```
./windows/build_windows.ps1 -msi
```
```
Usage: build_windows.ps1 [options...]
Options:
        -arches <arcn...> Can be x86, x64, or arm64. Comma separated list, default is amd64.
        -root <path>      MSYS2 root path, default is 'C:\msys64'.
        -msi              Build an msi installer
        -help             Display this message.
```

### Dependencies (generic linux):
- `Libadwaita` >= 1.2
- `GTK` >= 4.10
- `PyGObject`
- `Meson`
- `GLib`
- `python3-msal`
- `python3-requests`
- `python3-caldav`
- `python3-icalendar`
- `python3-setuptools`
- `GSound`
- `WebKitGTK`
- `Libsecret`

### Building (generic linux):
```
meson setup build -Ddevel=true
```
```
ninja -C build install
```
```
remembrance --restart-service
```

## Todo
- Make log files debug logs (Need to add more logging code)
- Maybe make a GNOME Shell extension that lets you view your reminders (This probably will never happen)
- Maybe integrate the search with GNOME Shell (Also probably not happening)

If you want to contribute anything, just open a pull request. Depending on what you are going to contribute, you might want to [email me](mailto:dgsasha04@gmail.com) first. This will let me help you get started and it will also help me make sure that multiple people aren't working on the same feature without knowing it.

## Reminders DBus Service Documentation
The documentation can be found [here](REMINDERS_SERVICE.md). You probably will want to select the tag for the latest release of Reminders when looking at the documentation.

## Copying
Reminders is licensed under the terms of the [GNU General Public License, version 3 or later](https://www.gnu.org/licenses/gpl-3.0.txt).
