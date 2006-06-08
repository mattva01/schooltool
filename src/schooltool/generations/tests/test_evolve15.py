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
Unit tests for schooltool.generations.evolve15

$Id$
"""

import unittest

from zope.annotation.interfaces import IAnnotations
from zope.interface import directlyProvides
from zope.annotation.interfaces import IAnnotatable
from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(dict):
    implements(ISchoolToolApplication, IAnnotatable)

    def __init__(self):
        groups = self['groups'] = {}
        persons = self['persons'] = {}

    def __repr__(self):
        return '<app>'


class ObjectStub(dict):
    implements(IAnnotatable)

    def __init__(self, name='stub'):
        self.name = name

    def __repr__(self):
        return '<Object %r>' % self.name


def doctest_removeLocalGrants():
    r"""Doctest for removeLocalGrants.

    Prepare object with local grants:

        >>> obj = ObjectStub('object')
        >>> directlyProvides(obj, IAnnotations)
        >>> from zope.app.securitypolicy.principalpermission import AnnotationPrincipalPermissionManager
        >>> from zope.app.securitypolicy.principalrole import AnnotationPrincipalRoleManager
        >>> ppm = AnnotationPrincipalPermissionManager(obj)
        >>> ppm.grantPermissionToPrincipal('test.run', 'testrunner')
        >>> prm = AnnotationPrincipalRoleManager(obj)
        >>> prm.assignRoleToPrincipal('doctester', 'testrunner')
        >>> ann = IAnnotations(obj)
        >>> print '\n'.join(sorted(ann.keys()))
        zope.app.security.AnnotationPrincipalRoleManager
        zopel.app.security.AnnotationPrincipalPermissionManager

        >>> from schooltool.generations.evolve15 import removeLocalGrants
        >>> removeLocalGrants(obj)
        >>> print '\n'.join(sorted(ann.keys()))
        <BLANKLINE>
    """


def doctest_evolve():
    r"""Doctest for evolution to generation 15.

    Create context:

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()
        >>> directlyProvides(app, IAnnotations)

        >>> person = app['persons']['person'] = ObjectStub('person')
        >>> group = app['groups']['group'] = ObjectStub('group')
        >>> directlyProvides(person, IAnnotations)
        >>> directlyProvides(group, IAnnotations)

        >>> from schooltool.generations import evolve15 as ev
        >>> result = []
        >>> def removeLocalGrantsStub(obj):
        ...     result.append('removeLocalGrants from %r' % obj)
        >>> old_removeLocalGrants = ev.removeLocalGrants
        >>> ev.removeLocalGrants = removeLocalGrantsStub
        >>> ev.evolve(context)
        >>> print '\n'.join(sorted(result))
        removeLocalGrants from <Object 'group'>
        removeLocalGrants from <Object 'person'>
        removeLocalGrants from <app>

        >>> ev.removeLocalGrants = old_removeLocalGrants
    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
