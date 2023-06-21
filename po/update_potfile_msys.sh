#!/usr/bin/env bash
# update_potfile_msys.sh
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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

/${PREFIX}/bin/xgettext -f "${SCRIPT_DIR}/POTFILES" -o "${SCRIPT_DIR}/retainer.pot" --keyword=_ --add-comments=Translators --from-code=UTF-8 --package-name=retainer
