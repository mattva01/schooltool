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
"""
Level-related Tests

$Id$
"""
import os
import unittest
from zope.testing import doctest, doctestunit
from zope.component import testing
from zope.app.testing import setup

def setUp(test):
    test.globs['this_directory'] = os.path.join(os.path.dirname(__file__), '..')
    setup.placefulSetUp()

def tearDown(test):
    setup.placefulTearDown()


def showApplications(activity, pd):
    return [pd.applications[id]
            for (id, other, other) in activity.applications]


def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite('../README.txt',
                             setUp=setUp, tearDown=tearDown,
                             globs={'pprint': doctestunit.pprint,
                                    'showApplications': showApplications},
                             optionflags=doctest.NORMALIZE_WHITESPACE),
        ))

if __name__ == '__main__':
    unittest.main(default='test_suite')
