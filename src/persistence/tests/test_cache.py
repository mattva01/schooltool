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
import unittest, time
from persistence import Persistent
from persistence.cache import Cache

class P(Persistent):
    pass

class DM:
    def __init__(self, cache):
        self.called=0
        self.cache=cache

    def register(self, ob):
        self.called += 1

    def setstate(self, ob):
        ob.__setstate__({'x': 42})
        self.cache.activate(ob._p_oid)

class Test(unittest.TestCase):

    def testBasicLife(self):
        dm=DM(Cache())
        p1=P()
        p1._p_oid=1
        p1._p_jar=dm
        dm.cache.set(1, p1)
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        del p1
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 0},
                         )
        p1=P()
        p1._p_oid=1
        p1._p_jar=dm
        dm.cache.set(1, p1)
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        p=dm.cache.get(1)
        dm.cache.invalidate([1])
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 1, 'active': 0},
                         )
        # XXX deal with current cPersistence implementation
        if p._p_changed != 3:
            self.assertEqual(p._p_changed, None)

        p.a=1
        p._p_changed=0
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        dm.cache.invalidate([1])
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 1, 'active': 0},
                         )
        # XXX deal with current cPersistence implementation
        if p._p_changed != 3:
            self.assertEqual(p._p_changed, None)

        p.a=1
        p._p_changed=0
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        dm.cache.clear()
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 1, 'active': 0},
                         )
        # XXX deal with current cPersistence implementation
        if p._p_changed != 3:
            self.assertEqual(p._p_changed, None)



        p.a=1
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        # No changed because p is modified:
        dm.cache.shrink()
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        p._p_changed = 0
        dm.cache.clear()
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 1, 'active': 0},
                         )
        del p
        del p1
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 0},
                         )

    def testGC(self):
        dm=DM(Cache(inactive=1, size=2))
        p1=P()
        p1._p_oid=1
        p1._p_jar=dm
        dm.cache.set(1, p1)
        p1.a=1
        p1._p_atime=int(time.time()-5000)%86400
        dm.cache.shrink()
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        p1._p_changed=0
        dm.cache.shrink()
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 1, 'active': 0},
                         )

        p1.a=1
        p1._p_changed=0
        p1._p_atime=int(time.time()-5000)%86400
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 0, 'active': 1},
                         )
        dm.cache.shrink()
        self.assertEqual(dm.cache.statistics(),
                         {'ghosts': 1, 'active': 0},
                         )

def test_suite():
    return unittest.makeSuite(Test)

if __name__ == "__main__":
    unittest.main()
