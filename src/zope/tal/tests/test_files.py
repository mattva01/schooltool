#! /usr/bin/env python
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
"""Tests that run driver.py over input files comparing to output files.

$Id: test_files.py,v 1.3 2004/03/08 23:33:58 srichter Exp $
"""

import glob
import os
import sys
import unittest

import zope.tal.runtest

from zope.tal.tests import utils


class FileTestCase(unittest.TestCase):

    def __init__(self, file, dir):
        self.__file = file
        self.__dir = dir
        unittest.TestCase.__init__(self)

    # For unittest.
    def shortDescription(self):
        path = os.path.basename(self.__file)
        return '%s (%s)' % (path, self.__class__)

    def runTest(self):
        basename = os.path.basename(self.__file)
        #sys.stdout.write(basename + " ")
        sys.stdout.flush()
        if basename.startswith('test_metal'):
            sys.argv = ["", "-Q", "-m", self.__file]
        else:
            sys.argv = ["", "-Q", self.__file]
        pwd = os.getcwd()
        try:
            try:
                os.chdir(self.__dir)
                zope.tal.runtest.main()
            finally:
                os.chdir(pwd)
        except SystemExit, what:
            if what.code:
                self.fail("output for %s didn't match" % self.__file)

try:
    script = __file__
except NameError:
    script = sys.argv[0]

def test_suite():
    suite = unittest.TestSuite()
    dir = os.path.dirname(script)
    dir = os.path.abspath(dir)
    parentdir = os.path.dirname(dir)
    prefix = os.path.join(dir, "input", "test*.")
    if utils.skipxml:
        xmlargs = []
    else:
        xmlargs = glob.glob(prefix + "xml")
        xmlargs.sort()
    htmlargs = glob.glob(prefix + "html")
    htmlargs.sort()
    args = xmlargs + htmlargs
    if not args:
        sys.stderr.write("Warning: no test input files found!!!\n")
    for arg in args:
        case = FileTestCase(arg, parentdir)
        suite.addTest(case)
    return suite

if __name__ == "__main__":
    errs = utils.run_suite(test_suite())
    sys.exit(errs and 1 or 0)
