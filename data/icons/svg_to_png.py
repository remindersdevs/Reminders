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

SIZES = (16, 24, 32, 48, 256)
IDS = ('io.github.retainerdevs.Retainer', 'io.github.retainerdevs.Retainer.Devel')

SYMBOLIC = 'io.github.retainerdevs.Retainer-symbolic'

INKSCAPE = [which('flatpak'), 'run', 'org.inkscape.Inkscape'] if len(sys.argv) > 1 and sys.argv[1] == 'flatpak' else [which('inkscape')]

SCRIPT_DIR = path.realpath(path.dirname(__file__))

for id in IDS:
    ID_DIR = f'{SCRIPT_DIR}{sep}{id}'
    try:
        mkdir(ID_DIR)
    except:
        pass

    for size in SIZES:
        for hidpi in False, True:
            SIZE_DIR = f'{ID_DIR}{sep}{size}x{size}'
            if hidpi:
                SIZE_DIR += '@2x'
                size *= 2

            try:
                mkdir(SIZE_DIR)
            except:
                pass

            APPS_DIR = SIZE_DIR + sep + 'apps'

            try:
                mkdir(APPS_DIR)
            except:
                pass

            run(INKSCAPE + ['-w', str(size), '-h', str(size), '-o', f'{APPS_DIR}{sep}{id}.png', f'{SCRIPT_DIR}{sep}{id}.Source.svg'])


    SYMBOLIC_DIR = ID_DIR + sep + 'symbolic'
    try:
        mkdir(SYMBOLIC_DIR)
    except:
        pass

    APPS_DIR = SYMBOLIC_DIR + sep + 'apps'

    try:
        mkdir(APPS_DIR)
    except:
        pass

    run(INKSCAPE + ['--export-plain-svg', '-o', f'{APPS_DIR}{sep}{SYMBOLIC}.svg',  f'{SCRIPT_DIR}{sep}{SYMBOLIC}.Source.svg'])
