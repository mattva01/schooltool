##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test a gettext implementation of a Message Catalog.

$Id$
"""
import unittest, os
from zope.i18n.gettextmessagecatalog import GettextMessageCatalog
from zope.i18n.tests.test_imessagecatalog import TestIMessageCatalog


class GettextMessageCatalogTest(TestIMessageCatalog):

    def _getMessageCatalog(self):
        from zope.i18n import tests
        path = os.path.split(tests.__file__)[0]
        self._path = os.path.join(path, 'en-default.mo')
        catalog = GettextMessageCatalog('en', 'default', self._path)
        return catalog


    def _getUniqueIndentifier(self):
        return self._path



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GettextMessageCatalog))
    return suite


if __name__=='__main__':
    unittest.TextTestRunner().run(test_suite())
