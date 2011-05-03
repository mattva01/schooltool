#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""Tests for Pluggable Traversers
"""
import unittest
import doctest

from zope.component import testing

from schooltool.testing.setup import ZCMLWrapper


def setUp(test=None):
    testing.setUp(test=test)
    zcml = ZCMLWrapper()
    zcml.include('zope.app.zcmlfiles')
    zcml.include('schooltool.traverser', file='meta.zcml')
    zcml.include('schooltool.traverser')
    test.globs['zcml'] = zcml

def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)

    return unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=setUp, tearDown=testing.tearDown,
            optionflags=optionflags),
        ))

if __name__ == '__main__':
    unittest.main(default='test_suite')
