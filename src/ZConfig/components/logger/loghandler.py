##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

"""Handlers which can plug into a PEP 282 logger."""

import os.path
import sys

from logging import Handler, StreamHandler
from logging.handlers import SysLogHandler
from logging.handlers import HTTPHandler, SMTPHandler
from logging.handlers import NTEventLogHandler as Win32EventLogHandler


class FileHandler(StreamHandler):
    """File handler which supports reopening of logs.

    Re-opening should be used instead of the 'rollover' feature of
    the FileHandler from the standard library's logging package.
    """

    def __init__(self, filename, mode="a"):
        filename = os.path.abspath(filename)
        StreamHandler.__init__(self, open(filename, mode))
        self.baseFilename = filename
        self.mode = mode

    def close(self):
        self.stream.close()

    def reopen(self):
        self.close()
        self.stream = open(self.baseFilename, self.mode)


class NullHandler(Handler):
    """Handler that does nothing."""

    def emit(self, record):
        pass

    def handle(self, record):
        pass


class StartupHandler(Handler):
    """
    A handler which outputs messages to a stream but also buffers them until
    they can be flushed to a target handler.  Useful at startup before we can
    know that we can safely write to a config-specified handler.
    """
    def __init__(self, stream=None):
        Handler.__init__(self)
        if not stream:
            stream = sys.stderr
        self.stream = stream
        self.buffer = []

    def emit(self, record):
        try:
            self.buffer.append(record)
            msg = self.format(record)
            self.stream.write("%s\n" % msg)
            self.flush()
        except:
            self.handleError(record)

    def flush(self):
        self.stream.flush()

    def flushBufferTo(self, target):
        for record in self.buffer:
            target.handle(record)
        self.buffer = []
