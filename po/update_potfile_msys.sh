#!/usr/bin/env bash

set -e
set -x

SCRIPT_DIR=$(dirname $(realpath -s $0))

if [[ "$MSYSTEM" == "MINGW32" ]]; then
    ARCH="i686"
    PREFIX="mingw32"
elif [[ "$MSYSTEM" == "CLANGARM64" ]]; then
    ARCH="clang-aarch64"
    PREFIX="clangarm64"
else
    ARCH="x86_64"
    PREFIX="mingw64"
fi

pacman --noconfirm -Syu

pacman --noconfirm -S --needed \
    mingw-w64-${ARCH}-gettext

cd "${SCRIPT_DIR}/../"

/${PREFIX}/bin/xgettext -f "${SCRIPT_DIR}/POTFILES" -o "${SCRIPT_DIR}/reminders.pot" --keyword=_ --add-comments=Translators --from-code=UTF-8 --package-name=reminders
