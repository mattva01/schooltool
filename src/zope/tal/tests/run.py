#! /usr/bin/env python
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
"""Run all tests.

$Id$
"""
import sys
import unittest

from zope.tal.tests import utils
from zope.tal.tests import test_htmltalparser
from zope.tal.tests import test_talinterpreter
from zope.tal.tests import test_files
from zope.tal.tests import test_sourcepos

# XXX this code isn't picked up by the Zope 3 test framework..
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(test_htmltalparser.test_suite())
    if not utils.skipxml:
        import test_xmlparser
        suite.addTest(test_xmlparser.test_suite())
    suite.addTest(test_talinterpreter.test_suite())
    suite.addTest(test_files.test_suite())
    suite.addTest(test_sourcepos.test_suite())
    return suite

def main():
    return utils.run_suite(test_suite())

if __name__ == "__main__":
    errs = main()
    sys.exit(errs and 1 or 0)
