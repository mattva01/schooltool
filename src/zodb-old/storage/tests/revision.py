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

"""Check loadSerial() on storages that support historical revisions.
"""

from zodb.storage.base import ZERO
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle

class RevisionStorage:

    def testLoadSerial(self):
        oid = self._storage.newObjectId()
        revid = ZERO
        revisions = {}
        for i in range(31, 38):
            revid = self._dostore(oid, revid=revid, data=MinPO(i))
            revisions[revid] = MinPO(i)
        # Now make sure all the revisions have the correct value
        for revid, value in revisions.items():
            data = self._storage.loadSerial(oid, revid)
            self.assertEqual(zodb_unpickle(data), value)
