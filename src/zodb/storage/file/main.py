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
"""File-based ZODB storage

$Id: main.py,v 1.9 2003/07/10 17:41:09 bwarsaw Exp $
"""

from __future__ import generators

import os
import sys
import errno
import base64
import struct
import logging
from struct import pack, unpack
from cPickle import Pickler, Unpickler, loads

try:
    from posix import fsync
except:
    fsync = None

from zope.interface import implements

from zodb.storage.base import BaseStorage, splitrefs
from zodb import conflict
from zodb.interfaces import *
from zodb.timestamp import TimeStamp, newTimeStamp, timeStampFromTime
from zodb.lockfile import LockFile
from zodb.utils import p64, u64, cp
from zodb.storage.file.index import fsIndex
from zodb.storage.interfaces import *

from zodb.storage.file.copy import DataCopier
from zodb.storage.file.errors import *
from zodb.storage.file.format \
     import FileStorageFormatter, DataHeader, TxnHeader
from zodb.storage.file.format import TRANS_HDR, TRANS_HDR_LEN, DATA_HDR
from zodb.storage.file.format import DATA_HDR_LEN, DATA_VERSION_HDR_LEN
from zodb.storage.file.pack import FileStoragePacker

logger = logging.getLogger("zodb.storage.file")

warn = logger.warn
error = logger.error

def panic(message, *data):
    logger.critical(message, *data)
    raise CorruptedTransactionError(message % data)

class TxnTempFile(FileStorageFormatter):
    """Helper class used in conjunction with _tfile of FileStorage."""

    def __init__(self, afile):
        self._file = afile

class FileStorage(BaseStorage, DataCopier):
    implements(IStorage, IUndoStorage, IVersionStorage)

    def __init__(self, file_name, create=0, read_only=0, stop=None,
                 quota=None):

        # This check was removed from zodb3, because old versions of
        # python could lie if they didn't have large file support.
        if not os.path.exists(file_name):
            create = 1

        if read_only:
            self._is_read_only = 1
            if create:
                raise ValueError, "can't create a read-only file"
        elif stop is not None:
            raise ValueError("time-travel is only supported "
                             "in read-only mode")

        if stop is None:
            stop=MAXTID

        self._file_name = file_name
        super(FileStorage, self).__init__(file_name)
        self._initIndex()
        if not read_only:
            self._lock()
            self._tfile = open(file_name + '.tmp', 'w+b')
            self._tfmt = TxnTempFile(self._tfile)
        else:
            self._tfile = None

        self._file = None
        if not create:
            try:
                self._file = open(file_name, read_only and 'rb' or 'r+b')
            except IOError, exc:
                if exc.errno == errno.EFBIG:
                    # The file is too big to open.  Fail visibly.
                    raise
                if exc.errno == errno.ENOENT:
                    # The file doesn't exist.  Create it.
                    create = 1
                # If something else went wrong, it's hard to guess
                # what the problem was.  If the file does not exist,
                # create it.  Otherwise, fail.
                if os.path.exists(file_name):
                    raise
                else:
                    create = 1

        if self._file is None and create:
            if os.path.exists(file_name):
                os.remove(file_name)
                self._clear_index()
            self._file = open(file_name, 'w+b')
            self._write_metadata()

        self._conflict = conflict.ConflictResolver(self)
        r = self._restore_index()
        if r is not None:
            index, vindex, start, maxoid, ltid = r
            self._initIndex(index, vindex)
            self._pos, self._oid, tid = self._read_index(
                self._index, self._vindex, self._tindex, stop, ltid=ltid,
                start=start, maxoid=maxoid, read_only=read_only)
        else:
            self._pos, self._oid, tid = self._read_index(
                self._index, self._vindex, self._tindex, stop,
                read_only=read_only)
        self._ltid = tid
        # The packing boolean is used by undo to prevent undo during
        # a pack.  The _pack_time variable is set to a timestamp during
        # a pack so that undoLog() / undoInfo() don't return txns
        # that occurred during the pack time.
        self._packing = False
        self._pack_time = None

        # self._pos should always point just past the last
        # transaction.  During 2PC, data is written after _pos.
        # invariant is restored at tpc_abort() or tpc_finish().

        if tid is not None:
            self._ts = tid = TimeStamp(tid)
            t = newTimeStamp()
            if tid > t:
                warn("%s Database records in the future", file_name);
                if tid.timeTime() - t.timeTime() > 86400*30:
                    # a month in the future? This is bogus, use current time
                    self._ts = t

        self._quota = quota

    def _lock(self):
        self._lock_file = LockFile(self._name + '.lock')

    def _initIndex(self, index=None, vindex=None, tindex=None, tvindex=None):
        self._index = index or fsIndex()
        self._vindex = vindex or {}
        self._tindex = tindex or {}
        self._tvindex = tvindex or {}

    def _save_index(self):
        """Write the database index to a file to support quick startup."""

        index_name = self._name + '.index'
        tmp_name = index_name + '.index_tmp'

        f = open(tmp_name,'wb')
        p = Pickler(f,1)
        info = {'index': self._index, 'pos': self._pos,
                'oid': self._oid, 'vindex': self._vindex}

        p.dump(info)
        f.flush()
        f.close()
        try:
            try:
                os.remove(index_name)
            except OSError:
                pass
            os.rename(tmp_name, index_name)
        except:
            pass

    def _clear_index(self):
        index_name = self._name + '.index'
        if os.path.exists(index_name):
            try:
                os.remove(index_name)
            except OSError:
                pass

    def _restore_index(self):
        """Load database index to support quick startup."""
        try:
            f = open("%s.index" % self._name, 'rb')
        except:
            return None

        p = Unpickler(f)
        try:
            info = p.load()
        except:
            exc, err = sys.exc_info()[:2]
            warn("Failed to load database index: %s: %s", exc, err)
            return None
        index = info.get('index')
        vindex = info.get('vindex')
        pos = info.get('pos')
        oid = info.get('oid')
        if index is None or pos is None or oid is None or vindex is None:
            return None

        if pos > self._metadata_size: # otherwise storage is empty
            # Get the last transaction
            self._file.seek(pos - 8)
            tl = u64(self._file.read(8))
            pos -= tl + 8
            self._file.seek(pos)
            tid = self._file.read(8)
        else:
            tid = None

        return index, vindex, pos, oid, tid

    def close(self):
        self._file.close()
        if hasattr(self, '_lock_file'):
            self._lock_file.close()
        if self._tfile:
            self._tfile.close()
        try:
            self._save_index()
        except:
            logger.warn("Error saving storage index",
                        exc_info=sys.exc_info())
            pass # We don't care if this fails.

    def setVersion(self, version):
        self._version = version
        if not self._is_read_only:
            self._write_metadata()

    def abortVersion(self, src, transaction):
        return self.commitVersion(src, '', transaction, abort=True)

    def commitVersion(self, src, dest, transaction, abort=False):
        # We are going to commit by simply storing back pointers.
        if self._is_read_only:
            raise ReadOnlyError()
        if not (src and isinstance(src, str) and isinstance(dest, str)):
            raise VersionCommitError('Invalid source version')

        if src == dest:
            raise VersionCommitError(
                "Can't commit to same version: %s" % repr(src))

        if dest and abort:
            raise VersionCommitError(
                "Internal error, can't abort to a version")

        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)

        self._lock_acquire()
        try:
            return self._commitVersion(src, dest, transaction, abort)
        finally:
            self._lock_release()

    def _commitVersion(self, src, dest, transaction, abort=False):
        # call after checking arguments and acquiring lock
        srcpos = self._vindex.get(src, 0)
        spos = p64(srcpos)
        # middle holds bytes 16:38 of a data record:
        #    pos of transaction, len of version name, data length, nrefs
        #    commit version never writes data, so data length and nrefs are
        #    always 0
        middle = struct.pack(">QHIQ", self._pos, len(dest), 0, 0)

        # recsize is the total size of a data record written by
        # commit version.  The var here stores the location of the
        # current data record.  here is incremented by recsize
        # each time we write an object record.

        # Add 8 to header size to account for backpointer.
        if dest:
            sd = p64(self._vindex.get(dest, 0))
            recsize = DATA_VERSION_HDR_LEN + 8 + len(dest)
        else:
            sd = ''
            recsize = DATA_HDR_LEN + 8

        here = self._pos + self._tfile.tell() + self._thl
        oids = []
        current_oids = {}
        if not abort:
            newserial = self._serial

        while srcpos:
            h = self._read_data_header(srcpos)
            if abort:
                # If we are aborting, the serialno in the new data
                # record should be the same as the serialno in the last
                # non-version data record.
                # XXX This might be the only time that the serialno
                # of a data record does not match the transaction id.
                self._file.seek(h.pnv)
                h_pnv = self._read_data_header(srcpos)
                newserial = h_pnv.serial

            if self._index.get(h.oid) == srcpos:
                # This is a current record!
                self._tindex[h.oid] = here
                oids.append(h.oid)
                self._tfile.write(h.oid + newserial + spos + middle)
                if dest:
                    self._tvindex[dest] = here
                    self._tfile.write(p64(h.pnv) + sd + dest)
                    sd = p64(here)

                self._tfile.write(abort and p64(h.pnv) or spos)
                # data backpointer to src data
                here += recsize

                current_oids[h.oid] = 1
            else:
                # XXX I don't understand this branch.  --jeremy
                # Hm.  This is a non-current record.  Is there a
                # current record for this oid?
                if not current_oids.has_key(h.oid):
                    break

            srcpos = h.vprev
            spos = p64(srcpos)
        return oids

    def load(self, oid, version=''):
        self._lock_acquire()
        try:
            try:
                pos = self._index[oid]
            except KeyError:
                raise POSKeyError(oid)
            h = self._read_data_header(pos, oid)
            if h.version and h.version != version:
                return self._loadBack(oid, h.pnv)

            # If we get here, then either this was not a version record,
            # or we've already read past the version data!  Read past any
            # references data first.
            self._file.read(h.nrefs * 8)

            if h.plen:
                return self._file.read(h.plen), h.serial
            # We use the current serial, since that is the one that
            # will get checked when we store.
            return self._loadBack(oid, h.back)[0], h.serial
        finally:
            self._lock_release()

    def loadSerial(self, oid, serial):
        self._lock_acquire()
        try:
            try:
                pos = self._index[oid]
            except KeyError:
                raise POSKeyError(oid)
            while 1:
                h = self._read_data_header(pos, oid)
                if h.serial == serial:
                    break
                # Keep looking for serial
                pos = h.prev
                if not pos:
                    # XXX serial?
                    raise POSKeyError(serial)
                continue

            # Read past any references data
            self._file.read(h.nrefs * 8)
            if h.plen:
                return self._file.read(h.plen)
            return self._loadBack(oid, h.back)[0]
        finally:
            self._lock_release()

    def modifiedInVersion(self, oid):
        self._lock_acquire()
        try:
            try:
                pos = self._index[oid]
            except KeyError:
                raise POSKeyError(oid)
            h = self._read_data_header(pos, oid)
            return h.version
        finally:
            self._lock_release()

    def store(self, oid, serial, data, refs, version, transaction):
        if self._is_read_only:
            raise ReadOnlyError()
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)

        self._lock_acquire()
        try:
            old = self._index.get(oid, 0)
            pnv = None
            if old:
                h = self._read_data_header(old)
                if h.version:
                    if version != h.version:
                        raise VersionLockError(oid, h.version)
                    pnv = h.pnv

                if serial != h.serial:
                    data, refs = self._conflict.resolve(
                        oid, h.serial, serial, data)

            pos = self._pos
            here = pos + self._tfile.tell() + self._thl
            self._tindex[oid] = here
            new = DataHeader(oid, self._serial, old, pos, len(version),
                             len(refs), len(data))
            if version:
                # Link to last record for this version:
                pv = (self._tvindex.get(version, 0)
                      or self._vindex.get(version, 0))
                if pnv is None:
                    pnv = old
                new.setVersion(version, pnv, pv)
                self._tvindex[version] = here
                
            self._tfile.write(new.asString())
            self._tfile.write(''.join(refs))
            self._tfile.write(data)

            if self._quota is not None and here > quota:
                raise FileStorageQuotaError("storage quota exceeded")

            if old and serial != h.serial:
                return conflict.ResolvedSerial
            else:
                return self._serial

        finally:
            self._lock_release()

    def restore(self, oid, serial, data, refs, version, prev_txn, transaction):
        # A lot like store() but without all the consistency checks.  This
        # should only be used when we /know/ the data is good, hence the
        # method name.  While the signature looks like store() there are some
        # differences:
        #
        # - serial is the serial number of /this/ revision, not of the
        #   previous revision.  It is used instead of self._serial, which is
        #   ignored.
        #
        # - Nothing is returned
        #
        # - data can be None, which indicates a George Bailey object
        #   (i.e. one who's creation has been transactionally undone).
        #
        # prev_txn is a backpointer.  In the original database, it's possible
        # that the data was actually living in a previous transaction.  This
        # can happen for transactional undo and other operations, and is used
        # as a space saving optimization.  Under some circumstances the
        # prev_txn may not actually exist in the target database (i.e. self)
        # for example, if it's been packed away.  In that case, the prev_txn
        # should be considered just a hint, and is ignored if the transaction
        # doesn't exist.
        if self._is_read_only:
            raise ReadOnlyError()
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)

        self._lock_acquire()
        try:
            offset = self._pos + self._tfile.tell() + self._thl
            self.copy(oid, serial, data, refs, version, prev_txn,
                      self._pos, offset)
        finally:
            self._lock_release()

    def _clear_temp(self):
        self._tindex.clear()
        self._tvindex.clear()
        if self._tfile is not None:
            self._tfile.seek(0)

    def _begin(self, tid):
        self._nextpos = 0
        u, d, e = self._ude
        self._thl = TRANS_HDR_LEN + len(u) + len(d) + len(e)
        if self._thl > 65535:
            # one of u, d, or e may be > 65535
            # We have to check lengths here because struct.pack
            # doesn't raise an exception on overflow!
            if len(u) > 65535:
                raise FileStorageError('user name too long')
            if len(d) > 65535:
                raise FileStorageError('description too long')
            if len(e) > 65535:
                raise FileStorageError('too much extension data')


    def tpcVote(self, transaction):
        self._lock_acquire()
        try:
            if transaction is not self._transaction:
                return
            dlen = self._tfile.tell()
            if not dlen:
                return # No data in this trans
            self._tfile.seek(0)
            user, desc, ext = self._ude
            self._file.seek(self._pos)
            tl = self._thl + dlen
            try:
                # Note that we use a status of 'c', for checkpoint.
                # If this flag isn't cleared, anything after this is
                # suspect.
                h = TxnHeader(self._serial, tl, "c", len(user),
                              len(desc), len(ext))
                h.user = user
                h.descr = desc
                h.ext = ext
                self._file.write(h.asString())
                cp(self._tfile, self._file, dlen)
                self._file.write(p64(tl))
                self._file.flush()
            except:
                # Hm, an error occured writing out the data. Maybe the
                # disk is full. We don't want any turd at the end.
                self._file.truncate(self._pos)
                raise
            self._nextpos = self._pos + (tl + 8)
        finally:
            self._lock_release()

    def _finish(self, tid):
        nextpos = self._nextpos
        if nextpos:
            # Clear the checkpoint flag
            self._file.seek(self._pos + 16)
            self._file.write(self._tstatus)
            self._file.flush()

            if fsync is not None:
                fsync(self._file.fileno())

            self._pos = nextpos

            self._index.update(self._tindex)
            self._vindex.update(self._tvindex)
        self._ltid = tid

    def _abort(self):
        if self._nextpos:
            self._file.truncate(self._pos)
            self._nextpos=0

    def getSerial(self, oid):
        self._lock_acquire()
        try:
            return self._getSerial(oid, self._index[oid])
        finally:
            self._lock_release()

    def _getSerial(self, oid, pos):
        self._file.seek(pos)
        h = self._file.read(16)
        assert oid == h[:8]
        return h[8:]

    def _getVersion(self, oid, pos):
        # Return version and non-version pointer from oid record at pos.
        h = self._read_data_header(pos)
        if h.oid != oid:
            raise ValueError("invalid previous pointer")
        if h.version:
            return h.version, p64(h.pnv)
        else:
            return "", None

    def _undo_get_data(self, oid, pos, tpos):
        """Return the serial, data pointer, data, and version for the oid
        record at pos"""
        if tpos:
            pos = tpos - self._pos - self._thl
            tpos = self._tfile.tell()
            h = self._tfmt._read_data_header(pos)
            afile = self._tfile
        else:
            h = self._read_data_header(pos)
            afile = self._file
        if h.oid != oid:
            raise UndoError(oid, "Invalid undo transaction id")

        refsdata = afile.read(h.nrefs * 8)
        if h.plen:
            data = afile.read(h.plen)
        else:
            data = ''
            pos = h.back

        if tpos:
            # Restore temp file to end
            self._tfile.seek(tpos)

        return h.serial, pos, data, h.version

    def _undo_record(self, h, pos):
        """Get the undo information for a data record

        Return a 6-tuple consisting of a pickle, references, data
        pointer, version, packed non-version data pointer, and current
        position.  If the pickle is true, then the data pointer must
        be 0, but the pickle can be empty *and* the pointer 0.
        """

        copy = 1 # Can we just copy a data pointer

        # First check if it is possible to undo this record.
        tpos = self._tindex.get(h.oid, 0)
        ipos = self._index.get(h.oid, 0)
        tipos = tpos or ipos

        if tipos != pos:
            # Eek, a later transaction modified the data, but,
            # maybe it is pointing at the same data we are.
            cserial, cdataptr, cdata, cver = self._undo_get_data(
                h.oid, ipos, tpos)
            # Versions of undone record and current record *must* match!
            if cver != h.version:
                raise UndoError(oid, 'Current and undone versions differ')

            if cdataptr != pos:
                # If the backpointers don't match, check to see if
                # conflict resolution is possible.  If not, raise
                # UndoError.
                try:
                    if (
                        # The current record wrote a new pickle
                        cdataptr == tipos
                        or
                        # Backpointers are different
                        self._loadBackPOS(h.oid, pos) !=
                        self._loadBackPOS(h.oid, cdataptr)
                        ):
                        if h.prev and not tpos:
                            copy = 0 # we'll try to do conflict resolution
                        else:
                            # We bail if:
                            # - We don't have a previous record, which should
                            #   be impossible.
                            raise UndoError(h.oid, "No previous record")
                except KeyError:
                    # LoadBack gave us a key error. Bail.
                    raise UndoError(h.oid, "_loadBack() failed")

        # Return the data that should be written in the undo record.
        if not h.prev:
            # There is no previous revision, because the object creation
            # is being undone.
            return "", "", 0, "", "", ipos

        # What does getVersion do?
        version, snv = self._getVersion(h.oid, h.prev)
        if copy:
            # we can just copy our previous-record pointer forward
            return "", "", h.prev, version, snv, ipos

        try:
            # returns data, serial tuple
            bdata = self._loadBack(h.oid, h.prev)[0]
        except KeyError:
            # couldn't find oid; what's the real explanation for this?
            raise UndoError(h.oid, "_loadBack() failed")


        # XXX conflict resolution needs to give us new references, but
        # that code isn't written yet

        try:
            data, refs = self._conflict.resolve(h.oid, cserial, h.serial,
                                                bdata, cdata)
        except ConflictError:
            data = None
            refs = []

        if data is None:
            raise UndoError(h.oid,
                            "Some data were modified by a later transaction")
        return data, ''.join(refs), 0, h.version, snv, ipos


    # undoLog() returns a description dict that includes an id entry.
    # The id is opaque to the client, but contains the transaction id.
    # The transactionalUndo() implementation does a simple linear
    # search through the file (from the end) to find the transaction.

    def undoLog(self, first=0, last=-20, filter=None):
        if last < 0:
            last = first - last + 1
        self._lock_acquire()
        try:
            if self._packing:
                raise UndoError("Can't undo during pack")
            us = UndoSearch(self._file, self._pos, self._pack_time,
                            first, last, filter)
            while not us.finished():
                # Hold lock for batches of 20 searches, so default search
                # parameters will finish without letting another thread run.
                for i in range(20):
                    if us.finished():
                        break
                    us.search()
                # Give another thread a chance, so that a long undoLog()
                # operation doesn't block all other activity.
                self._lock_release()
                self._lock_acquire()
            return us.results
        finally:
            self._lock_release()

    def undo(self, transaction_id, transaction):
        """Undo a transaction, given by transaction_id.

        Do so by writing new data that reverses the action taken by
        the transaction.

        Usually, we can get by with just copying a data pointer, by
        writing a file position rather than a pickle. Sometimes, we
        may do conflict resolution, in which case we actually copy
        new data that results from resolution.
        """

        if self._is_read_only:
            raise ReadOnlyError()
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)

        self._lock_acquire()
        try:
            return self._txn_undo(transaction_id)
        finally:
            self._lock_release()

    def _txn_undo(self, transaction_id):
        # Find the right transaction to undo and call _txn_undo_write().
        tid = base64.decodestring(transaction_id + '\n')
        assert len(tid) == 8
        tpos = self._txn_find(tid, 1)
        tindex = self._txn_undo_write(tpos)
        self._tindex.update(tindex)
        return tindex.keys()

    def _txn_undo_write(self, tpos):
        # a helper function to write the data records for transactional undo

        otloc = self._pos
        here = self._pos + self._tfile.tell() + self._thl
        # Let's move the file pointer back to the start of the txn record.
        th = self._read_txn_header(tpos)
        if th.status != " ":
            raise UndoError(None, "non-undoable transaction")
            
        tend = tpos + th.tlen
        pos = tpos + th.headerlen()
        tindex = {}

        # keep track of failures, cause we may succeed later
        failures = {}
        while pos < tend:
            h = self._read_data_header(pos)
            if h.oid in failures:
                del failures[h.oid] # second chance!
            try:
                p, refs, prev, version, snv, ipos = self._undo_record(h, pos)
            except UndoError, v:
                # Don't fail right away. We may be redeemed later!
                failures[h.oid] = v
            else:
                plen = len(p)
                nrefs = len(refs) / 8
                self._tfile.write(pack(DATA_HDR,
                                       h.oid, self._serial, ipos, otloc,
                                       len(version), nrefs, plen))
                # If the backpointer refers to an object in a version,
                # we need to write a reasonable pointer to the previous
                # version data, which might be in _tvindex.
                if version:
                    vprev = (self._tvindex.get(version)
                             or self._vindex.get(version))
                    self._tfile.write(snv + p64(vprev) + version)
                    self._tvindex[version] = here
                    odlen = DATA_VERSION_HDR_LEN + len(version) + (plen or 8)
                else:
                    odlen = DATA_HDR_LEN + (plen or 8)

                self._tfile.write(refs)
                if p:
                    self._tfile.write(p)
                else:
                    self._tfile.write(p64(prev))
                tindex[h.oid] = here
                here += odlen + nrefs * 8
            pos += h.recordlen()
            if pos > tend:
                raise UndoError(None, "non-undoable transaction")
        if failures:
            if len(failures) == 1:
                raise failures.values()[0]
            raise MultipleUndoErrors(failures.items())

        return tindex

    def versionEmpty(self, version):
        if not version:
            # The interface is silent on this case. I think that this should
            # be an error, but Barry thinks this should return 1 if we have
            # any non-version data. This would be excruciatingly painful to
            # test, so I must be right. ;)
            raise VersionError("The version must be an non-empty string")
        self._lock_acquire()
        try:
            pos = self._vindex.get(version, 0)
            if not pos:
                return True
            while pos:
                h = self._read_data_header(pos)
                if self._index[h.oid] == pos:
                    return False
                pos = h.vprev
            return True
        finally:
            self._lock_release()

    def versions(self):
        return [version for version in self._vindex.keys()
                if not self.versionEmpty(version)]

    def pack(self, t, gc=True):
        """Perform a pack on the storage.

        There are two forms of packing: incremental and full gc.  In an
        incremental pack, only old object revisions are removed.  In a full gc
        pack, cyclic garbage detection and removal is also performed.

        t is the pack time.  All non-current object revisions older than t
        will be removed in an incremental pack.

        FileStorage ignores the gc flag.  Every pack does both incremental and
        full gc packing.
        """
        if self._is_read_only:
            raise ReadOnlyError()

        stop = timeStampFromTime(t).raw()
        if stop == ZERO:
            raise FileStorageError("Invalid pack time")

        # If the storage is empty, there's nothing to do.
        if not self._index:
            return

        # Record pack time so we don't undo while packing
        self._lock_acquire()
        try:
            if self._packing:
                # Already packing.
                raise FileStorageError("Already packing")
            self._packing = True
            self._pack_time = stop
        finally:
            self._lock_release()

        p = FileStoragePacker(self._name, stop,
                              self._lock_acquire, self._lock_release,
                              self._commit_lock_acquire,
                              self._commit_lock_release)
        try:
            opos = p.pack()
            if opos is None:
                return
            assert p.locked
            oldpath = self._name + ".old"
            self._lock_acquire()
            try:
                self._file.close()
                try:
                    if os.path.exists(oldpath):
                        os.remove(oldpath)
                    os.rename(self._name, oldpath)
                except Exception, msg:
                    self._file = open(self._name, 'r+b')
                    raise

                # OK, we're beyond the point of no return
                os.rename(self._name + '.pack', self._name)
                self._file = open(self._name, 'r+b')
                self._initIndex(p.index, p.vindex, p.tindex, p.tvindex)
                self._pos = opos
                self._save_index()
            finally:
                self._lock_release()
        finally:
            if p.locked:
                self._commit_lock_release()
            self._lock_acquire()
            self._packing = False
            self._pack_time = None
            self._lock_release()


    def iterator(self, start=None, stop=None):
        return FileIterator(self._file_name, start, stop)

    def lastSerial(self, oid):
        """Return last serialno committed for object oid.

        If there is no serialno for this oid -- which can only occur
        if it is a new object -- return None.
        """
        try:
            pos = self._index[oid]
        except KeyError:
            return None
        self._file.seek(pos)
        # first 8 bytes are oid, second 8 bytes are serialno
        h = self._file.read(16)
        if len(h) < 16:
            raise CorruptedDataError(oid, h)
        if h[:8] != oid:
            # get rest of header
            h += self._file.read(26)
            raise CorruptedDataError(oid, h)
        return h[8:]

    def cleanup(self):
        """Remove all files created by this storage."""
        cleanup(self._file_name)

        
def _truncate(file, name, pos):
    seek=file.seek
    seek(0,2)
    file_size=file.tell()
    try:
        i=0
        while 1:
            oname='%s.tr%s' % (name, i)
            if os.path.exists(oname):
                i=i+1
            else:
                warn("Writing truncated data from %s to %s", name, oname)
                o=open(oname,'wb')
                seek(pos)
                cp(file, o, file_size-pos)
                o.close()
                break
    except:
        error("couldn\'t write truncated data for %s", name)
        raise StorageSystemError("Couldn't save truncated data")

    seek(pos)
    file.truncate()

class FileIterator(FileStorageFormatter):
    """Iterate over the transactions in a FileStorage file."""
    _ltid = ZERO
    _file = None

    implements(IStorageIterator)

    def __init__(self, filename, start=None, stop=None):
        self._file = open(filename, "rb")
        self._read_metadata()
        self._file.seek(0,2)
        self._file_size = self._file.tell()
        self._pos = self._metadata_size
        assert start is None or isinstance(start, str)
        assert stop is None or isinstance(stop, str)
        if start:
            self._skip_to_start(start)
        self._stop = stop

    def close(self):
        file = self._file
        if file is not None:
            self._file = None
            file.close()

    def _skip_to_start(self, start):
        # Scan through the transaction records doing almost no sanity
        # checks.
        while True:
            self._file.seek(self._pos)
            h = self._file.read(16)
            if len(h) < 16:
                return
            tid, stl = unpack(">8s8s", h)
            if tid >= start:
                return
            tl = u64(stl)
            try:
                self._pos += tl + 8
            except OverflowError:
                self._pos = long(self._pos) + tl + 8
            if __debug__:
                # Sanity check
                self._file.seek(self._pos - 8, 0)
                rtl = self._file.read(8)
                if rtl != stl:
                    pos = self._file.tell() - 8
                    panic("%s has inconsistent transaction length at %s "
                          "(%s != %s)",
                          self._file.name, pos, u64(rtl), u64(stl))

    def __iter__(self):
        if self._file is None:
            # A closed iterator.  XXX: Is IOError the best we can do?  For
            # now, mimic a read on a closed file.
            raise IOError("iterator is closed")
        file = self._file
        seek = file.seek
        read = file.read

        pos = self._pos
        while True:
            # Read the transaction record
            seek(pos)
            h = read(TRANS_HDR_LEN)
            if len(h) < TRANS_HDR_LEN:
                break

            tid, tl, status, ul, dl, el = unpack(TRANS_HDR,h)
            if el < 0:
                el = (1L<<32) - el

            if tid <= self._ltid:
                warn("%s time-stamp reduction at %s", self._file.name, pos)
            self._ltid = tid

            if pos+(tl+8) > self._file_size or status=='c':
                # Hm, the data were truncated or the checkpoint flag wasn't
                # cleared.  They may also be corrupted,
                # in which case, we don't want to totally lose the data.
                warn("%s truncated, possibly due to damaged records at %s",
                     self._file.name, pos)
                break

            if status not in ' p':
                warn('%s has invalid status, %s, at %s', self._file.name,
                     status, pos)

            if tl < (TRANS_HDR_LEN+ul+dl+el):
                # We're in trouble. Find out if this is bad data in
                # the middle of the file, or just a turd that Win 9x
                # dropped at the end when the system crashed.  Skip to
                # the end and read what should be the transaction
                # length of the last transaction.
                seek(-8, 2)
                rtl = u64(read(8))
                # Now check to see if the redundant transaction length is
                # reasonable:
                if self._file_size - rtl < pos or rtl < TRANS_HDR_LEN:
                    logger.critical('%s has invalid transaction header at %s',
                                    self._file.name, pos)
                    warn("It appears that there is invalid data at the end of "
                         "the file, possibly due to a system crash.  %s "
                         "truncated to recover from bad data at end.",
                         self._file.name)
                    break
                else:
                    warn('%s has invalid transaction header at %s',
                         self._file.name, pos)
                    break

            if self._stop is not None and tid > self._stop:
                return

            tpos = pos
            tend = tpos+tl

            pos = tpos+(TRANS_HDR_LEN+ul+dl+el)
            # user and description are utf-8 encoded strings
            user = read(ul).decode('utf-8')
            description = read(dl).decode('utf-8')
            e = {}
            if el:
                try:
                    e = loads(read(el))
                # XXX can we do better?
                except:
                    pass

            result = RecordIterator(tid, status, user, description, e, pos,
                                    tend, file, tpos)
            pos = tend

            # Read the (intentionally redundant) transaction length
            seek(pos)
            l = u64(read(8))
            if l != tl:
                warn("%s redundant transaction length check failed at %s",
                     self._file.name, pos)
                break
            pos += 8
            yield result

class RecordIterator(FileStorageFormatter):
    """Iterate over the transactions in a FileStorage file."""

    implements(ITransactionRecordIterator, ITransactionAttrs)

    def __init__(self, tid, status, user, desc, ext, pos, tend, file, tpos):
        self.tid = tid
        self.status = status
        self.user = user
        self.description = desc
        self._extension = ext
        self._pos = pos
        self._tend = tend
        self._file = file
        self._tpos = tpos

    def __iter__(self):
        pos = self._pos
        while pos < self._tend:
            # Read the data records for this transaction
            h = self._read_data_header(pos)
            dlen = h.recordlen()
            if pos + dlen > self._tend or h.tloc != self._tpos:
                warn("%s data record exceeds transaction record at %s",
                     file.name, pos)
                return

            pos += dlen
            prev_txn = None

            if h.plen:
                refsdata = self._file.read(h.nrefs * 8)
                refs = splitrefs(refsdata)
                data = self._file.read(h.plen)
            else:
                if not h.back:
                    # If the backpointer is 0, then this transaction
                    # undoes the object creation.  It either aborts
                    # the version that created the object or undid the
                    # transaction that created it.  Return None
                    # for data and refs because the backpointer has
                    # the real data and refs.
                    data = None
                    refs = None
                else:
                    data, refs, _s, tid = self._loadBackTxn(h.oid, h.back)
                    prev_txn = self.getTxnFromData(h.oid, h.back)

            yield Record(h.oid, h.serial, h.version, data, prev_txn, refs)

class Record:
    """An abstract database record."""

    implements(IDataRecord)

    def __init__(self, oid, serial, version, data, data_txn, refs):
        self.oid = oid
        self.serial = serial
        self.version = version
        self.data = data
        self.data_txn = data_txn
        self.refs = refs

class UndoSearch(FileStorageFormatter):

    def __init__(self, file, pos, packt, first, last, filter=None):
        self._file = file
        self.pos = pos
        self.packt = packt
        self.first = first
        self.last = last
        self.filter = filter
        self.i = 0
        self.results = []
        self.stop = 0

    def finished(self):
        """Return True if UndoSearch has found enough records."""
        # The first txn record is at 1024, so pos must be >= 1024
        return self.i >= self.last or self.pos < 1024 or self.stop

    def search(self):
        """Search for another record."""
        dict = self._readnext()
        if dict is None:
            return
        if dict is not None and (self.filter is None or self.filter(dict)):
            if self.i >= self.first:
                self.results.append(dict)
            self.i += 1

    def _readnext(self):
        """Read the next record from the storage."""
        self._file.seek(self.pos - 8)
        self.pos -= u64(self._file.read(8)) + 8
        if self.pos < 1024:
            return None
        h = self._read_txn_header(self.pos)
        if h.tid < self.packt or h.status == 'p':
            self.stop = 1
            return None
        assert h.status == " "
        d = {'id': base64.encodestring(h.tid).rstrip(),
             'time': TimeStamp(h.tid).timeTime(),
             'user_name': h.user,
             'description': h.descr}
        if h.ext:
            ext = loads(h.ext)
            d.update(ext)
        return d

def cleanup(filename):
    """Remove all FileStorage related files."""
    for ext in '', '.old', '.tmp', '.lock', '.index', '.pack':
        try:
            os.remove(filename + ext)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
