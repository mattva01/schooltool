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
Unit tests for schooltool.browser.model

$Id$
"""

import unittest

from schooltool.browser.tests import RequestStub, setPath
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestPersonInfo(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.root = app['groups'].new("root", title="root")
        self.person = app['persons'].new("johndoe", title="John Doe")

        Membership(group=self.root, member=self.person)

    def test(self):
        from schooltool.browser.app import PersonView
        view = PersonView(self.person)
        request = RequestStub(authenticated_user='not None')
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('johndoe' in result)
        self.assert_('John Doe' in result)

    def test_traverse(self):
        from schooltool.browser.model import PersonView, PhotoView
        view = PersonView(self.person)
        photoview = view._traverse('photo.jpg', RequestStub())
        self.assert_(photoview.context is self.person)
        self.assert_(isinstance(photoview, PhotoView))
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())

    def test_info(self):
        from schooltool.browser.model import PersonView
        from schooltool.component import FacetManager
        facet = FacetManager(self.person).facetByName('person_info')
        view = PersonView(self.person)
        self.assert_(view.info() is facet)

    def test_getParentGroups(self):
        from schooltool.browser.model import PersonView
        request = RequestStub()
        view = PersonView(self.person)
        self.assertEquals(view.getParentGroups(request),
                          [{'url': 'http://localhost:7001/groups/root',
                            'title': 'root'}])

    def test_photo(self):
        from schooltool.model import Person
        from schooltool.browser.model import PersonView
        from schooltool.component import FacetManager
        person = Person()
        setPath(person, '/persons/>me')
        facet = FacetManager(person).facetByName('person_info')
        facet.photo = ';-)'
        view = PersonView(person)
        view.request = RequestStub(authenticated_user='not None')
        markup = view.photo()
        self.assertEquals(markup, '<img src="http://localhost:7001/persons/'
                                                      '&gt;me/photo.jpg" />')

        facet.photo = None
        markup = view.photo()
        self.assertEquals(markup, '<i>N/A</i>')


class TestMembershipViewMixin(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.root = app['groups'].new("root", title="root")
        self.group = app['groups'].new("new", title="Teachers")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.root, member=self.group)
        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)

    def test(self):
        from schooltool.browser.model import GroupView
        view = GroupView(self.group)
        request = RequestStub(authenticated_user='not None')
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('Teachers' in result)

    def test_getOtherMembers(self):
        from schooltool.browser.model import GroupView
        request = RequestStub()
        view = GroupView(self.group)
        self.assertEquals(view.getOtherMembers(request),
                          [{'url': 'http://localhost:7001/persons/p',
                            'title': 'Pete'}])

    def test_getSubGroups(self):
        from schooltool.browser.model import GroupView
        request = RequestStub()
        view = GroupView(self.group)
        self.assertEquals(view.getSubGroups(request),
                          [{'url': 'http://localhost:7001/groups/sub',
                            'title': 'subgroup'}])

    def test_getParentGroups(self):
        from schooltool.browser.model import GroupView
        request = RequestStub()
        view = GroupView(self.group)
        self.assertEquals(view.getParentGroups(request),
                          [{'url': 'http://localhost:7001/groups/root',
                            'title': 'root'}])


class TestPhotoView(unittest.TestCase):

    def createView(self, photo):
        from schooltool.model import Person
        from schooltool.browser.model import PhotoView
        from schooltool.component import FacetManager
        person = Person()
        facet = FacetManager(person).facetByName('person_info')
        facet.photo = photo
        return PhotoView(person)

    def test(self):
        view = self.createView(';-)')
        request = RequestStub(authenticated_user='not None')
        photo = view.render(request)
        self.assertEquals(request.headers['content-type'], 'image/jpeg')
        self.assertEquals(photo, ';-)')

    def test_nophoto(self):
        view = self.createView(None)
        request = RequestStub(authenticated_user='not None')
        self.assertRaises(ValueError, view.render, request)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfo))
    suite.addTest(unittest.makeSuite(TestMembershipViewMixin))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    return suite


if __name__ == '__main__':
    unittest.main()
