#!/usr/bin/env bash
# update_potfile.sh
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

dir=$(dirname "$(realpath "$0")")

cd "${dir}/../"

xgettext -f "${dir}/POTFILES" -o "${dir}/retainer.pot" --keyword=_ --add-comments=Translators --from-code=UTF-8 --package-name=retainer
