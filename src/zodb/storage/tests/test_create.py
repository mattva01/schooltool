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

# Unit test for database creation

import os
import time
import unittest

from zodb.storage.base import BerkeleyConfig, berkeley_is_available
from zodb.storage.tests import bdbmixin
from zodb.storage.tests.base import DBHOME

if berkeley_is_available:
    from zodb.storage.bdbfull import BDBFullStorage



class TestMixin:
    def testDBHomeExists(self):
        self.failUnless(os.path.isdir(DBHOME))


class MinimalCreateTest(bdbmixin.MinimalTestBase, TestMixin):
    pass


class FullCreateTest(bdbmixin.FullTestBase, TestMixin):
    pass



class FullOpenExistingTest(bdbmixin.FullTestBase):
    def testOpenWithExistingVersions(self):
        version = 'test-version'
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=7, version=version)
        # Now close the current storage and re-open it
        self._storage.close()
        self._storage = self.ConcreteStorage(DBHOME)
        self.assertEqual(self._storage.modifiedInVersion(oid), version)

    def testOpenAddVersion(self):
        eq = self.assertEqual
        version1 = 'test-version'
        oid1 = self._storage.newObjectId()
        revid = self._dostore(oid1, data=7, version=version1)
        # Now close the current storage and re-open it
        self._storage.close()
        self._storage = self.ConcreteStorage(DBHOME)
        eq(self._storage.modifiedInVersion(oid1), version1)
        # Now create a 2nd version string, then close/reopen
        version2 = 'new-version'
        oid2 = self._storage.newObjectId()
        revid = self._dostore(oid2, data=8, version=version2)
        # Now close the current storage and re-open it
        self._storage.close()
        self._storage = self.ConcreteStorage(DBHOME)
        eq(self._storage.modifiedInVersion(oid1), version1)
        # Now create a 2nd version string, then close/reopen
        eq(self._storage.modifiedInVersion(oid2), version2)



class FullOpenCloseTest(bdbmixin.FullTestBase):
    level = 2

    def _mk_dbhome(self, dir):
        config = BerkeleyConfig
        config.interval = 10
        os.mkdir(dir)
        try:
            return self.ConcreteStorage(dir, config=config)
        except:
            self._zap_dbhome(dir)
            raise

    def testCloseWithCheckpointingThread(self):
        # All the interesting stuff happens in the setUp and tearDown
        time.sleep(20)



class OpenRecoveryTest(bdbmixin.FullTestBase):
    def open(self):
        self._storage = None

    def testOpenWithBogusConfig(self):
        class C: pass
        c = C()
        # This instance won't have the necessary attributes, so the creation
        # will fail.  We want to be sure that everything gets cleaned up
        # enough to fix that and create a proper storage.
        dir = self._envdir()
        self.assertRaises(AttributeError, BDBFullStorage, dir, config=c)
        s = BDBFullStorage(dir, config=self._config())
        s.close()



def test_suite():
    suite = unittest.TestSuite()
    if berkeley_is_available:
        suite.addTest(unittest.makeSuite(MinimalCreateTest))
        suite.addTest(unittest.makeSuite(FullCreateTest))
        suite.addTest(unittest.makeSuite(FullOpenExistingTest))
        suite.addTest(unittest.makeSuite(FullOpenCloseTest))
        suite.addTest(unittest.makeSuite(OpenRecoveryTest))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
