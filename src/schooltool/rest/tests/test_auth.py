#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for schooltool.rest.auth

$Id$
"""

import unittest
from zope.interface import implements
from schooltool.rest.tests import RequestStub
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestAccessPolicies(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        import schooltool.membership
        from schooltool.membership import Membership
        from schooltool.model import Person, Group
        from schooltool.app import Application, ApplicationObjectContainer
        self.setUpRegistries()
        schooltool.membership.setUp()

        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)

        self.teachers_group = app['groups'].new('teachers')
        self.managers_group = app['groups'].new('managers')

        self.simpleuser = app['persons'].new('simpleuser')
        self.otheruser = app['persons'].new('otheruser')
        self.teacher = app['persons'].new('teacher')
        self.manager = app['persons'].new('manager')

        Membership(group=self.teachers_group, member=self.teacher)
        Membership(group=self.managers_group, member=self.manager)

    def test_isManager(self):
        from schooltool.rest.auth import isManager
        self.assertEquals(isManager(None), False)
        self.assertEquals(isManager(self.simpleuser), False)
        self.assertEquals(isManager(self.teacher), False)
        self.assertEquals(isManager(self.manager), True)

    def test_isTeacher(self):
        from schooltool.rest.auth import isTeacher
        self.assertEquals(isTeacher(None), False)
        self.assertEquals(isTeacher(self.simpleuser), False)
        self.assertEquals(isTeacher(self.teacher), True)
        self.assertEquals(isTeacher(self.manager), True)

    def test_getOwner(self):
        from schooltool.rest.auth import getOwner
        from schooltool.interfaces import ILocation, IApplicationObject

        class ObjectStub:
            implements(ILocation)

            def __init__(self, parent, name='foo'):
                self.__parent__ = parent
                self.__name__ = name

        class PersonStub(ObjectStub):
            implements(IApplicationObject)

        a = ObjectStub(None)
        b = PersonStub(a)
        c = ObjectStub(b)

        self.assertEquals(getOwner(None), None)
        self.assertEquals(getOwner(a), None)
        self.assertEquals(getOwner(b), b)
        self.assertEquals(getOwner(c), b)
        self.assertEquals(getOwner('foo'), None)

    def do_test_access(self, auth, matrix, context=None):

        class ViewStub:
            authorize = auth

        view = ViewStub()

        usermap = {'anonymous': None, 'simpleuser': self.simpleuser,
                   'teacher': self.teacher, 'manager': self.manager,
                   'otheruser': self.otheruser}
        matrix = matrix.strip().splitlines()
        methods = matrix[0].split()
        for row in matrix[1:]:
            cols = row.split()
            username = cols[0]
            user = usermap[username]
            for method, access in zip(methods, cols[1:]):
                assert access in '+-'
                request = RequestStub(method=method, authenticated_user=user)
                if access == '-':
                    self.failIf(view.authorize(context, request),
                                'access for %s granted for %s'
                                % (method, username))
                else:
                    self.assert_(view.authorize(context, request),
                                 'access for %s denied for %s'
                                 % (method, username))

    def test_PublicAccess(self):
        from schooltool.rest.auth import PublicAccess
        access = """
                    GET     HEAD    PUT     POST    DELETE  OTHER
        anonymous    +       +       -       -        -       -
        simpleuser   +       +       -       -        -       -
        teacher      +       +       -       -        -       -
        manager      +       +       +       +        +       +
        """
        self.do_test_access(PublicAccess, access)

    def test_TeacherAccess(self):
        from schooltool.rest.auth import TeacherAccess
        access = """
                    GET     HEAD    PUT     POST    DELETE  OTHER
        anonymous    +       +       -       -        -       -
        simpleuser   +       +       -       -        -       -
        teacher      +       +       +       +        -       -
        manager      +       +       +       +        +       +
        """
        self.do_test_access(TeacherAccess, access)

    def test_SystemAccess(self):
        from schooltool.rest.auth import SystemAccess
        access = """
                    GET     HEAD    PUT     POST    DELETE  OTHER
        anonymous    -       -       -       -        -       -
        simpleuser   -       -       -       -        -       -
        teacher      -       -       -       -        -       -
        manager      +       +       +       +        +       +
        """
        self.do_test_access(SystemAccess, access)

    def test_PrivateAccess(self):
        from schooltool.rest.auth import PrivateAccess
        access = """
                    GET     HEAD    PUT     POST    DELETE  OTHER
        anonymous    -       -       -       -        -       -
        simpleuser   -       -       -       -        -       -
        otheruser    -       -       -       -        -       -
        teacher      -       -       -       -        -       -
        manager      +       +       +       +        +       +
        """
        self.do_test_access(PrivateAccess, access)

        access = """
                    GET     HEAD    PUT     POST    DELETE  OTHER
        anonymous    -       -       -       -        -       -
        simpleuser   +       +       +       +        +       +
        otheruser    -       -       -       -        -       -
        teacher      -       -       -       -        -       -
        manager      +       +       +       +        +       +
        """
        self.do_test_access(PrivateAccess, access, self.simpleuser.calendar)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAccessPolicies))
    return suite

if __name__ == '__main__':
    unittest.main()
