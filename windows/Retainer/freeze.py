#!/usr/bin/env python3
# freeze.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import os
from retainer import info

SPEC = sys.argv[1]
DEST_DIR = sys.argv[2]

import PyInstaller.__main__
import pyinstaller_versionfile

for name, exe in ('retainer', 'retainer.exe'), ('retainer-service', 'retainer-service.exe'):
    version_file = f'{DEST_DIR}{os.sep}tmp{os.sep}{name}.txt'
    pyinstaller_versionfile.create_versionfile(
        output_file=version_file,
        version=info.version,
        company_name='Retainer Developers',
        legal_copyright='Copyright 2023 Retainer Developers',
        file_description=name,
        internal_name=name,
        original_filename=exe,
        product_name=name
    )

PyInstaller.__main__.run([
    SPEC,
    '--noconfirm',
    f'--distpath={DEST_DIR}{os.sep}tmp{os.sep}out',
])
