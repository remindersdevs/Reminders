<div align="center">

<img src="io.github.retainerdevs.Retainer.png" width="128" height="128" alt="Retainer"/>

# Retainer, a cross platform and open source reminder app

<a href="https://flathub.org/apps/details/io.github.dgsasha.Remembrance">
    <img src="https://flathub.org/assets/badges/flathub-badge-i-en.png" width="300" height="100" alt="Download on Flathub"/>
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
You can translate Retainer on [Weblate](https://hosted.weblate.org/engage/reminders/), or through GitHub pull requests.

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
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.retainerdevs.Retainer.Devel.yml
```
```
flatpak run io.github.retainerdevs.Retainer.Devel --restart-service
```

### Building (Windows):
You need at least Windows 10 build 17763 (October 2018) to build and install Retainer.

Install [MSYS2](https://www.msys2.org/)

Install [Visual Studio](https://visualstudio.microsoft.com/)

MSYS2 will be used to build the app in a unix environment (Arch based), and all of the dependencies will be automatically installed. Visual Studio is used to build the installer, but you should probably edit the code in a regular text editor. You might want to consider adding msbuild to the PATH and using dotnet tools to manage the solution and project files.

Open Retainer.sln in Visual Studio and build there. Or run this if msbuild is in the PATH:

```
msbuild Retainer.sln -property:Platform=x64 -property:Configuration=Devel
```

Sometimes the build may fail after certain things are updated, in that case run the clean target in msbuild/VS and also delete the `build` folder.

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
meson setup build -Drelease-type=Devel
```
```
ninja -C build install
```
```
retainer --restart-service
```

## Todo
- Make log files debug logs (Need to add more logging code)

If you want to contribute anything, just open a pull request. Depending on what you are going to contribute, you might want to [email me](mailto:dgsasha04@gmail.com) first. This will let me help you get started and it will also help me make sure that multiple people aren't working on the same feature without knowing it.

## Retainer DBus Service Documentation
The documentation can be found [here](RETAINER_SERVICE.md). You probably will want to select the tag for the latest release of Retainer when looking at the documentation.

## Copying
Retainer is licensed under the terms of the [Mozilla Public License, Version 2.0](https://www.mozilla.org/en-US/MPL/2.0/).
