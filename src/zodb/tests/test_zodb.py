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
import os
import unittest
import tempfile

from zodb.db import DB
from zodb.storage.file import FileStorage
from zodb.utils import u64
from zodb.tests.undo import TransactionalUndoDB
from persistence.dict import PersistentDict
from transaction import get_transaction

_fsname = tempfile.mktemp() + ".fs"

class ExportImportTests:

    def duplicate(self, abort_it, dup_name):
        conn = self._db.open()
        try:
            root = conn.root()
            ob = root['test']
            self.assert_(len(ob) > 10, 'Insufficient test data')
            try:
                f = tempfile.TemporaryFile()
                ob._p_jar.exportFile(ob._p_oid, f)
                self.assert_(f.tell() > 0, 'Did not export correctly')
                f.seek(0)
                new_ob = ob._p_jar.importFile(f)
                root[dup_name] = new_ob
                f.close()
                if abort_it:
                    get_transaction().abort()
                else:
                    get_transaction().commit()
            except Exception, err:
                get_transaction().abort()
                raise
        finally:
            conn.close()

    def verify(self, abort_it, dup_name):
        get_transaction().begin()
        # Verify the duplicate.
        conn = self._db.open()
        try:
            root = conn.root()
            ob = root['test']
            try:
                ob2 = root[dup_name]
            except KeyError:
                if abort_it:
                    # Passed the test.
                    return
                else:
                    raise
            else:
                if abort_it:
                    oid = ob2._p_oid
                    if oid is not None:
                        oid = u64(oid)
                    print oid, ob2.__class__, ob2._p_state
                    print ob2
                    self.fail("Did not abort duplication")
            l1 = list(ob.items())
            l1.sort()
            l2 = list(ob2.items())
            l2.sort()
            l1 = [(k, v[0]) for k, v in l1]
            l2 = [(k, v[0]) for k, v in l2]
            self.assertEqual(l1, l2, 'Duplicate did not match')
            self.assert_(ob._p_oid != ob2._p_oid, 'Did not duplicate')
            self.assertEqual(ob._p_jar, ob2._p_jar, 'Not same connection')
            oids = {}
            for v in ob.values():
                oids[v._p_oid] = 1
            for v in ob2.values():
                self.assert_(v._p_oid not in oids,
                             'Did not fully separate duplicate from original')
            get_transaction().commit()
        finally:
            conn.close()

    def checkDuplicate(self, abort_it=False, dup_name='test_duplicate'):
        self.populate()
        get_transaction().begin()
        get_transaction().note('duplication')
        self.duplicate(abort_it, dup_name)
        self.verify(abort_it, dup_name)

    def checkDuplicateAborted(self):
        self.checkDuplicate(abort_it=True, dup_name='test_duplicate_aborted')

class ZODBTests(ExportImportTests, TransactionalUndoDB,
                unittest.TestCase):

    def setUp(self):
        self._db = DB(FileStorage(_fsname, create=True))
        self._conn = self._db.open()
        self._root = self._conn.root()

    def populate(self):
        get_transaction().begin()
        conn = self._db.open()
        root = conn.root()
        root['test'] = pm = PersistentDict()
        for n in range(100):
            pm[n] = PersistentDict({0: 100 - n})
        get_transaction().note('created test data')
        get_transaction().commit()
        conn.close()

    def checkModifyGhost(self):
        self.populate()
        root = self._db.open().root()
        o = root["test"][5]
        o._p_activate()
        o._p_deactivate()
        o.anattr = "anattr"
        self.assert_(o._p_changed)
        get_transaction().commit()
        self.assert_(not o._p_changed)
        o._p_deactivate()
        self.assertEqual(o.anattr, "anattr")

    # need a test that loads an object with references to other
    # objects so that it creates ghosts.

    def tearDown(self):
        self._db.close()
        for ext in '', '.old', '.tmp', '.lock', '.index':
            path = _fsname + ext
            if os.path.exists(path):
                os.remove(path)

def test_suite():
    return unittest.makeSuite(ZODBTests, 'check')

if __name__=='__main__':
    unittest.TextTestRunner().run(test_suite())
