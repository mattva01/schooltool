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
Unit tests for schooltool.generations.evolve11

$Id$
"""

import unittest

from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements

from schooltool.generations.tests import ContextStub


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()


def tearDown(test):
    setup.placelessTearDown()


def doctest_evolve11():
    """Evolution to generation 11.

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.course.interfaces import ISection
        >>> from zope.app.securitypolicy.interfaces import IPrincipalRoleManager
        >>> from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
        >>> from zope.interface import implements
        >>> from zope.app.testing import ztapi

        >>> class RoleManagerStub:
        ...     implements(IPrincipalRoleManager)
        ...     def __init__(self, *args, **kw):
        ...         pass
        ...     def assignRoleToPrincipal(self, role, principal):
        ...         print 'Assign role=%s, principal=%s' % (role, principal)
        >>> class PermissionManagerStub:
        ...     implements(IPrincipalPermissionManager)
        ...     def __init__(self, parent, *args, **kw):
        ...         self.__name__ = parent.__name__
        ...     def grantPermissionToPrincipal(self, permission, principal):
        ...         print '%s assign permission=%s, principal=%s' % (
        ...               self.__name__, permission, principal)

        >>> ztapi.provideAdapter(ISchoolToolApplication, IPrincipalRoleManager,
        ...                      RoleManagerStub)
        >>> ztapi.provideAdapter(ISection, IPrincipalPermissionManager,
        ...                      PermissionManagerStub)

        >>> class MockSchoolTool(dict):
        ...     implements(ISchoolToolApplication)

        >>> class PersonStub:
        ...     def __init__(self, title):
        ...         self.__name__ = title
        >>> class SectionStub:
        ...     implements(ISection)
        ...     __name__ = 'section1'
        ...     instructors = [PersonStub('teacher')]

        >>> context = ContextStub()
        >>> app = MockSchoolTool()
        >>> from schooltool.person.person import PersonContainer
        >>> app['sections'] = {'section1': SectionStub()}
        >>> context.root_folder['app'] = app

    Shazam!

        >>> from schooltool.generations.evolve11 import evolve
        >>> evolve(context)
        Assign role=schooltool.manager, principal=sb.group.manager
        Assign role=schooltool.administrator, principal=sb.group.administrators
        Assign role=schooltool.teacher, principal=sb.group.teachers
        Assign role=schooltool.clerk, principal=sb.group.clerks
        section1 assign permission=schooltool.viewAttendance, principal=sb.person.teacher
    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
