##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors.
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

# Test some simple ZODB level stuff common to both the Minimal and Full
# storages, like transaction aborts and commits, changing objects, etc.
# Doesn't test undo, versions, or packing.

import time
import unittest

from transaction import get_transaction
from persistence.dict import PersistentDict

from zodb.storage.base import berkeley_is_available
from zodb.storage.tests.base import ZODBTestBase



class CommitAndRead:
    def testCommit(self):
        self.failUnless(not self._root)
        names = self._root['names'] = PersistentDict()
        names['Warsaw'] = 'Barry'
        names['Hylton'] = 'Jeremy'
        get_transaction().commit()

    def testReadAfterCommit(self):
        eq = self.assertEqual
        self.testCommit()
        names = self._root['names']
        eq(names['Warsaw'], 'Barry')
        eq(names['Hylton'], 'Jeremy')
        self.failUnless(names.get('Drake') is None)

    def testAbortAfterRead(self):
        self.testReadAfterCommit()
        names = self._root['names']
        names['Drake'] = 'Fred'
        get_transaction().abort()

    def testReadAfterAbort(self):
        self.testAbortAfterRead()
        names = self._root['names']
        self.failUnless(names.get('Drake') is None)

    def testChangingCommits(self):
        self.testReadAfterAbort()
        now = time.time()
        # Make sure the last timestamp was more than 3 seconds ago
        timestamp = self._root.get('timestamp')
        if timestamp is None:
            timestamp = self._root['timestamp'] = 0
            get_transaction().commit()
        self.failUnless(now > timestamp + 3)
        self._root['timestamp'] = now
        time.sleep(3)



class MinimalCommitAndRead(ZODBTestBase, CommitAndRead):
    from zodb.storage.bdbminimal import BDBMinimalStorage
    ConcreteStorage = BDBMinimalStorage


class FullCommitAndRead(ZODBTestBase, CommitAndRead):
    from zodb.storage.bdbfull import BDBFullStorage
    ConcreteStorage = BDBFullStorage



def test_suite():
    suite = unittest.TestSuite()
    if berkeley_is_available:
        suite.addTest(unittest.makeSuite(MinimalCommitAndRead))
        suite.addTest(unittest.makeSuite(FullCommitAndRead))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
