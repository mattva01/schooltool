#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.browser.acl

$Id$
"""

import unittest
from logging import INFO

from schooltool.browser.tests import RequestStub
from schooltool.tests.utils import AppSetupMixin, NiceDiffsMixin
from schooltool.common import dedent

__metaclass__ = type


class TestACLView(AppSetupMixin, NiceDiffsMixin, unittest.TestCase):

    def createView(self):
        from schooltool.browser.acl import ACLView
        return ACLView(self.person2.calendar.acl)

    def test(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)

    def test_list(self):
        from schooltool.interfaces import Everybody
        from schooltool.interfaces import ViewPermission, AddPermission
        view = self.createView()
        view.request = RequestStub(authenticated_user=self.manager)
        grants = view.list()

        result = "\n".join(["%(title)s | %(permission)-6s | %(value)s" % item
                            for item in grants])
        expected = dedent("""
            Not John Doe | Add    | Add:/persons/notjohn
            Not John Doe | Modify | Modify:/persons/notjohn
            Not John Doe | View   | View:/persons/notjohn
        """).strip()
        self.assertEquals(result, expected)

        view.context.add((self.person, AddPermission))
        view.context.add((Everybody, ViewPermission))
        grants = view.list()
        result = "\n".join(["%(title)-12s | %(permission)-6s | %(value)s"
                            % item for item in grants])
        expected = dedent("""
            John Doe     | Add    | Add:/persons/johndoe
            Not John Doe | Add    | Add:/persons/notjohn
            Not John Doe | Modify | Modify:/persons/notjohn
            Not John Doe | View   | View:/persons/notjohn
            Everybody    | View   | View:Everybody
        """).strip()
        self.assertEquals(result, expected)
        self.assertEquals([item['url'] for item in grants],
                          ['http://localhost:7001/persons/johndoe'] +
                          ['http://localhost:7001/persons/notjohn'] * 3 +
                          [None])

    def test_update_delete(self):
        from schooltool.interfaces import ViewPermission
        view = self.createView()
        view.context.add((self.person, ViewPermission))
        assert view.context.allows(self.person, ViewPermission)
        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'DELETE': 'revoke',
                                         'CHECK': ['View:/persons/johndoe',
                                                   'Edit:/no/such/thing']})
        result = view.update()
        assert not view.context.allows(self.person, ViewPermission)
        self.assertEquals(view.request.applog,
                          [(self.manager,
                           'Revoked permission View on'
                           ' /persons/notjohn/calendar/acl from'
                           ' /persons/johndoe (John Doe)', INFO)])
        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'DELETE': 'revoke'})
        result = view.update()

    def test_update_delete_Everybody(self):
        from schooltool.interfaces import ViewPermission, Everybody
        view = self.createView()
        view.context.add((Everybody, ViewPermission))
        assert view.context.allows(Everybody, ViewPermission)
        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'DELETE': 'revoke',
                                         'CHECK': 'View:Everybody'})
        result = view.update()
        assert not view.context.allows(Everybody, ViewPermission)
        self.assertEquals(view.request.applog,
                          [(self.manager,
                           'Revoked permission View on'
                           ' /persons/notjohn/calendar/acl from'
                           ' Everybody', INFO)])
        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'DELETE': 'revoke'})
        result = view.update()

    def test_update_add(self):
        from schooltool.interfaces import ViewPermission
        view = self.createView()
        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'ADD': 'add',
                                         'user': '/persons/johndoe',
                                         'permission': 'View'})
        result = view.update()
        assert view.context.allows(self.person, ViewPermission), result
        self.assertEquals(view.request.applog,
                          [(self.manager,
                           'Granted permission View on'
                           ' /persons/notjohn/calendar/acl to'
                           ' /persons/johndoe (John Doe)', INFO)])
        self.assertEquals(result,
                          'Granted permission View to'
                          ' /persons/johndoe (John Doe)')
        result = view.update()
        self.assertEquals(result, 'John Doe already has permission View')

        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'ADD': 'grant permission',
                                         'user': ''})
        result = view.update()
        self.assertEquals(view.user_widget.error,
                          "Please select a user")
        self.assertEquals(view.request.applog, [])

        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'ADD': 'grant permission',
                                         'user':'foo', 'permission': ''})
        result = view.update()
        self.assertEquals(view.permission_widget.error,
                          "Please select a permission")

    def test_update_add_Everybody(self):
        from schooltool.interfaces import ViewPermission, Everybody
        view = self.createView()
        view.request = RequestStub(authenticated_user=self.manager,
                                   args={'ADD': 'add',
                                         'user': 'Everybody',
                                         'permission': 'View'})
        result = view.update()
        assert view.context.allows(Everybody, ViewPermission), result


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestACLView))
    return suite


if __name__ == '__main__':
    unittest.main()
