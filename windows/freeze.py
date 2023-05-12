#!/usr/bin/env python3

import sys
import os
from reminders import info

SPEC = sys.argv[1]
DEST_DIR = sys.argv[2]

import PyInstaller.__main__
import pyinstaller_versionfile

for name in 'Reminders', 'Reminders Service':
    version_file = f'{DEST_DIR}{os.sep}tmp{os.sep}{name}.txt'
    pyinstaller_versionfile.create_versionfile(
        output_file=version_file,
        version=info.version,
        company_name='Reminders Developers',
        legal_copyright='Copyright 2023 Reminders Developers',
        file_description=name,
        internal_name=name,
        original_filename=f'{name}.exe',
        product_name=name
    )

PyInstaller.__main__.run([
    SPEC,
    '--noconfirm',
    f'--distpath={DEST_DIR}{os.sep}tmp{os.sep}out',
])
