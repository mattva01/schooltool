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
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import zodb.storage.mapping
import os, unittest

from zodb.storage.tests import base, basic, synchronization

class MappingStorageTests(base.StorageTestBase,
                          basic.BasicStorage,
                          synchronization.SynchronizedStorage,
                          ):

    def setUp(self):
        self._storage = zodb.storage.mapping.MappingStorage()

    def tearDown(self):
        self._storage.close()

    def testDatabaseVersionPersistent(self):
        # This can't possibly work
        pass


def test_suite():
    suite = unittest.makeSuite(MappingStorageTests)
    return suite




if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
