##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
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
"""Provide a text dump of a storage based on a storage iterator."""

from zodb.storage.file import FileIterator
from zodb.timestamp import TimeStamp
from zodb.utils import u64
from zodb.storage.tests.base import zodb_unpickle
from zodb.serialize import SimpleObjectReader

import md5
import time

def dbdump(iter, outp=None, with_offset=True):
    i = 0
    for trans in iter:
        t = TimeStamp(trans.tid).timeTime()
        # special case just for FileStorage
        if with_offset and hasattr(trans, "_pos"):
            print >> outp, "Trans #%05d tid=%016x time=%s offset=%d" % \
                  (i, u64(trans.tid), time.ctime(t), trans._pos)
        else:
            print >> outp, "Trans #%05d tid=%016x time=%s" % \
                  (i, u64(trans.tid), time.ctime(t))
        print >> outp, "\tstatus=%s user=%s description=%s" % \
              (`trans.status`, trans.user, trans.description)
        j = 0
        for rec in trans:
            if rec.data is None:
                fullclass = "undo or abort of object creation"
                size = 0
            else:
                # Any object reader will do
                reader = SimpleObjectReader()
                fullclass = reader.getClassName(rec.data)
                dig = md5.new(rec.data).hexdigest()
                size = len(rec.data)
            # special case for testing purposes
            if fullclass == "zodb.tests.minpo.MinPO":
                obj = zodb_unpickle(rec.data)
                fullclass = "%s %s" % (fullclass, obj.value)
            if rec.version:
                version = "version=%s " % rec.version
            else:
                version = ''
            print >> outp, "  data #%05d oid=%016x %sclass=%s size=%d" % \
                  (j, u64(rec.oid), version, fullclass, size)
            j += 1
        print >> outp
        i += 1
    iter.close()

def fsdump(path, outp=None, with_offset=True):
    iter = FileIterator(path)
    dbdump(iter, outp, with_offset)

if __name__ == "__main__":
    import sys
    path = sys.argv[1]
    fsdump(path)
