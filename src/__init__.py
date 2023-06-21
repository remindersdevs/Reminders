# Reminders - Set reminders and manage tasks
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import logging

class Logger:
    def __init__(self, stream, file_stream):
        self.stream = stream
        self.file_stream = file_stream

    def write(self, data):
        if self.stream is not None:
            self.stream.write(data)
            self.stream.flush()
        self.file_stream.write(data)
        self.file_stream.flush()

    def flush(self):
        if self.stream is not None:
            self.stream.flush()
        self.file_stream.flush()

def create_logger(name, path):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s')

    if sys.stdout is not None:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(path, 'w')
    file_handler.setFormatter(formatter)
    sys.stdout = Logger(sys.stdout, file_handler.stream)
    sys.stderr = Logger(sys.stderr, file_handler.stream)
    logger.addHandler(file_handler)
    return logger
