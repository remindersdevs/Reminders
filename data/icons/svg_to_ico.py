#!/usr/bin/env python3
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
from subprocess import run
from os import path, sep, mkdir
from shutil import which, rmtree
from atexit import register
from telnetlib import TM

SIZES = (16, 24, 32, 48, 64, 128, 256)
SCRIPT_DIR = path.realpath(path.dirname(__file__))

IDS = ('io.github.retainerdevs.Retainer', 'io.github.retainerdevs.Retainer.Devel')

INKSCAPE = [which('flatpak'), 'run', 'org.inkscape.Inkscape'] if len(sys.argv) > 1 and sys.argv[1] == 'flatpak' else [which('inkscape')]

MAGICK = [which('magick')]

TMP_DIR = SCRIPT_DIR + sep + 'tmp'
WIN_DIR = SCRIPT_DIR + sep + 'windows'

for i in TMP_DIR, WIN_DIR:
    try:
        mkdir(i)
    except:
        pass

register(rmtree, TMP_DIR, ignore_errors=True)

for id in IDS:
    out = []
    for size in SIZES:
        name = f'{TMP_DIR}{sep}{id}-{size}.png'
        out += [name, '-background', 'none']
        run(INKSCAPE + ['-w', str(size), '-h', str(size), '-o', name, f'{SCRIPT_DIR}{sep}{id}.Source.svg'])

    run(MAGICK + out + [f'{WIN_DIR}{sep}{id}.ico'])
