##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""Create copy of a data record."""

from zodb.interfaces import MAXTID, ZERO, UndoError
from zodb.utils import p64, u64
from zodb.storage.file.format import FileStorageFormatter, DataHeader
from zodb.storage.file.format \
     import TRANS_HDR, TRANS_HDR_LEN, DATA_HDR_LEN, DATA_VERSION_HDR_LEN

class DataCopier(FileStorageFormatter):
    """Mixin class for copying transactions into a storage.

    The restore() and pack() methods share a need to copy data records
    and update pointers to data in earlier transaction records.  This
    class provides the shared logic.

    The mixin extends the FileStorageFormatter with a copy() method.
    It also requires that the concrete class provides the following
    attributes:

    _file -- file with earlier destination data
    _tfile -- destination file for copied data
    _pack_time -- p64() representation of latest pack time
    _pos -- file pos of destination transaction
    _tindex -- maps oid to data record file pos
    _tvindex -- maps version name to data record file pos

    _tindex and _tvindex are updated by copy().

    The copy() method does not do any locking.
    """

    def _txn_find(self, tid, stop_at_pack):
        # _pos always points just past the last transaction
        pos = self._pos
        while pos > 1024:
            self._file.seek(pos - 8)
            pos = pos - u64(self._file.read(8)) - 8
            self._file.seek(pos)
            h = self._file.read(TRANS_HDR_LEN)
            _tid = h[:8]
            if _tid == tid:
                return pos
            if stop_at_pack:
                # check the status field of the transaction header
                # XXX _pack_time seems to be either ZERO or None
                if h[16] == 'p' or _tid < self._pack_time:
                    break
        raise UndoError(None, "Invalid transaction id")

    def _data_find(self, tpos, oid, data):
        # Return backpointer to oid in data record for in transaction at tpos.
        # It should contain a pickle identical to data. Returns 0 on failure.
        # Must call with lock held.
        h = self._read_txn_header(tpos)
        tend = tpos + h.tlen
        pos = self._file.tell()
        while pos < tend:
            h = self._read_data_header(pos)
            if h.oid == oid:
                # Read past any references data
                self._file.read(h.nrefs * 8)
                # Make sure this looks like the right data record
                if h.plen == 0:
                    # This is also a backpointer.  Gotta trust it.
                    return pos
                if h.plen != len(data):
                    # The expected data doesn't match what's in the
                    # backpointer.  Something is wrong.
                    error("Mismatch between data and backpointer at %d", pos)
                    return 0
                _data = self._file.read(h.plen)
                if data != _data:
                    return 0
                return pos
            pos += h.recordlen()
        return 0
    
    def _restore_pnv(self, oid, prev, version, bp):
        # Find a valid pnv (previous non-version) pointer for this version.

        # If there is no previous record, there can't be a pnv.
        if not prev:
            return None

        pnv = None
        h = self._read_data_header(prev, oid)
        # If the previous record is for a version, it must have
        # a valid pnv.
        if h.version:
            return h.pnv
        elif bp:
            # XXX Not sure the following is always true:
            # The previous record is not for this version, yet we
            # have a backpointer to it.  The current record must
            # be an undo of an abort or commit, so the backpointer
            # must be to a version record with a pnv.
            h2 = self._read_data_header(bp, oid)
            if h2.version:
                return h2.pnv
            else:
                warn("restore could not find previous non-version data "
                     "at %d or %d", prev, bp)
                return None

    def _resolve_backpointer(self, prev_txn, oid, data):
        prev_pos = 0
        if prev_txn is not None:
            prev_txn_pos = self._txn_find(prev_txn, 0)
            if prev_txn_pos:
                prev_pos = self._data_find(prev_txn_pos, oid, data)
        return prev_pos

    def copy(self, oid, serial, data, refs, version, prev_txn,
             txnpos, datapos):
        prev_pos = self._resolve_backpointer(prev_txn, oid, data)
        old = self._index.get(oid, 0)
        # Calculate the pos the record will have in the storage.
        here = datapos
        # And update the temp file index
        self._tindex[oid] = here
        if prev_pos:
            # If there is a valid prev_pos, don't write data.
            data = None
        if data is None:
            dlen = 0
            refs = []
        else:
            dlen = len(data)
        # Write the recovery data record
        h = DataHeader(oid, serial, old, txnpos, len(version), len(refs), dlen)
        if version:
            h.version = version
            pnv = self._restore_pnv(oid, old, version, prev_pos)
            if pnv is not None:
                h.pnv = pnv
            else:
                h.pnv = old
            # Link to the last record for this version
            h.vprev = self._tvindex.get(version, 0)
            if not h.vprev:
                h.vprev = self._vindex.get(version, 0)
            self._tvindex[version] = here

        self._tfile.write(h.asString())
        self._tfile.write(''.join(refs))
        # Write the data or a backpointer
        if data is None:
            if prev_pos:
                self._tfile.write(p64(prev_pos))
            else:
                # Write a zero backpointer, which indicates an
                # un-creation transaction.
                self._tfile.write(ZERO)
        else:
            self._tfile.write(data)
