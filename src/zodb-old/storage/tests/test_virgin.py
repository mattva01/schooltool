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

# Test creation of a brand new database, and insertion of root objects.

import unittest

from transaction import get_transaction
from persistence.dict import PersistentDict

from zodb.storage.base import berkeley_is_available
from zodb.storage.tests.base import ZODBTestBase



class InsertMixin:
    def testIsEmpty(self):
        self.failUnless(not self._root.has_key('names'))

    def testNewInserts(self):
        self._root['names'] = names = PersistentDict()
        names['Warsaw'] = 'Barry'
        names['Hylton'] = 'Jeremy'
        get_transaction().commit()



class FullNewInsertsTest(ZODBTestBase, InsertMixin):
    from zodb.storage.bdbfull import BDBFullStorage
    ConcreteStorage = BDBFullStorage


class MinimalNewInsertsTest(ZODBTestBase, InsertMixin):
    from zodb.storage.bdbminimal import BDBMinimalStorage
    ConcreteStorage = BDBMinimalStorage



def test_suite():
    suite = unittest.TestSuite()
    if berkeley_is_available:
        suite.addTest(unittest.makeSuite(MinimalNewInsertsTest))
        suite.addTest(unittest.makeSuite(FullNewInsertsTest))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
