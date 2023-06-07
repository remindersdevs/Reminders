#!/usr/bin/env python3
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
from os import mkdir, path, sep
from subprocess import run
from shutil import which

SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)
SCALES = (100, 125, 150, 200, 400)
IDS = ('retainerdevs.Retainer', 'retainerdevs.Retainer.Devel')

INKSCAPE = [which('flatpak'), 'run', 'org.inkscape.Inkscape'] if len(sys.argv) > 1 and sys.argv[1] == 'flatpak' else [which('inkscape')]

SIZE_NAME_PAIRS = (('Square44x44Logo', 44, 44), ('Square150x150Logo', 150, 150), ('StoreLogo', 50, 50), ('SmallTile', 71, 71), ('LargeTile', 310, 310), ('Wide310x150Logo', 310, 150), ('SplashScreen', 620, 300))
SCRIPT_DIR = path.realpath(path.dirname(__file__))

for id in IDS:
    WIN_DIR = f'{SCRIPT_DIR}{sep}windows'
    ID_DIR = f'{WIN_DIR}{sep}{id}'

    for i in WIN_DIR, ID_DIR:
        try:
            mkdir(i)
        except:
            pass

    for size in SIZES:
        NAMES = (f'Square44x44Logo.targetsize-{size}', f'Square44x44Logo.targetsize-{size}_altform-unplated', f'Square44x44Logo.targetsize-{size}_altform-lightunplated')
        for name in NAMES:
            run(INKSCAPE + ['-w', str(size), '-h', str(size), '-o', f'{ID_DIR}{sep}{name}.png', f'{SCRIPT_DIR}{sep}io.github.{id}.Source.svg'])

    for name, x, y in SIZE_NAME_PAIRS:
        x_offset = int((x - y) * (128 / y) + 0.5) / 2 if x > y else 0
        y_offset = int((y - x) * (128 / x) + 0.5) / 2 if x < y else 0

        for scale in SCALES:
            new_x = int(x * (scale / 100) + 0.5)
            new_y = int(y * (scale / 100) + 0.5)

            run(INKSCAPE + ['--export-area', f'{-x_offset}:{-y_offset}:{128+x_offset}:{128+y_offset}', '-w', str(new_x), '-h', str(new_y), '-o', f'{ID_DIR}{sep}{name}.scale-{scale}.png', f'{SCRIPT_DIR}{sep}io.github.{id}.Source.svg'])
