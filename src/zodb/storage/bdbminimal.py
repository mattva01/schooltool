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

"""Berkeley storage without undo or versioning.

$Id: bdbminimal.py,v 1.26 2003/07/10 17:36:50 bwarsaw Exp $
"""

from zope.interface import implements

from zodb.interfaces import ZERO, ConflictError
from zodb.storage.interfaces import *
from zodb.utils import p64, u64
from zodb.conflict import ResolvedSerial
from zodb.storage.base import db, BerkeleyBase, PackStop, _WorkThread
from zodb.storage.base import splitrefs
# For debugging
from zodb.interfaces import _fmt_oid as fo

ABORT = 'A'
COMMIT = 'C'
PRESENT = 'X'
EMPTYSTRING = ''

BDBMINIMAL_SCHEMA_VERSION = 'BM03'



class BDBMinimalStorage(BerkeleyBase):

    implements(IStorage)

    def _init(self):
        # Data Type Assumptions:
        #
        # - Object ids (oid) are 8-bytes
        # - Objects have revisions, with each revision being identified by a
        #   unique serial number.
        # - Transaction ids (tid) are 8-bytes
        # - Data pickles are of arbitrary length
        #
        # Here is a list of tables common between the Berkeley storages.
        # There may be some minor differences in semantics.
        #
        # info -- {key -> value}
        #     This table contains storage metadata information.  The keys and
        #     values are simple strings of variable length.   Here are the
        #     valid keys:
        #
        #         dbversion - the version of the database (reserved for ZODB4)
        #
        #         version - the underlying Berkeley database schema version
        #
        # serials -- {oid -> [serial]}
        #     Maps oids to serial numbers.  Each oid can be mapped to 1 or 2
        #     serial numbers (this is for optimistic writes).  If it maps to
        #     two serial numbers, then the current one is determined by the
        #     pending flag (see below).
        #
        # pickles -- {oid+serial -> pickle}
        #     Maps the object revisions to the revision's pickle data.
        #
        # refcounts -- {oid -> count}
        #     Maps the oid to the reference count for the object.  This
        #     reference count is updated during the _finish() call.  When it
        #     goes to zero, the object is automatically deleted.
        #
        # references -- {oid+tid -> oid+oid+...}
        #     For each revision of the object, these are the oids of the
        #     objects referred to in the data record, as a list of 8-byte
        #     oids, concatenated together.
        #
        # oids -- [oid]
        #     This is a list of oids of objects that are modified in the
        #     current uncommitted transaction.
        #
        # pending -- tid -> 'A' | 'C'
        #     This is an optional flag which says what to do when the database
        #     is recovering from a crash.  The flag is normally 'A' which
        #     means any pending data should be aborted.  At the start of the
        #     tpc_finish() this flag will be changed to 'C' which means, upon
        #     recovery/restart, all pending data should be committed.  Outside
        #     of any transaction (e.g. before the tpc_begin()), there will be
        #     no pending entry.  It is a database invariant that if the
        #     pending table is empty, the oids table must also be empty.
        #
        # packmark -- [oid]
        #     Every object reachable from the root during a classic pack
        #     operation will have its oid present in this table.
        #
        # oidqueue -- [oid]
        #     This table is a Queue, not a BTree.  It is used during the mark
        #     phase of pack() and contains a list of oids for work to be done.
        #     It is also used during pack to list objects for which no more
        #     references exist, such that the objects can be completely packed
        #     away.
        self._oidqueue = self._setupDB('oidqueue', 0, db.DB_QUEUE, 8)

    def _version_check(self, txn):
        version = self._info.get('version')
        if version is None:
            self._info.put('version', BDBMINIMAL_SCHEMA_VERSION, txn=txn)
        elif version <> BDBMINIMAL_SCHEMA_VERSION:
            raise StorageSystemError, 'incompatible storage version'

    def _dorecovery(self):
        # Do recovery and consistency checks
        pendings = self._pending.keys()
        assert len(pendings) <= 1
        if len(pendings) == 0:
            assert len(self._oids) == 0
        else:
            # Do recovery
            tid = pendings[0]
            flag = self._pending.get(tid)
            assert flag in (ABORT, COMMIT)
            self._lock_acquire()
            try:
                if flag == ABORT:
                    self._withtxn(self._doabort, tid)
                else:
                    self._withtxn(self._docommit, tid)
            finally:
                self._lock_release()

    def _make_autopacker(self, event):
        return _Autopack(self, event, self._config.frequency)

    def _doabort(self, txn, tid):
        co = cs = None
        try:
            co = self._oids.cursor(txn=txn)
            cs = self._serials.cursor(txn=txn)
            rec = co.first()
            while rec:
                oid = rec[0]
                rec = co.next()
                try:
                    cs.set_both(oid, tid)
                except db.DBNotFoundError:
                    pass
                else:
                    cs.delete()
                # Clean up revision-indexed tables
                revid = oid+tid
                self._pickles.delete(revid, txn=txn)
                if self._references.has_key(revid):
                    self._references.delete(revid, txn=txn)
        finally:
            # There's a small window of opportunity for leaking a cursor here,
            # if co.close() were to fail.  In practice this shouldn't happen.
            if co: co.close()
            if cs: cs.close()
        # We're done with these tables
        self._oids.truncate(txn)
        self._pending.truncate(txn)

    def _abort(self):
        self._withtxn(self._doabort, self._serial)

    def _docommit(self, txn, tid):
        self._pending.put(self._serial, COMMIT, txn)
        deltas = {}
        co = cs = None
        try:
            co = self._oids.cursor(txn=txn)
            cs = self._serials.cursor(txn=txn)
            rec = co.first()
            while rec:
                oid = rec[0]
                rec = co.next()
                # Remove from the serials table all entries with key oid where
                # the serial is not tid.  These are the old revisions of the
                # object.  At the same time, we want to collect the oids of
                # the objects referred to by this revision's pickle, so that
                # later we can decref those reference counts.
                srec = cs.set(oid)
                while srec:
                    soid, stid = srec
                    if soid <> oid:
                        break
                    if stid <> tid:
                        revid = oid+stid
                        # This is the previous revision of the object, so
                        # decref its references and clean up its pickles.
                        cs.delete()
                        references = self._references.get(revid, txn=txn)
                        if references:
                            self._update(deltas, references, -1)
                        self._pickles.delete(revid, txn=txn)
                        if self._references.has_key(revid):
                            self._references.delete(revid, txn=txn)
                    srec = cs.next_dup()
                # Now add incref deltas for all objects referenced by the new
                # revision of this object.
                references = self._references.get(oid+tid, txn=txn)
                if references:
                    self._update(deltas, references, 1)
        finally:
            # There's a small window of opportunity for leaking a cursor here,
            # if co.close() were to fail.  In practice this shouldn't happen.
            if co: co.close()
            if cs: cs.close()
        # We're done with this table
        self._pending.truncate(txn)
        self._oids.truncate(txn)
        # Now, to finish up, we need apply the refcount deltas to the
        # refcounts table, and do recursive collection of all refcount == 0
        # objects.
        while deltas:
            deltas = self._update_refcounts(deltas, txn)

    def _update_refcounts(self, deltas, txn):
        newdeltas = {}
        for oid, delta in deltas.items():
            refcount = u64(self._refcounts.get(oid, ZERO, txn=txn)) + delta
            assert refcount >= 0, refcount
            if refcount == 0:
                # The reference count for this object has just gone to zero,
                # so we can safely remove all traces of it from the serials,
                # pickles and refcounts table.  Note that before we remove its
                # pickle, we need to decref all the objects referenced by it.
                current = self._getCurrentSerial(oid)
                references = self._references.get(oid+current, txn=txn)
                if references:
                    self._update(newdeltas, references, -1)
                # And delete the serials, pickle and refcount entries.  At
                # this point, I believe we should have just one serial entry.
                self._serials.delete(oid, txn=txn)
                assert self._serials.get(oid, txn=txn) is None
                self._refcounts.delete(oid, txn=txn)
                self._pickles.delete(oid+current, txn=txn)
            else:
                self._refcounts.put(oid, p64(refcount), txn=txn)
        # Return the list of objects referenced by pickles just deleted in
        # this round, for decref'ing on the next go 'round.
        return newdeltas

    def _begin(self, tid):
        # When a transaction begins, we set the pending flag to ABORT,
        # meaning, if we crash between now and the time we vote, all changes
        # will be aborted.
        txn = self._env.txn_begin()
        try:
            self._pending.put(self._serial, ABORT, txn)
        except:
            txn.abort()
            raise
        else:
            txn.commit()

    def _dostore(self, txn, oid, serial, data, refs):
        oserial = self._getCurrentSerial(oid)
        if oserial is not None and serial <> oserial:
            # Conflict resolution depends on loadSerial() which minimal
            # storage doesn't implement, so we can't do it.
            raise ConflictError
        # Optimistically write to the various tables.
        newserial = self._serial
        revid = oid+newserial
        self._serials.put(oid, newserial, txn=txn)
        self._pickles.put(revid, data, txn=txn)
        if refs:
            references = EMPTYSTRING.join(refs)
            assert len(references) % 8 == 0
            self._references.put(revid, references, txn=txn)
        self._oids.put(oid, PRESENT, txn=txn)
        return newserial

    def store(self, oid, serial, data, refs, version, transaction):
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)
        # We don't support versions
        if version <> '':
            raise NotImplementedError
        # All updates must be done with the application lock acquired
        self._lock_acquire()
        try:
            return self._withtxn(self._dostore, oid, serial, data, refs)
        finally:
            self._lock_release()

    #
    # Accessor interface
    #

    def _getAllSerials(self, oid):
        # BAW: We must have the application level lock here.
        c = self._serials.cursor()
        try:
            # There can be zero, one, or two entries in the serials table for
            # this oid.  If there are no entries, raise a KeyError (we know
            # nothing about this object).
            #
            # If there is exactly one entry then this has to be the entry for
            # the object, regardless of the pending flag.
            #
            # If there are two entries, then we need to look at the pending
            # flag to decide which to return (there /better/ be a pending flag
            # set!).  If the pending flag is COMMIT then we've already voted
            # so the second one is the good one.  If the pending flag is ABORT
            # then we haven't yet committed to this transaction so the first
            # one is the good one.
            serials = []
            try:
                rec = c.set(oid)
            except db.DBNotFoundError:
                rec = None
            while rec:
                serials.append(rec[1])
                rec = c.next_dup()
            return serials
        finally:
            c.close()

    def _getCurrentSerial(self, oid):
        serials = self._getAllSerials(oid)
        if not serials:
            return None
        if len(serials) == 1:
            return serials[0]
        pending = self._pending.get(self._serial)
        assert pending in (ABORT, COMMIT)
        if pending == ABORT:
            return serials[0]
        return serials[1]

    def load(self, oid, version):
        if version <> '':
            raise NotImplementedError
        self._lock_acquire()
        try:
            # Get the current serial number for this object
            serial = self._getCurrentSerial(oid)
            if serial is None:
                raise KeyError, 'Object does not exist: %r' % oid
            # Get this revision's pickle data
            return self._pickles[oid+serial], serial
        finally:
            self._lock_release()

    def modifiedInVersion(self, oid):
        # So BaseStorage.getSerial() just works.  Note that this storage
        # doesn't support versions.
        return ''

    #
    # Packing.  In Minimal storage, packing is only required to get rid of
    # object cycles, since there are no old object revisions.
    #

    def pack(self, t, gc=True):
        self.log('pack started')
        # A simple wrapper around the bulk of packing, but which acquires a
        # lock that prevents multiple packs from running at the same time.
        # It's redundant in this storage because we hold the commit lock
        # for the duration, but it doesn't hurt.
        self._packlock.acquire()
        # Before setting the packing flag to true, acquire the storage lock
        # and clear out the packmark table, in case there's any cruft left
        # over from the previous pack.
        #
        # Caution: this used to release the commit lock immediately after
        # clear_packmark (below) was called, so there was a small chance for
        # transactions to commit between the packing phases.  This suffered
        # rare races, where packing could (erroneously) delete an active
        # object.  Since interleaving packing with commits is thought to be
        # unimportant for minimal storages, the easiest (by far) fix is to
        # hold the commit lock throughout packing.
        #
        # Details: Suppose the commit lock is released after clearing
        # packmark.  Suppose a transaction gets through _dostore() before
        # marking begins.  Then because self._packing is True, _dostore() adds
        # the stored oids to _packmark.  But _mark() uses _packmark as a list
        # of *chased* oids, not as a list of oids to *be* chased.  So the oids
        # added to _packmark by _dostore() don't get chased by _mark(), and
        # anything they reference (that isn't referenced by something else
        # too) is considered to be trash.  Holding the commit lock during all
        # of packing makes it impossible for self._packing to be True when in
        # _dostore() or _docommit(), so those never add anything to _packmark,
        # and only the correct oid-chasing code in _mark() populates
        # _packmark.
        #
        # Later:  All code referencing self._packing was removed.
        self._commit_lock_acquire()
        try:
            # We have to do this within a Berkeley transaction
            def clear_packmark(txn):
                self._packmark.truncate(txn=txn)
            self._withtxn(clear_packmark)
            # We don't wrap this in _withtxn() because we're going to do the
            # operation across several Berkeley transactions, which allows
            # other work to happen (stores and reads) while packing is being
            # done.
            #
            # Also, we don't care about the pack time, since we don't need to
            # collect object revisions
            self._dopack()
        finally:
            self._packlock.release()
            self._commit_lock_release()
        self.log('pack finished')

    def _dopack(self):
        # Do a mark and sweep for garbage collection.  Calculate the set of
        # objects reachable from the root.  Anything else is a candidate for
        # having all their revisions packed away.  The set of reachable
        # objects lives in the _packmark table.
        self._withlock(self._withtxn, self._mark)
        # Now perform a sweep, using oidqueue to hold all object ids for
        # objects which are not root reachable as of the pack time.
        self._withlock(self._withtxn, self._sweep)
        # Once again, collect any objects with refcount zero due to the mark
        # and sweep garbage collection pass.
        self._withlock(self._withtxn, self._collect_objs)

    def _mark(self, txn):
        # Find the oids for all the objects reachable from the root.  To
        # reduce the amount of in-core memory we need do do a pack operation,
        # we'll save the mark data in the packmark table.  The oidqueue is a
        # BerkeleyDB Queue that holds the list of object ids to look at next,
        # and by using this we don't need to keep an in-memory dictionary.
        assert len(self._oidqueue) == 0
        # Quick exit for empty storages
        if not self._serials:
            return
        # The oid of the object we're looking at, starting at the root
        oid = ZERO
        # Start at the root, find all the objects the current revision of the
        # root references, and then for each of those, find all the objects it
        # references, and so on until we've traversed the entire object graph.
        while oid:
            if self._stop:
                raise PackStop, 'stopped in _mark()'
            if not self._packmark.has_key(oid):
                # We've haven't yet seen this object
                self._packmark.put(oid, PRESENT, txn=txn)
                # Get the pickle data for every revision of this object we
                # know about.
                serials = self._getAllSerials(oid)
                for tid in serials:
                    # Now get the oids of all the objects referenced by this
                    # object revision
                    references = self._references.get(oid+tid)
                    if references:
                        for oid in splitrefs(references):
                            self._oidqueue.append(oid, txn)
            # Pop the next oid off the queue and do it all again
            rec = self._oidqueue.consume(txn)
            oid = rec and rec[1]
        assert len(self._oidqueue) == 0

    def _sweep(self, txn):
        c = self._serials.cursor(txn=txn)
        try:
            rec = c.first()
            while rec:
                if self._stop:
                    raise PackStop, 'stopped in _sweep()'
                oid = rec[0]
                rec = c.next()
                # If packmark (which knows about all the root reachable
                # objects) doesn't have a record for this guy, then we can zap
                # it.  Do so by appending to oidqueue.
                if not self._packmark.has_key(oid):
                    self._oidqueue.append(oid, txn)
        finally:
            c.close()
        # We're done with the mark table
        self._packmark.truncate(txn=txn)

    def _collect_objs(self, txn):
        orec = self._oidqueue.consume(txn)
        while orec:
            if self._stop:
                raise PackStop, 'stopped in _collect_objs()'
            oid = orec[1]
            # Delete the object from the serials table
            c = self._serials.cursor(txn)
            try:
                try:
                    rec = c.set(oid)
                except db.DBNotFoundError:
                    rec = None
                while rec and rec[0] == oid:
                    if self._stop:
                        raise PackStop, 'stopped in _collect_objs() loop 1'
                    c.delete()
                    rec = c.next_dup()
                # We don't need the refcounts any more, but note that if the
                # object was never referenced from another object, there may
                # not be a refcounts entry.
                try:
                    self._refcounts.delete(oid, txn=txn)
                except db.DBNotFoundError:
                    pass
            finally:
                c.close()
            # Collect the pickle data
            c = self._pickles.cursor(txn)
            try:
                try:
                    rec = c.set_range(oid)
                except db.DBNotFoundError:
                    rec = None
                while rec and rec[0][:8] == oid:
                    if self._stop:
                        raise PackStop, 'stopped in _collect_objs() loop 2'
                    c.delete()
                    rec = c.next()
            finally:
                c.close()
            # Collect references and do reference counting
            c = self._references.cursor(txn)
            try:
                try:
                    rec = c.set_range(oid)
                except db.DBNotFoundError:
                    rec = None
                while rec and rec[0][:8] == oid:
                    if self._stop:
                        raise PackStop, 'stopped in _collect_objs() loop 3'
                    references = rec[1]
                    if references:
                        deltas = {}
                        self._update(deltas, references, -1)
                        for oid, delta in deltas.items():
                            rc = u64(self._refcounts.get(oid, ZERO)) + delta
                            if rc <= 0:
                                self._oidqueue.append(oid, txn)
                            else:
                                self._refcounts.put(oid, p64(rc), txn=txn)
                        # Delete table entry
                        c.delete()
                        rec = c.next()
            finally:
                c.close()
            # We really do want this down here, since _decrefPickle() could
            # add more items to the queue.
            orec = self._oidqueue.consume(txn)
        assert len(self._oidqueue) == 0

    # getSerial(self, oid)


class _Autopack(_WorkThread):
    NAME = 'autopacking'

    def _dowork(self):
        # Run the autopack phase
        self._storage.pack('ignored')
