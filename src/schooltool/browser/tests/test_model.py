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
import datetime
from logging import INFO

from schooltool.browser.tests import RequestStub, setPath, TraversalTestMixin
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestPersonView(TraversalTestMixin, RegistriesSetupMixin,
                     unittest.TestCase):

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
        self.managers = app['groups'].new("managers", title="managers")
        self.person = app['persons'].new("johndoe", title="John Doe")
        self.manager = app['persons'].new("manager", title="Manager")

        Membership(group=self.root, member=self.person)
        Membership(group=self.managers, member=self.manager)

    def test(self):
        from schooltool.browser.app import PersonView
        view = PersonView(self.person)
        request = RequestStub(authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('johndoe' in result)
        self.assert_('John Doe' in result)
        self.assert_('edit.html' not in result)

    def test_manager(self):
        from schooltool.browser.app import PersonView
        view = PersonView(self.person)
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('johndoe' in result)
        self.assert_('John Doe' in result)
        self.assert_('edit.html' in result)

    def test_traverse(self):
        from schooltool.browser.model import PersonView, PhotoView
        from schooltool.browser.model import PersonEditView
        view = PersonView(self.person)
        self.assertTraverses(view, 'photo.jpg', PhotoView, self.person)
        self.assertTraverses(view, 'edit.html', PersonEditView, self.person)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())

    def test_getParentGroups(self):
        from schooltool.browser.model import PersonView
        request = RequestStub()
        view = PersonView(self.person)
        self.assertEquals(view.getParentGroups(request),
                          [{'url': 'http://localhost:7001/groups/root',
                            'title': 'root'}])



class TestPersonEditView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.model import PersonEditView
        from schooltool.component import FacetManager
        from schooltool.model import Person

        self.person = Person()
        self.person.title = "Mr. Wise Guy"
        setPath(self.person, '/persons/somebody')
        self.info = FacetManager(self.person).facetByName('person_info')
        return PersonEditView(self.person)

    def test_post(self):
        view = self.createView()
        request = RequestStub(args={'first_name': 'I Changed \xc4\x85',
                                    'last_name': 'My Name \xc4\x8d Recently',
                                    'date_of_birth': '2004-08-05',
                                    'comment': 'For some \xc4\x99 reason.',
                                    'photo': 'P6\n1 1\n255\n\xff\xff\xff'})
        view.do_POST(request)

        self.assertEquals(request.applog,
            [(None, u'Photo added on Mr. Wise Guy (/persons/somebody)', INFO),
             (None, u'Person info updated on I Changed \u0105'
                    u' My Name \u010d Recently (/persons/somebody)', INFO)])

        self.assertEquals(self.info.first_name, u'I Changed \u0105')
        self.assertEquals(self.info.last_name, u'My Name \u010d Recently')
        self.assertEquals(self.info.date_of_birth, datetime.date(2004, 8, 5))
        self.assertEquals(self.info.comment, u'For some \u0119 reason.')
        self.assert_('JFIF' in self.info.photo)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody')

        # Check that the photo doesn't get removed.
        request = RequestStub(args={'first_name': 'I Changed',
                                    'last_name': 'My Name Recently',
                                    'date_of_birth': '2004-08-06',
                                    'comment': 'For various reasons.',
                                    'photo': ''})
        view.do_POST(request)
        self.assertEquals(request.applog,
            [(None, u'Person info updated on I Changed'
                    u' My Name Recently (/persons/somebody)', INFO)])
        self.assertEquals(self.info.date_of_birth, datetime.date(2004, 8, 6))
        self.assert_('JFIF' in self.info.photo)

        # Empty dates are explicitly allowed
        request = RequestStub(args={'first_name': 'I Changed',
                                    'last_name': 'My Name Recently',
                                    'date_of_birth': '',
                                    'comment': 'For various reasons.',
                                    'photo': ''})
        view.do_POST(request)
        self.assertEquals(request.applog,
            [(None, u'Person info updated on I Changed'
                    u' My Name Recently (/persons/somebody)', INFO)])
        self.assert_(self.info.date_of_birth is None)

    def test_post_errors(self):
        for dob in ['bwahaha', '2004-13-01', '2004-08-05-01']:
            view = self.createView()
            request = RequestStub(args={'first_name': 'I Changed',
                                        'last_name': 'My Name Recently',
                                        'date_of_birth': dob,
                                        'comment': 'For various reasons.',
                                        'photo': 'P6\n1 1\n255\n\xff\xff\xff'})
            body = view.do_POST(request)
            self.assert_('Invalid date' in body)

        view = self.createView()
        request = RequestStub(args={'first_name': 'I Changed',
                                    'last_name': 'My Name Recently',
                                    'date_of_birth': '2004-08-05',
                                    'comment': 'For various reasons.',
                                    'photo': 'eeevill'})
        body = view.do_POST(request)
        self.assert_('Invalid photo' in body, body)


class TestPersonInfoMixin(unittest.TestCase):

    def test_info(self):
        from schooltool.browser.model import PersonInfoMixin
        from schooltool.component import FacetManager
        from schooltool.model import Person

        mixin = PersonInfoMixin()
        mixin.context = Person()
        self.assert_(mixin.info() is
                     FacetManager(mixin.context).facetByName('person_info'))

    def test_photoURL(self):
        from schooltool.browser.model import PersonInfoMixin
        from schooltool.component import FacetManager
        from schooltool.model import Person

        person = Person()
        setPath(person, '/persons/>me')
        facet = FacetManager(person).facetByName('person_info')
        facet.photo = ';-)'
        mixin = PersonInfoMixin()
        mixin.context = person
        mixin.request = RequestStub()
        self.assertEquals(mixin.photoURL(),
                          'http://localhost:7001/persons/&gt;me/photo.jpg')

        facet.photo = None
        self.assertEquals(mixin.photoURL(), '')



class TestGroupView(RegistriesSetupMixin, unittest.TestCase):

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


class TestGroupEditView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        self.root = app['groups'].new("root", title="root")
        self.group = app['groups'].new("new", title="Teachers")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.group2 = app['groups'].new("group2", title="Random group")
        self.per = app['persons'].new("p", title="Pete")
        self.per2 = app['persons'].new("j", title="John")
        self.per3 = app['persons'].new("lj", title="Longjohn")
        self.res = app['resources'].new("hall", title="Hall")

        Membership(group=self.root, member=self.group)
        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.group, member=self.per2)

    def test(self):
        from schooltool.browser.model import GroupEditView
        view = GroupEditView(self.group)
        view.authorization = lambda x, y: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('Pete' in result, result)

    def test_list(self):
        from schooltool.browser.model import GroupEditView
        view = GroupEditView(self.group)
        request = RequestStub()
        self.assertEquals(
            view.list(request),
            [('Group', 'subgroup', '/groups/sub',
              'http://localhost:7001/groups/sub'),
             ('Person', 'John', '/persons/j',
              'http://localhost:7001/persons/j'),
             ('Person', 'Pete', '/persons/p',
              'http://localhost:7001/persons/p'),
             ])

    def test_addList(self):
        from schooltool.browser.model import GroupEditView
        view = GroupEditView(self.group)
        request = RequestStub(args={'SEARCH': ''})
        self.assertEquals(
            view.addList(request),
            [('Group', 'Random group', '/groups/group2',
              'http://localhost:7001/groups/group2'),
             ('Group', 'Teachers', '/groups/new',
              'http://localhost:7001/groups/new'),
             ('Group', 'root', '/groups/root',
              'http://localhost:7001/groups/root'),
             ('Person', 'Longjohn', '/persons/lj',
              'http://localhost:7001/persons/lj'),
             ('Resource', 'Hall', '/resources/hall',
              'http://localhost:7001/resources/hall')
             ])

        request = RequestStub(args={'SEARCH': 'john'})
        self.assertEquals(
            view.addList(request),
            [('Person', 'Longjohn', '/persons/lj',
            'http://localhost:7001/persons/lj')])

    def test_update_DELETE(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = GroupEditView(self.group)
        request = RequestStub(args={"DELETE":"Remove them",
                                    "CHECK": ['/groups/sub', '/persons/p']})
        view.update(request)
        self.assertEquals(getRelatedObjects(self.group, URIMember),
                          [self.per2])

    def test_update_ADD(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = GroupEditView(self.group)
        request = RequestStub(args={"FINISH_ADD":"Add selected",
                                    "CHECK": ['/groups/group2',
                                              '/persons/lj']})
        view.update(request)
        members = getRelatedObjects(self.group, URIMember)
        assert self.group2 in members
        assert self.per3 in members


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
    suite.addTest(unittest.makeSuite(TestPersonInfoMixin))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestPersonEditView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestGroupEditView))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    return suite


if __name__ == '__main__':
    unittest.main()
