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
"""Support for database export and import."""

from zodb.interfaces import ExportError
from zodb.utils import p64, u64, Set
from zodb.serialize import findrefs, ObjectCopier
from transaction import get_transaction

from tempfile import TemporaryFile

export_end_marker = '\377' * 16

class ExportImport:
    # a mixin for use with ZODB.Connection.Connection

    __hooks = None

    def exportFile(self, oid, file=None):
        if file is None:
            file = TemporaryFile()
        elif isinstance(file, str):
            file = open(file, 'w+b')
        file.write('ZEXP')
        oids = [oid]
        done_oids = Set()
        while oids:
            oid = oids.pop(0)
            if oid in done_oids:
                continue
            done_oids.add(oid)
            try:
                p, serial = self._storage.load(oid, self._version)
            except:
                # XXX what exception is expected?
                pass # Ick, a broken reference
            else:
                oids += findrefs(p)
                file.write(oid)
                file.write(p64(len(p)))
                file.write(p)
        file.write(export_end_marker)
        return file

    def importFile(self, file, clue=None, customImporters=None):
        # This is tricky, because we need to work in a transaction!
        # XXX I think this needs to work in a transaction, because it
        # needs to write pickles into the storage, which only allows
        # store() calls between tpc_begin() and tpc_vote().

        if isinstance(file, str):
            file = open(file,'rb')
        magic = file.read(4)

        if magic != 'ZEXP':
            if customImporters is not None and customImporters.has_key(magic):
                file.seek(0)
                return customImporters[magic](self, file, clue)
            raise ExportError("Invalid export header")

        t = get_transaction()
        if clue is not None:
            t.note(clue)

        L = []
        if self.__hooks is None:
            self.__hooks = []
        self.__hooks.append((file, L))
        t.join(self)
        t.savepoint()
        # Return the root imported object.
        if L:
            return self.get(L[0])
        else:
            return None

    def importHook(self, txn):
        if self.__hooks is None:
            return
        for file, L in self.__hooks:
            self._importDuringCommit(txn, file, L)
        del self.__hooks

    def _importDuringCommit(self, txn, file, return_oid_list):
        """Invoked by the transaction manager mid commit.

        Appends one item, the OID of the first object created,
        to return_oid_list.
        """
        copier = ObjectCopier(self, self._storage, self._created)

        while True:
            h = file.read(16)
            if h == export_end_marker:
                break
            if len(h) != 16:
                raise ExportError("Truncated export file")
            l = u64(h[8:16])
            p = file.read(l)
            if len(p) != l:
                raise ExportError("Truncated export file")

            # XXX I think it would be better if copier.copy()
            # returned an oid and a new pickle so that this logic
            # wasn't smeared across two modules.
            oid = h[:8]
            new_ref = copier.oids.get(oid)
            if new_ref is None:
                newObjectId = self._storage.newObjectId()
                copier.oids[oid] = newObjectId, None
                return_oid_list.append(newObjectId)
                self._created.add(newObjectId)
            else:
                newObjectId = new_ref[0]

            data, refs = copier.copy(p)
            self._storage.store(newObjectId, None, data, refs,
                                self._version, txn)

        copier.close()
