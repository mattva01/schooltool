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
Gradebook-related Tests

$Id$
"""
import os
import unittest

import zope.component
from zope.testing import doctest, doctestunit
from zope.app.testing import setup

# Has to be imported before
import schooltool.app
import schooltool.requirement.testing
from schooltool import course, person, requirement
from schooltool.relationship.tests import setUpRelationships
from schooltool.gradebook import activity, gradebook, statistic, interfaces

def setUp(test):
    setup.placefulSetUp()
    setUpRelationships()
    schooltool.requirement.testing.setUpEvaluation()
    zope.component.provideAdapter(
        activity.getCourseActivities,
        (course.interfaces.ICourse,), interfaces.IActivities)
    zope.component.provideAdapter(
        activity.getSectionActivities,
        (course.interfaces.ISection,), interfaces.IActivities)

    zope.component.provideAdapter(gradebook.Gradebook)
    zope.component.provideAdapter(statistic.Statistics)


def tearDown(test):
    setup.placefulTearDown()


def test_suite():
    optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS
    return unittest.TestSuite((
        doctest.DocFileSuite('../README.txt',
                             setUp=setUp, tearDown=tearDown,
                             globs={'pprint': doctestunit.pprint},
                             optionflags=optionflags),
        ))

if __name__ == '__main__':
    unittest.main(default='test_suite')
