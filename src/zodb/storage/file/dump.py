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
"""A low-level utility to dump the internal FileStorage representation."""

import struct
from zodb.storage.file.format \
     import TRANS_HDR, TRANS_HDR_LEN, DATA_HDR, DATA_HDR_LEN
from zodb.utils import u64
from zodb.storage.base import splitrefs
from zodb.storage.tests.base import zodb_unpickle

def fmt(p64):
    # Return a nicely formatted string for a packaged 64-bit value
    return "%016x" % u64(p64)

def dump(path, dest=None):
    Dumper(path, dest).dump()

class Dumper:
    """A very verbose dumper for debugging FileStorage problems."""

    def __init__(self, path, dest=None):
        self.file = open(path, "rb")
        self.dest = dest

    def dump(self):
        fid = self.file.read(1024)
        print >> self.dest, "*" * 60
        print >> self.dest, "file identifier: %r" % fid[:4]
        print >> self.dest, "database version: %r" % fid[4:8]
        # XXX perhaps verify that the rest of the metadata is nulls?
        while self.dump_txn():
            pass

    def dump_txn(self):
        pos = self.file.tell()
        h = self.file.read(TRANS_HDR_LEN)
        if not h:
            return False
        tid, tlen, status, ul, dl, el = struct.unpack(TRANS_HDR, h)
        end = pos + tlen
        print >> self.dest, "=" * 60
        print >> self.dest, "offset: %d" % pos
        print >> self.dest, "end pos: %d" % end
        print >> self.dest, "transaction id: %s" % fmt(tid)
        print >> self.dest, "trec len: %d" % tlen
        print >> self.dest, "status: %r" % status
        user = descr = extra = ""
        if ul:
            user = self.file.read(ul)
        if dl:
            descr = self.file.read(dl)
        if el:
            extra = self.file.read(el)
        print >> self.dest, "user: %r" % user
        print >> self.dest, "description: %r" % descr
        print >> self.dest, "len(extra): %d" % el
        while self.file.tell() < end:
            self.dump_data(pos)
        tlen2 = u64(self.file.read(8))
        print >> self.dest, "redundant trec len: %d" % tlen2
        return True

    def dump_data(self, tloc):
        pos = self.file.tell()
        h = self.file.read(DATA_HDR_LEN)
        assert len(h) == DATA_HDR_LEN
        oid, revid, prev, tloc, vlen, nrefs, dlen = struct.unpack(DATA_HDR, h)
        print >> self.dest, "-" * 60
        print >> self.dest, "offset: %d" % pos
        print >> self.dest, "oid: %s" % fmt(oid)
        print >> self.dest, "revid: %s" % fmt(revid)
        print >> self.dest, "previous record offset: %d" % prev
        print >> self.dest, "transaction offset: %d" % tloc
        if vlen:
            pnv = self.file.read(8)
            sprevdata = self.file.read(8)
            version = self.file.read(vlen)
            print >> self.dest, "version: %r" % version
            print >> self.dest, "non-version data offset: %d" % u64(pnv)
            print >> self.dest, \
                  "previous version data offset: %d" % u64(sprevdata)
        print >> self.dest, 'numrefs:', nrefs
        for ref in splitrefs(self.file.read(nrefs * 8)):
            print >> self.dest, '\t%s' % fmt(ref)
        print >> self.dest, "len(data): %d" % dlen
        data = self.file.read(dlen)
        # A debugging feature for use with the test suite.
        if data.startswith("(czodb.storage.tests.minpo\nMinPO\n"):
            print >> self.dest, "value: %r" % zodb_unpickle(data).value
        if not dlen:
            sbp = self.file.read(8)
            print >> self.dest, "backpointer: %d" % u64(sbp)

if __name__ == "__main__":
    import sys
    Dumper(sys.argv[1]).dump()
