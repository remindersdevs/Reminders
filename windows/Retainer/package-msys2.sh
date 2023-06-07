#!/usr/bin/env bash
# package-msys2.sh
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

set -e
set -x

SCRIPT_DIR=$(dirname $(realpath -s $0))
SRC_DIR=${SCRIPT_DIR}/../..

if [[ "$MSYSTEM" == "MINGW32" ]]; then
    ARCH="i686"
    PREFIX="mingw32"
    OUT="${1}/x86"
elif [[ "$MSYSTEM" == "CLANGARM64" ]]; then
    ARCH="clang-aarch64"
    PREFIX="clangarm64"
    OUT="${1}/arm64"
else
    ARCH="x86_64"
    PREFIX="mingw64"
    OUT="${1}/x64"
fi

export PATH="/${PREFIX}/bin:$PATH"

pacman --noconfirm -Syu

pacman --noconfirm -S --needed base-devel

mkdir -p ${SRC_DIR}/build/gtk4

rm -rf ${SRC_DIR}/build/gtk4/src/gtk*

cp -rf ${SCRIPT_DIR}/gtk4/* ${SRC_DIR}/build/gtk4

cd ${SRC_DIR}/build/gtk4

makepkg-mingw --noconfirm --needed --syncdeps --nobuild

makepkg-mingw --noconfirm --needed --noextract || true

makepkg-mingw --noconfirm --install

pacman --noconfirm -S --needed \
    mingw-w64-${ARCH}-glib2 \
    mingw-w64-${ARCH}-gobject-introspection \
    mingw-w64-${ARCH}-gobject-introspection-runtime \
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

export SETUPTOOLS_USE_DISTUTILS=stdlib

/${PREFIX}/bin/python3 -m pip install --upgrade pip

/${PREFIX}/bin/python3 -m pip install --upgrade msal \
    caldav \
    icalendar \
    pyinstaller \
    pyinstaller-versionfile

rm -rf ${SRC_DIR}/build/${OUT}

cd ${SRC_DIR}

/${PREFIX}/bin/meson setup build

/${PREFIX}/bin/meson configure build "-Drelease-type=${1}" "-Dprefix=/${PREFIX}"

/${PREFIX}/bin/ninja -C build install

mkdir -p build/${OUT}

cd build/${OUT}

mkdir -p bin
cp -rf /${PREFIX}/bin/gdbus.exe bin
cp -rf /${PREFIX}/tmp/out/Retainer/certifi bin
cp -rf /${PREFIX}/tmp/out/Retainer/cryptography* bin
cp -rf /${PREFIX}/tmp/out/Retainer/gi bin
cp -rf /${PREFIX}/tmp/out/Retainer/gi_typelibs bin
cp -rf /${PREFIX}/tmp/out/Retainer/lib-dynload bin
cp -rf /${PREFIX}/tmp/out/Retainer/lxml bin
cp -rf /${PREFIX}/tmp/out/Retainer/pytz bin
cp -rf /${PREFIX}/tmp/out/Retainer/share bin
cp -rf /${PREFIX}/tmp/out/Retainer/tzdata bin
cp -rf /${PREFIX}/tmp/out/Retainer/winsdk bin
cp -rf /${PREFIX}/tmp/out/Retainer/retainer*.exe bin
cp -rf /${PREFIX}/tmp/out/Retainer/gspawn*.exe bin
cp -rf /${PREFIX}/tmp/out/Retainer/*.pyd bin
cp -rf /${PREFIX}/tmp/out/Retainer/*.dll bin
cp -rf /${PREFIX}/tmp/out/Retainer/base_library.zip bin

mkdir -p bin/lib/gdk-pixbuf
cp -rf /${PREFIX}/tmp/out/Retainer/lib/gdk-pixbuf/loaders.cache bin/lib/gdk-pixbuf

mkdir -p lib/gdk-pixbuf
cp -rf /${PREFIX}/tmp/out/Retainer/lib/gdk-pixbuf/loaders lib/gdk-pixbuf

mkdir -p share
cp -rf /${PREFIX}/share/retainer share
cp -rf /${PREFIX}/share/locale share

mkdir -p etc
cp -rf /${PREFIX}/etc/fonts etc
