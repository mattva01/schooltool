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
"""Run the version related tests for a storage.

Any storage that supports versions should be able to pass all these tests.
"""

import time

from zodb import interfaces
from zodb.db import DB
from zodb.ztransaction import Transaction
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle, snooze
from zodb.storage.interfaces import IUndoStorage, IVersionStorage

from transaction import get_transaction


class VersionStorage:

    def testIVersionStorage(self):
        self.assert_(IVersionStorage.isImplementedBy(self._storage))

    def testVersionedStoreAndLoad(self):
        eq = self.assertEqual
        # Store a couple of non-version revisions of the object
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(11))
        revid = self._dostore(oid, revid=revid, data=MinPO(12))
        # And now store some new revisions in a version
        version = 'test-version'
        revid = self._dostore(oid, revid=revid, data=MinPO(13),
                              version=version)
        revid = self._dostore(oid, revid=revid, data=MinPO(14),
                              version=version)
        revid = self._dostore(oid, revid=revid, data=MinPO(15),
                              version=version)
        # Now read back the object in both the non-version and version and
        # make sure the values jive.
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(12))
        data, vrevid = self._storage.load(oid, version)
        eq(zodb_unpickle(data), MinPO(15))
        s = self._storage.getSerial(oid)
        eq(s, max(revid, vrevid))

    def testVersionedLoadErrors(self):
        oid = self._storage.newObjectId()
        version = 'test-version'
        revid = self._dostore(oid, data=MinPO(11))
        revid = self._dostore(oid, revid=revid, data=MinPO(12),
                              version=version)
        # Try to load a bogus oid
        self.assertRaises(KeyError,
                          self._storage.load,
                          self._storage.newObjectId(), '')
        data, revid = self._storage.load(oid, 'bogus')
        self.assertEqual(zodb_unpickle(data), MinPO(11))


    def testVersionLock(self):
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(11))
        version = 'test-version'
        revid = self._dostore(oid, revid=revid, data=MinPO(12),
                              version=version)
        self.assertRaises(interfaces.VersionLockError,
                          self._dostore,
                          oid, revid=revid, data=MinPO(14),
                          version='another-version')

    def testVersionEmpty(self):
        # Before we store anything, these versions ought to be empty
        version = 'test-version'
        self.failUnless(self._storage.versionEmpty(version))
        # Now store some objects
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(11))
        revid = self._dostore(oid, revid=revid, data=MinPO(12))
        revid = self._dostore(oid, revid=revid, data=MinPO(13),
                              version=version)
        revid = self._dostore(oid, revid=revid, data=MinPO(14),
                              version=version)
        # The blank version should not be empty

        # Neither should 'test-version'
        self.failUnless(not self._storage.versionEmpty(version))
        # But this non-existant version should be empty
        self.failUnless(self._storage.versionEmpty('bogus'))

    def testVersions(self):
        unless = self.failUnless
        # Store some objects in the non-version
        oid1 = self._storage.newObjectId()
        oid2 = self._storage.newObjectId()
        oid3 = self._storage.newObjectId()
        revid1 = self._dostore(oid1, data=MinPO(11))
        revid2 = self._dostore(oid2, data=MinPO(12))
        revid3 = self._dostore(oid3, data=MinPO(13))
        # Now create some new versions
        revid1 = self._dostore(oid1, revid=revid1, data=MinPO(14),
                               version='one')
        revid2 = self._dostore(oid2, revid=revid2, data=MinPO(15),
                               version='two')
        revid3 = self._dostore(oid3, revid=revid3, data=MinPO(16),
                               version='three')
        # Ask for the versions
        versions = self._storage.versions()
        unless('one' in versions)
        unless('two' in versions)
        unless('three' in versions)

    def _setup_version(self, version='test-version'):
        # Store some revisions in the non-version
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(49))
        revid = self._dostore(oid, revid=revid, data=MinPO(50))
        nvrevid = revid = self._dostore(oid, revid=revid, data=MinPO(51))
        # Now do some stores in a version
        revid = self._dostore(oid, revid=revid, data=MinPO(52),
                              version=version)
        revid = self._dostore(oid, revid=revid, data=MinPO(53),
                              version=version)
        revid = self._dostore(oid, revid=revid, data=MinPO(54),
                              version=version)
        return oid, version

    def testAbortVersion(self):
        eq = self.assertEqual
        oid, version = self._setup_version()

        # XXX Not sure I can write a test for getSerial() in the
        # presence of aborted versions, because FileStorage and
        # Berkeley storage give a different answer. I think Berkeley
        # is right and FS is wrong.

##        s1 = self._storage.getSerial(oid)
        # Now abort the version -- must be done in a transaction
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.abortVersion(version, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
##        s2 = self._storage.getSerial(oid)
##        eq(s1, s2) # or self.assert(s2 > s1) ?
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(51))

    def testAbortVersionErrors(self):
        eq = self.assertEqual
        oid, version = self._setup_version()
        # Now abort a bogus version
        t = Transaction()
        self._storage.tpcBegin(t)

        # And try to abort the empty version
        if IUndoStorage.isImplementedBy(self._storage):
            self.assertRaises(interfaces.VersionError,
                              self._storage.abortVersion,
                              '', t)

        # But now we really try to abort the version
        oids = self._storage.abortVersion(version, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(51))

    def testCommitVersionErrors(self):
        if not IVersionStorage.isImplementedBy(self._storage):
            return
        eq = self.assertEqual
        oid1, version1 = self._setup_version('one')
        data, revid1 = self._storage.load(oid1, version1)
        eq(zodb_unpickle(data), MinPO(54))
        t = Transaction()
        self._storage.tpcBegin(t)
        try:
            self.assertRaises(interfaces.VersionCommitError,
                              self._storage.commitVersion,
                              'one', 'one', t)
        finally:
            self._storage.tpcAbort(t)

    def testModifyAfterAbortVersion(self):
        eq = self.assertEqual
        oid, version = self._setup_version()
        # Now abort the version
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.abortVersion(version, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        # Load the object's current state (which gets us the revid)
        data, revid = self._storage.load(oid, '')
        # And modify it a few times
        revid = self._dostore(oid, revid=revid, data=MinPO(52))
        revid = self._dostore(oid, revid=revid, data=MinPO(53))
        revid = self._dostore(oid, revid=revid, data=MinPO(54))
        data, newrevid = self._storage.load(oid, '')
        eq(newrevid, revid)
        eq(zodb_unpickle(data), MinPO(54))

    def testCommitToNonVersion(self):
        eq = self.assertEqual
        oid, version = self._setup_version()
        data, revid = self._storage.load(oid, version)
        eq(zodb_unpickle(data), MinPO(54))
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(51))
        # Try committing this version to the empty version
        oids = self._commitVersion(version, "")
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(54))

    def testCommitToOtherVersion(self):
        eq = self.assertEqual
        oid1, version1 = self._setup_version('one')

        data, revid1 = self._storage.load(oid1, version1)
        eq(zodb_unpickle(data), MinPO(54))
        oid2, version2 = self._setup_version('two')
        data, revid2 = self._storage.load(oid2, version2)
        eq(zodb_unpickle(data), MinPO(54))

        # make sure we see the non-version data when appropriate
        data, revid2 = self._storage.load(oid1, version2)
        eq(zodb_unpickle(data), MinPO(51))
        data, revid2 = self._storage.load(oid2, version1)
        eq(zodb_unpickle(data), MinPO(51))
        data, revid2 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(51))

        # Okay, now let's commit version1 to version2
        oids = self._commitVersion(version1, version2)
        eq(len(oids), 1)
        eq(oids[0], oid1)
        data, revid = self._storage.load(oid1, version2)
        eq(zodb_unpickle(data), MinPO(54))
        data, revid = self._storage.load(oid2, version2)
        eq(zodb_unpickle(data), MinPO(54))

        # an object can only exist in one version, so a load from
        # version1 should now give the non-version data
        data, revid2 = self._storage.load(oid1, version1)
        eq(zodb_unpickle(data), MinPO(51))

        # as should a version that has never been used
        data, revid2 = self._storage.load(oid1, 'bela lugosi')
        eq(zodb_unpickle(data), MinPO(51))

    def testAbortOneVersionCommitTheOther(self):
        eq = self.assertEqual
        oid1, version1 = self._setup_version('one')
        data, revid1 = self._storage.load(oid1, version1)
        eq(zodb_unpickle(data), MinPO(54))
        oid2, version2 = self._setup_version('two')
        data, revid2 = self._storage.load(oid2, version2)
        eq(zodb_unpickle(data), MinPO(54))

        # Let's make sure we can't get object1 in version2
        data, revid2 = self._storage.load(oid1, version2)
        eq(zodb_unpickle(data), MinPO(51))

        oids = self._abortVersion(version1)
        eq(len(oids), 1)
        eq(oids[0], oid1)
        data, revid = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(51))

        data, revid = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(51))
        data, revid = self._storage.load(oid2, version2)
        eq(zodb_unpickle(data), MinPO(54))
        oids = self._commitVersion(version2, "")
        eq(len(oids), 1)
        eq(oids[0], oid2)
        data, revid = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(51))

        # But the trunk should be up to date now
        data, revid = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(54))
        data, revid = self._storage.load(oid2, version2)
        eq(zodb_unpickle(data), MinPO(54))

        oid = self._storage.newObjectId()
        revid = self._dostore(oid, revid=revid, data=MinPO(54), version='one')
        self.assertRaises(KeyError,
                          self._storage.load, oid, '')
        self.assertRaises(KeyError,
                          self._storage.load, oid, 'two')

    def testPackVersions(self):
        db = DB(self._storage)
        cn = db.open(version="testversion")
        root = cn.root()

        obj = root["obj"] = MinPO("obj")
        root["obj2"] = MinPO("obj2")
        txn = get_transaction()
        txn.note("create 2 objs in version")
        txn.commit()

        obj.value = "77"
        txn = get_transaction()
        txn.note("modify obj in version")
        txn.commit()

        # undo the modification to generate a mix of backpointers
        # and versions for pack to chase
        info = db.undoInfo()
        db.undo(info[0]["id"])
        txn = get_transaction()
        txn.note("undo modification")
        txn.commit()

        snooze()
        self._storage.pack(time.time())

        db.commitVersion("testversion")
        txn = get_transaction()
        txn.note("commit version")
        txn.commit()

        cn = db.open()
        root = cn.root()
        root["obj"] = "no version"

        txn = get_transaction()
        txn.note("modify obj")
        txn.commit()

        self._storage.pack(time.time())

    def testPackVersionsInPast(self):
        db = DB(self._storage)
        cn = db.open(version="testversion")
        root = cn.root()

        obj = root["obj"] = MinPO("obj")
        root["obj2"] = MinPO("obj2")
        txn = get_transaction()
        txn.note("create 2 objs in version")
        txn.commit()

        obj.value = "77"
        txn = get_transaction()
        txn.note("modify obj in version")
        txn.commit()

        t0 = time.time()
        snooze()

        # undo the modification to generate a mix of backpointers
        # and versions for pack to chase
        info = db.undoInfo()
        db.undo(info[0]["id"])
        txn = get_transaction()
        txn.note("undo modification")
        txn.commit()

        self._storage.pack(t0)

        db.commitVersion("testversion")
        txn = get_transaction()
        txn.note("commit version")
        txn.commit()

        cn = db.open()
        root = cn.root()
        root["obj"] = "no version"

        txn = get_transaction()
        txn.note("modify obj")
        txn.commit()

        self._storage.pack(time.time())

    def testPackVersionReachable(self):
        db = DB(self._storage)
        cn = db.open()
        root = cn.root()

        names = "a", "b", "c"

        for name in names:
            root[name] = MinPO(name)
            get_transaction().commit()

        for name in names:
            cn2 = db.open(version=name)
            rt2 = cn2.root()
            obj = rt2[name]
            obj.value = MinPO("version")
            get_transaction().commit()
            cn2.close()

        root["d"] = MinPO("d")
        get_transaction().commit()

        snooze()
        self._storage.pack(time.time())
        cn.sync()
        cn._cache.clear()

        # make sure all the non-version data is there
        for name, obj in root.items():
            self.assertEqual(name, obj.value)

        # make sure all the version-data is there,
        # and create a new revision in the version
        for name in names:
            cn2 = db.open(version=name)
            rt2 = cn2.root()
            obj = rt2[name].value
            self.assertEqual(obj.value, "version")
            obj.value = "still version"
            get_transaction().commit()
            cn2.close()

        db.abortVersion("b")
        txn = get_transaction()
        txn.note("abort version b")
        txn.commit()

        t = time.time()
        snooze()

        L = db.undoInfo()
        db.undo(L[0]["id"])
        txn = get_transaction()
        txn.note("undo abort")
        txn.commit()

        self._storage.pack(t)

        cn2 = db.open(version="b")
        rt2 = cn2.root()
        self.assertEqual(rt2["b"].value.value, "still version")
