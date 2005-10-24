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
Level-related Browser View Tests

$Id$
"""
import unittest

from zope.testing import doctest, doctestunit

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.group import group
from schooltool.person import person
from schooltool.level import testing

def setUpStudents(app):
    app['persons']['srichter'] = person.Person('srichter', 'Stephan Richter')
    app['persons']['thoffman'] = person.Person('thoffman', 'Tom Hoffman')
    app['persons']['crichter'] = person.Person('crichter', 'Claudia Richter')


def setUpGroups(app):
    app['groups']['manager'] = group.Group('manager', 'School Manager')


def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'level.txt',
            setUp=setUp, tearDown=tearDown,
            globs={'pprint': doctestunit.pprint},
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
        doctest.DocFileSuite(
            'promotion.txt',
            setUp=setUp, tearDown=tearDown,
            globs={'pprint': doctestunit.pprint,
                   'setUpLevels': testing.setUpLevels,
                   'setUpGroups': setUpGroups,
                   'setUpStudents': setUpStudents,
                   'setUpPromotionWorkflow': testing.setUpPromotionWorkflow},
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
        doctest.DocFileSuite(
            'record.txt',
            setUp=setUp, tearDown=tearDown,
            globs={'pprint': doctestunit.pprint,
                   'setUpLevels': testing.setUpLevels,
                   'setUpGroups': setUpGroups,
                   'setUpStudents': setUpStudents,
                   'setUpPromotionWorkflow': testing.setUpPromotionWorkflow},
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
        ))

if __name__ == '__main__':
    unittest.main(default='test_suite')
