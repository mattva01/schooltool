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
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from zodb.storage.base import ZERO
from zodb.storage.interfaces import ReadOnlyError, IUndoStorage
from zodb.ztransaction import Transaction


class ReadOnlyStorage:
    def _create_data(self):
        # test a read-only storage that already has some data
        self.oids = {}
        for i in range(10):
            oid = self._storage.newObjectId()
            revid = self._dostore(oid)
            self.oids[oid] = revid

    def _make_readonly(self):
        self._storage.close()
        self.open(read_only=True)
        self.failUnless(self._storage.isReadOnly())

    def testReadMethods(self):
        eq = self.assertEqual
        unless = self.failUnless
        self._create_data()
        self._make_readonly()
        # XXX not going to bother checking all read methods
        for oid in self.oids.keys():
            data, revid = self._storage.load(oid, '')
            eq(revid, self.oids[oid])
            unless(not self._storage.modifiedInVersion(oid))
            if IUndoStorage.isImplementedBy(self._storage):
                _data = self._storage.loadSerial(oid, revid)
                eq(data, _data)

    def testWriteMethods(self):
        raises = self.assertRaises
        self._make_readonly()
        t = Transaction()
        raises(ReadOnlyError, self._storage.newObjectId)
        raises(ReadOnlyError, self._storage.tpcBegin, t)
        raises(ReadOnlyError, self._storage.abortVersion, '', t)
        raises(ReadOnlyError, self._storage.commitVersion, '', '', t)
        raises(ReadOnlyError, self._storage.store, ZERO, None, '', '', '', t)
        if IUndoStorage.isImplementedBy(self._storage):
            raises(ReadOnlyError, self._storage.undo, ZERO, t)
