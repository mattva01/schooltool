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
"""High-level tests of the transaction interface"""

import os
import tempfile
import unittest

from transaction import get_transaction

import zodb
from zodb.db import DB
from zodb.storage.file import FileStorage
from zodb.storage.tests.minpo import MinPO
from zodb.interfaces import RollbackError

class TransactionTestBase(unittest.TestCase):

    def setUp(self):
        self.fs_path = tempfile.mktemp()
        self.fs = FileStorage(self.fs_path)
        db = DB(self.fs)
        conn = db.open()
        self.root = conn.root()

    def tearDown(self):
        get_transaction().abort()
        self.fs.close()
        self.fs.cleanup()

class BasicTests:

    def testSingleCommit(self, subtrans=None):
        self.root["a"] = MinPO("a")
        if subtrans:
            get_transaction().savepoint()
        else:
            get_transaction().commit()
        self.assertEqual(self.root["a"].value, "a")

    def testMultipleCommits(self, subtrans=None):
        a = self.root["a"] = MinPO("a")
        get_transaction().commit()
        a.extra_attr = MinPO("b")
        if subtrans:
            get_transaction().savepoint()
        else:
            get_transaction().commit()
        del a
        self.assertEqual(self.root["a"].value, "a")
        self.assertEqual(self.root["a"].extra_attr, MinPO("b"))

    def testCommitAndAbort(self, subtrans=None):
        a = self.root["a"] = MinPO("a")
        if subtrans:
            get_transaction().savepoint()
        else:
            get_transaction().commit()
        a.extra_attr = MinPO("b")
        get_transaction().abort()
        del a
        if subtrans:
            self.assert_("a" not in self.root)
        else:
            self.assertEqual(self.root["a"].value, "a")
            self.assert_(not hasattr(self.root["a"], 'extra_attr'))

class SubtransTests(BasicTests):

    def wrap_test(self, klass, meth_name):
        unbound_method = getattr(klass, meth_name)
        unbound_method(self, 1)
        get_transaction().commit()

    testSubSingleCommit = lambda self:\
                           self.wrap_test(BasicTests, "testSingleCommit")

    testSubMultipleCommits = lambda self:\
                              self.wrap_test(BasicTests,
                                             "testMultipleCommits")

    testSubCommitAndAbort = lambda self:\
                             self.wrap_test(BasicTests,
                                            "testCommitAndAbort")

class AllTests(TransactionTestBase, SubtransTests):

    def testSavepointAndRollback(self):
        # XXX Should change savepoint() so that you restore to the state
        # at the savepoint() not at the last txn activity before the
        # savepoint().
        self.root["a"] = MinPO()
        rb1 = get_transaction().savepoint()
        self.root["b"] = MinPO()
        rb2 = get_transaction().savepoint()
        self.assertEqual(len(self.root), 2)
        self.assert_("a" in self.root)
        self.assert_("b" in self.root)

        rb2.rollback()
        self.assertEqual(len(self.root), 1)
        self.assert_("a" in self.root)
        self.assert_("b" not in self.root)

        self.root["c"] = MinPO()
        rb3 = get_transaction().savepoint()
        self.root["d"] = MinPO()
        rb4 = get_transaction().savepoint()
        rb3.rollback()
        self.assertRaises(RollbackError, rb4.rollback)

        self.root["e"] = MinPO()
        rb5 = get_transaction().savepoint()
        self.root["f"] = MinPO()
        rb6 = get_transaction().savepoint()
        self.root["g"] = MinPO()
        rb6.rollback()
        self.root["h"] = MinPO()
        self.assertEqual(len(self.root), 3)
        for name in "a", "e", "h":
            self.assert_(name in self.root)
        for name in "b", "c", "d", "f", "g":
            self.assert_(name not in self.root)

def test_suite():
    return unittest.makeSuite(AllTests)

def main():
    tests = test_suite()
    runner = unittest.TextTestRunner()
    runner.run(tests)

if __name__ == "__main__":
    main()
