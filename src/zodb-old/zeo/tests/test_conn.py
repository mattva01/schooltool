##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Test setup for ZEO connection logic.

The actual tests are in ConnectionTests.py; this file provides the
platform-dependent scaffolding.
"""

import unittest

from zodb.zeo.tests.connection \
     import ConnectionTests, ReconnectionTests, TimeoutTests
from zodb.zeo.tests.invalid import InvalidationTests
from zodb.storage.base import berkeley_is_available

class FileStorageConfig:
    def getConfig(self, path, create, read_only):
        return """\
        <filestorage 1>
        path %s
        create %s
        read-only %s
        </filestorage>""" % (path,
                             create and 'yes' or 'no',
                             read_only and 'yes' or 'no')

class BerkeleyStorageConfig:
    def getConfig(self, path, create, read_only):
        return """\
        <fullstorage 1>
        name %s
        read-only %s
        </fullstorage>""" % (path, read_only and "yes" or "no")

class MappingStorageConfig:
    def getConfig(self, path, create, read_only):
        return """<mappingstorage 1/>"""


class FileStorageConnectionTests(
    FileStorageConfig,
    ConnectionTests,
    InvalidationTests
    ):
    """FileStorage-specific connection tests."""
    level = 2

class FileStorageReconnectionTests(
    FileStorageConfig,
    ReconnectionTests
    ):
    """FileStorage-specific re-connection tests."""
    # Run this at level 1 because MappingStorage can't do reconnection tests
    level = 1

class FileStorageTimeoutTests(
    FileStorageConfig,
    TimeoutTests
    ):
    level = 2


class BDBConnectionTests(
    BerkeleyStorageConfig,
    ConnectionTests,
    InvalidationTests
    ):
    """Berkeley storage connection tests."""
    level = 2

class BDBReconnectionTests(
    BerkeleyStorageConfig,
    ReconnectionTests
    ):
    """Berkeley storage re-connection tests."""
    level = 2

class BDBTimeoutTests(
    BerkeleyStorageConfig,
    TimeoutTests
    ):
    level = 2


class MappingStorageConnectionTests(
    MappingStorageConfig,
    ConnectionTests
    ):
    """Mapping storage connection tests."""
    level = 1

# The ReconnectionTests can't work with MappingStorage because it's only an
# in-memory storage and has no persistent state.

class MappingStorageTimeoutTests(
    MappingStorageConfig,
    TimeoutTests
    ):
    level = 1



test_classes = [FileStorageConnectionTests,
                FileStorageReconnectionTests,
                FileStorageTimeoutTests,
                MappingStorageConnectionTests,
                MappingStorageTimeoutTests]

if berkeley_is_available:
    test_classes.append(BDBConnectionTests)
    test_classes.append(BDBReconnectionTests)
    test_classes.append(BDBTimeoutTests)


def test_suite():
    suite = unittest.TestSuite()
    for klass in test_classes:
        sub = unittest.makeSuite(klass)
        suite.addTest(sub)
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
