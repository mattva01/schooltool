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
Unit tests for schooltool.rest.relationship

$Id$
"""

import unittest
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import QuietLibxml2Mixin, AppSetupMixin
from schooltool.tests.utils import EqualsSortedMixin, XMLCompareMixin
from schooltool.rest.tests import RequestStub

__metaclass__ = type


class TestACLView(AppSetupMixin, QuietLibxml2Mixin,
                  EqualsSortedMixin, XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def createView(self):
        from schooltool.rest.acl import ACLView
        return ACLView(self.person.calendar.acl)

    def test_listPerms(self):
        from schooltool.interfaces import Everybody, ViewPermission
        view = self.createView()
        view.context.add((Everybody, ViewPermission))
        self.assertEqualsSorted(view.listPerms(),
                                [{'path': '/persons/johndoe',
                                  'perm': 'Add', 'title': 'John Doe'},
                                 {'path': '/persons/johndoe',
                                  'perm': 'Modify', 'title': 'John Doe'},
                                 {'path': '/persons/johndoe',
                                  'perm': 'View', 'title': 'John Doe'},
                                 {'path': 'Everybody',
                                  'perm': 'View', 'title': 'Everybody'}])

    def test_do_GET(self):
        from schooltool.interfaces import Everybody, ViewPermission
        view = self.createView()
        view.context.add((Everybody, ViewPermission))
        result = view.render(RequestStub(authenticated_user=self.manager))
        expected = """
            <acl xmlns='http://schooltool.org/ns/model/0.1'>
              <allow principal="/persons/johndoe" permission="Add"
                     title="John Doe"/>
              <allow principal="/persons/johndoe" permission="Modify"
                     title="John Doe"/>
              <allow principal="/persons/johndoe" permission="View"
                     title="John Doe"/>
              <allow principal="Everybody" permission="View"
                     title="Everybody"/>
            </acl>
            """
        self.assertEqualsXML(result, expected)

    def test_do_POST_empty(self):
        view = self.createView()
        body = "<acl xmlns='http://schooltool.org/ns/model/0.1'/>"
        request = RequestStub(authenticated_user=self.manager,
                              method="PUT", body=body)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(list(view.context), [])

    def test_do_POST(self):
        from schooltool.interfaces import ViewPermission, ModifyPermission
        from schooltool.interfaces import Everybody
        view = self.createView()
        body = """
               <acl xmlns="http://schooltool.org/ns/model/0.1">
                 <allow principal="Everybody"  permission="View"/>
                 <allow principal="/groups/teachers" permission="Modify"/>
               </acl>
               """
        request = RequestStub(authenticated_user=self.manager,
                              method="PUT", body=body)
        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEqualsSorted(list(view.context),
                                [(Everybody, ViewPermission),
                                 (self.teachers, ModifyPermission)])

    def test_do_POST_errors(self):
        view = self.createView()
        bodies = ("""<acl xmlns="http://schooltool.org/ns/model/0.1">
                       <allow principal="Some guy"  permission="View"/>
                     </acl>
                     """,
                  """<acl xmlns="http://schooltool.org/ns/model/0.1">
                       <allow principal="Everybody"  permission="Fly"/>
                     </acl>
                     """,
                  """<acl>
                       <allow principal="Everybody"  permission="View"/>
                     </acl>
                     """)

        for body in bodies:
            request = RequestStub(authenticated_user=self.manager,
                                  method="PUT", body=body)
            result = view.render(request)
            self.assertEquals(request.code, 400)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestACLView))
    return suite


if __name__ == '__main__':
    unittest.main()

