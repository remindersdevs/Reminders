#!/usr/bin/env bash

set -e
set -x

SCRIPT_DIR=$(dirname $(realpath -s $0))
SRC_DIR=${SCRIPT_DIR}/..

if [[ "$MSYSTEM" == "MINGW32" ]]; then
    ARCH="i686"
    PREFIX="mingw32"
    OUT="x86"
elif [[ "$MSYSTEM" == "CLANGARM64" ]]; then
    ARCH="clang-aarch64"
    PREFIX="clangarm64"
    OUT="arm64"
else
    ARCH="x86_64"
    PREFIX="mingw64"
    OUT="x64"
fi

export PATH="/${PREFIX}/bin:$PATH"

pacman --noconfirm -Syu

pacman --noconfirm -S --needed \
    mingw-w64-${ARCH}-cantarell-fonts \
    mingw-w64-${ARCH}-gcc \
    mingw-w64-${ARCH}-glib2 \
    mingw-w64-${ARCH}-gobject-introspection \
    mingw-w64-${ARCH}-gobject-introspection-runtime \
    mingw-w64-${ARCH}-gtk4 \
    mingw-w64-${ARCH}-libadwaita \
    mingw-w64-${ARCH}-meson \
    mingw-w64-${ARCH}-python3 \
    mingw-w64-${ARCH}-python3-gobject \
    mingw-w64-${ARCH}-python-cryptography \
    mingw-w64-${ARCH}-python-lxml \
    mingw-w64-${ARCH}-python-markupsafe \
    mingw-w64-${ARCH}-python-pip \
    mingw-w64-${ARCH}-python-requests \
    mingw-w64-${ARCH}-python-setuptools \
    mingw-w64-${ARCH}-python-winsdk

rm -rf /${PREFIX}/tmp

mkdir -p /${PREFIX}/tmp

mkdir -p /${PREFIX}/etc/gtk-4.0

cp -rf ${SCRIPT_DIR}/settings.ini /${PREFIX}/etc/gtk-4.0/settings.ini

cd /${PREFIX}/tmp

export SETUPTOOLS_USE_DISTUTILS=stdlib

/${PREFIX}/bin/python3 -m pip install --upgrade pip

/${PREFIX}/bin/python3 -m pip install --upgrade msal \
    caldav \
    icalendar \
    pyinstaller \
    pyinstaller-versionfile

rm -rf ${SRC_DIR}/build/${OUT}

cp -rf ${SRC_DIR} reminders

cd reminders

/${PREFIX}/bin/meson setup build "-Drelease-type=${1}"

/${PREFIX}/bin/ninja -C build install

cd ${SRC_DIR}

mkdir -p build/${OUT}

cd build/${OUT}

mkdir reminders

cp -rf /${PREFIX}/tmp/out/Reminders/Reminders*.exe .

cd reminders

mkdir -p bin
cp -rf /${PREFIX}/bin/gdbus.exe bin
cp -rf /${PREFIX}/bin/libfontconfig-1.dll bin
cp -rf /${PREFIX}/tmp/out/Reminders/certifi bin
cp -rf /${PREFIX}/tmp/out/Reminders/cryptography* bin
cp -rf /${PREFIX}/tmp/out/Reminders/gi bin
cp -rf /${PREFIX}/tmp/out/Reminders/gi_typelibs bin
cp -rf /${PREFIX}/tmp/out/Reminders/lib-dynload bin
cp -rf /${PREFIX}/tmp/out/Reminders/lxml bin
cp -rf /${PREFIX}/tmp/out/Reminders/pytz bin
cp -rf /${PREFIX}/tmp/out/Reminders/share bin
cp -rf /${PREFIX}/tmp/out/Reminders/tzdata bin
cp -rf /${PREFIX}/tmp/out/Reminders/winsdk bin
cp -rf /${PREFIX}/tmp/out/Reminders/gspawn*.exe bin
cp -rf /${PREFIX}/tmp/out/Reminders/*.pyd bin
cp -rf /${PREFIX}/tmp/out/Reminders/*.dll bin
cp -rf /${PREFIX}/tmp/out/Reminders/base_library.zip bin

mkdir -p bin/lib/gdk-pixbuf
cp -rf /${PREFIX}/tmp/out/Reminders/lib/gdk-pixbuf/loaders.cache bin/lib/gdk-pixbuf

mkdir -p lib/gdk-pixbuf
cp -rf /${PREFIX}/tmp/out/Reminders/lib/gdk-pixbuf/loaders lib/gdk-pixbuf

mkdir -p share
cp -rf /${PREFIX}/share/reminders share

mkdir -p etc
cp -rf /${PREFIX}/etc/fonts etc
cp -rf /${PREFIX}/etc/gtk-4.0 etc
