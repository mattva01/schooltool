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

from schooltool.browser.tests import RequestStub, setPath
from schooltool.browser.tests import TraversalTestMixin, AppSetupMixin
from schooltool.tests.utils import RegistriesSetupMixin, NiceDiffsMixin
from schooltool.tests.helpers import sorted

__metaclass__ = type


class UserStub:
    title = 'Mango'

    def listLinks(self, uri):
        return []


class TestPersonView(TraversalTestMixin, AppSetupMixin, NiceDiffsMixin,
                     unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

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
        self.assert_('password.html' in result)

    def test_otheruser(self):
        from schooltool.browser.app import PersonView
        view = PersonView(self.person)
        request = RequestStub(authenticated_user=self.person2)
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('johndoe' in result)
        self.assert_('John Doe' in result)
        self.assert_('edit.html' not in result)
        self.assert_('password.html' not in result)

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
        self.assert_('password.html' in result)

    def test_traverse(self):
        from schooltool.browser.model import PersonView, PhotoView
        from schooltool.browser.model import PersonEditView, PersonPasswordView
        from schooltool.browser.timetable import TimetableTraverseView
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.browser.cal import WeeklyCalendarView
        from schooltool.browser.cal import MonthlyCalendarView
        from schooltool.rest.cal import CalendarView as RestCalendarView
        from schooltool.rest.cal import CalendarReadView as RestCalReadView
        view = PersonView(self.person)
        self.assertTraverses(view, 'photo.jpg', PhotoView, self.person)
        self.assertTraverses(view, 'edit.html', PersonEditView, self.person)
        self.assertTraverses(view, 'password.html', PersonPasswordView,
                             self.person)
        self.assertTraverses(view, 'timetables', TimetableTraverseView,
                             self.person)
        self.assertTraverses(view, 'calendar_daily.html', DailyCalendarView,
                             self.person.calendar)
        self.assertTraverses(view, 'calendar_weekly.html', WeeklyCalendarView,
                             self.person.calendar)
        self.assertTraverses(view, 'calendar_monthly.html',
                             MonthlyCalendarView, self.person.calendar)
        self.assertTraverses(view, 'calendar.ics',
                             RestCalendarView, self.person.calendar)
        self.assertTraverses(view, 'timetable-calendar.ics',
                             RestCalReadView)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())

    def test_getParentGroups(self):
        from schooltool.browser.model import PersonView
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.getParentGroups(), [self.root])

    def test_editURL(self):
        from schooltool.browser.model import PersonView
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.editURL(),
                          'http://localhost:7001/persons/johndoe/edit.html')

    def test_passwordURL(self):
        from schooltool.browser.model import PersonView
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.passwordURL(),
                'http://localhost:7001/persons/johndoe/password.html')

    def test_calendarURL(self):
        from schooltool.browser.model import PersonView
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.calendarURL(),
                'http://localhost:7001/persons/johndoe/calendar_weekly.html')

    def test_timetables(self):
        from schooltool.browser.model import PersonView
        from schooltool.timetable import Timetable
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.timetables(), [])

        view.context.timetables['2004-spring', 'default'] = Timetable([])
        view.context.timetables['2004-spring', 'another'] = Timetable([])
        view.context.timetables['2003-fall', 'another'] = Timetable([])
        self.root.timetables['2003-fall', 'default'] = Timetable([])
        pp = 'http://localhost:7001/persons/johndoe'
        self.assertEquals(view.timetables(),
                          [{'title': '2003-fall, another',
                            'url': '%s/timetables/2003-fall/another' % pp},
                           {'title': '2003-fall, default',
                            'url': '%s/timetables/2003-fall/default' % pp},
                           {'title': '2004-spring, another',
                            'url': '%s/timetables/2004-spring/another' % pp},
                           {'title': '2004-spring, default',
                            'url': '%s/timetables/2004-spring/default' % pp}])


class TestPersonPasswordView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def test_as_user(self):
        from schooltool.browser.model import PersonPasswordView
        view = PersonPasswordView(self.person)
        request = RequestStub(authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('old_password' in result)
        self.assert_('new_password' in result)
        self.assert_('verify_password' in result)
        self.assert_('Current password' in result)

    def test_as_manager(self):
        from schooltool.browser.model import PersonPasswordView
        view = PersonPasswordView(self.person)
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('old_password' in result)
        self.assert_('new_password' in result)
        self.assert_('verify_password' in result)
        self.assert_("Manager's password" in result)

    def test_locked(self):
        from schooltool.browser.model import PersonPasswordView
        view = PersonPasswordView(self.person)
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('disabled' in result)

    def test_unlocked(self):
        from schooltool.browser.model import PersonPasswordView
        self.person.setPassword('something')
        view = PersonPasswordView(self.person)
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('enabled' in result)

    def test_POST_as_manager(self):
        from schooltool.browser.model import PersonPasswordView
        self.manager.setPassword('mgrpw')
        view = PersonPasswordView(self.person)
        request = RequestStub(method='POST', args={'old_password': 'mgrpw',
                                                   'new_password': 'newpw',
                                                   'verify_password': 'newpw',
                                                   'CHANGE': 'change'},
                              authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('Password changed' in result)
        self.assert_(self.person.checkPassword('newpw'))
        self.assertEquals(request.applog,
                          [(self.manager,
                            "Password changed for John Doe (/persons/johndoe)",
                            INFO)])

    def test_POST_as_user(self):
        from schooltool.browser.model import PersonPasswordView
        self.person.setPassword('oldpw')
        view = PersonPasswordView(self.person)
        request = RequestStub(method='POST', args={'old_password': 'oldpw',
                                                   'new_password': 'newpw',
                                                   'verify_password': 'newpw',
                                                   'CHANGE': 'change'},
                              authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('Password changed' in result)
        self.assert_(self.person.checkPassword('newpw'))
        self.assertEquals(request.applog,
                          [(self.person,
                            "Password changed for John Doe (/persons/johndoe)",
                            INFO)])

    def test_POST_passwords_do_not_match(self):
        from schooltool.browser.model import PersonPasswordView
        self.person.setPassword('oldpw')
        view = PersonPasswordView(self.person)
        request = RequestStub(method='POST', args={'old_password': 'oldpw',
                                                   'new_password': 'newpw',
                                                   'verify_password': 'newwp',
                                                   'CHANGE': 'change'},
                              authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('Passwords do not match' in result)
        self.assert_(self.person.checkPassword('oldpw'))

    def test_POST_bad_old_passwod(self):
        from schooltool.browser.model import PersonPasswordView
        self.person.setPassword('oldpw')
        view = PersonPasswordView(self.person)
        request = RequestStub(method='POST', args={'old_password': 'dunno',
                                                   'new_password': 'newpw',
                                                   'verify_password': 'newwp',
                                                   'CHANGE': 'change'},
                              authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('Incorrect password for' in result)
        self.assert_(self.person.checkPassword('oldpw'))

    def test_POST_disable_account(self):
        from schooltool.browser.model import PersonPasswordView
        self.person.setPassword('oldpw')
        self.manager.setPassword('mgrpw')
        view = PersonPasswordView(self.person)
        request = RequestStub(method='POST', args={'old_password': 'mgrpw',
                                                   'new_password': 'newpw',
                                                   'verify_password': 'newpw',
                                                   'DISABLE': 'disable'},
                              authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_('Account disabled' in result)
        self.assert_(not self.person.hasPassword())
        self.assertEquals(request.applog,
                          [(self.manager,
                            "Account disabled for John Doe (/persons/johndoe)",
                            INFO)])


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

    def test_get(self):
        view = self.createView()
        view.authorization = lambda x, y: True
        request = RequestStub()
        result = view.render(request)
        self.assert_('Mr. Wise Guy' in result)

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
        setPath(person, '/persons/me')
        facet = FacetManager(person).facetByName('person_info')
        facet.photo = ';-)'
        mixin = PersonInfoMixin()
        mixin.context = person
        mixin.request = RequestStub()
        self.assertEquals(mixin.photoURL(),
                          'http://localhost:7001/persons/me/photo.jpg')

        facet.photo = None
        self.assertEquals(mixin.photoURL(), '')


class TestGroupView(RegistriesSetupMixin, TraversalTestMixin,
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
        self.group = app['groups'].new("new", title="Teachers")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.root, member=self.group)
        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)

    def test(self):
        from schooltool.browser.model import GroupView
        view = GroupView(self.group)
        request = RequestStub(authenticated_user=UserStub())
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        assert 'Teachers' in result, result

    def test_getOtherMembers(self):
        from schooltool.browser.model import GroupView
        view = GroupView(self.group)
        view.request = RequestStub()
        self.assertEquals(view.getOtherMembers(), [self.per])

    def test_getSubGroups(self):
        from schooltool.browser.model import GroupView
        view = GroupView(self.group)
        view.request = RequestStub()
        self.assertEquals(view.getSubGroups(), [self.sub])

    def test_getParentGroups(self):
        from schooltool.browser.model import GroupView
        view = GroupView(self.group)
        view.request = RequestStub()
        self.assertEquals(view.getParentGroups(), [self.root])

    def test_teachersList(self):
        from schooltool.browser.model import GroupView
        from schooltool.teaching import Teaching, setUp
        from schooltool.relationship import setUp as setUpRel
        setUpRel(); setUp()
        Teaching(teacher=self.per, taught=self.group)
        view = GroupView(self.group)
        view.request = RequestStub(authenticated_user=UserStub())
        self.assertEquals(view.teachersList(), [self.per])

    def test_traverse(self):
        from schooltool.browser.model import GroupView, GroupEditView
        from schooltool.browser.model import GroupTeachersView
        from schooltool.browser.timetable import TimetableTraverseView
        request = RequestStub()
        view = GroupView(self.group)
        self.assertTraverses(view, 'edit.html', GroupEditView, self.group)
        self.assertTraverses(view, 'teachers.html',
                             GroupTeachersView, self.group)
        self.assertTraverses(view, 'timetables', TimetableTraverseView,
                             self.group)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())

    def test_timetables(self):
        from schooltool.browser.model import GroupView
        from schooltool.timetable import Timetable
        view = GroupView(self.group)
        view.request = RequestStub()
        self.assertEquals(view.timetables(), [])

        view.context.timetables['2004-spring', 'default'] = Timetable([])
        view.context.timetables['2004-spring', 'another'] = Timetable([])
        view.context.timetables['2003-fall', 'another'] = Timetable([])
        self.root.timetables['2003-fall', 'default'] = Timetable([])
        pp = 'http://localhost:7001/groups/new'
        self.assertEquals(view.timetables(),
                          [{'title': '2003-fall, another',
                            'url': '%s/timetables/2003-fall/another' % pp},
                           {'title': '2003-fall, default',
                            'url': '%s/timetables/2003-fall/default' % pp},
                           {'title': '2004-spring, another',
                            'url': '%s/timetables/2004-spring/another' % pp},
                           {'title': '2004-spring, default',
                            'url': '%s/timetables/2004-spring/default' % pp}])


class TestGroupEditView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        from schooltool import relationship
        self.setUpRegistries()
        membership.setUp()
        relationship.setUp()
        app = Application()
        self.app = app
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
        view.request = RequestStub()
        self.assertEquals(view.list(),
                          [self.per2, self.per, self.sub])

    def test_addList(self):
        from schooltool.browser.model import GroupEditView
        view = GroupEditView(self.group)
        view.request = RequestStub(args={'SEARCH': ''})
        self.assertEquals(view.addList(),
                          [self.group2, self.group, self.root,
                           self.per3, self.res])

        view.request = RequestStub(args={'SEARCH': 'john'})
        self.assertEquals(view.addList(), [self.per3])

    def test_update_DELETE(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = GroupEditView(self.group)
        request = RequestStub(args={"DELETE":"Remove them",
                                    "CHECK": ['/groups/sub', '/persons/p']})
        view.request = request
        view.update()
        self.assertEquals(getRelatedObjects(self.group, URIMember),
                          [self.per2])
        self.assertEquals(sorted(request.applog),
                [(None,
                  "Relationship 'Membership' between "
                  "/groups/sub and /groups/new removed", INFO),
                 (None,
                  "Relationship 'Membership' between "
                  "/persons/p and /groups/new removed", INFO)])

    def test_update_ADD(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = GroupEditView(self.group)
        request = RequestStub(args={"FINISH_ADD":"Add selected",
                                    "toadd": ['/groups/group2',
                                              '/persons/lj']})
        view.request = request
        view.update()
        members = getRelatedObjects(self.group, URIMember)
        assert self.group2 in members
        assert self.per3 in members
        self.assertEquals(sorted(request.applog),
                [(None,
                  "Relationship 'Membership' between "
                  "/groups/group2 and /groups/new created", INFO),
                 (None,
                  "Relationship 'Membership' between "
                  "/persons/lj and /groups/new created", INFO)])


class TestGroupTeachersView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool.teaching import Teaching
        from schooltool import membership
        from schooltool import relationship
        from schooltool import teaching
        self.setUpRegistries()
        membership.setUp()
        relationship.setUp()
        teaching.setUp()
        app = Application()
        self.app = app
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        self.root = app['groups'].new("root", title="root")
        self.group = app['groups'].new("new", title="Group")
        self.per = app['persons'].new("p", title="Pete")
        self.per3 = app['persons'].new("lj", title="Longjohn")
        self.teachers = self.app['groups'].new('teachers', title='Teachers')
        self.teacher = self.app['persons'].new('josh', title='Josh')

        Membership(group=self.root, member=self.group)
        Membership(group=self.group, member=self.per)
        Membership(group=self.teachers, member=self.teacher)
        Teaching(teacher=self.per3, taught=self.group)

    def test(self):
        from schooltool.browser.model import GroupTeachersView
        view = GroupTeachersView(self.group)
        view.authorization = lambda x, y: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('Group' in result, result)

    def test_teachersList(self):
        from schooltool.browser.model import GroupTeachersView
        view = GroupTeachersView(self.group)
        view.request = RequestStub(authenticated_user=UserStub())
        self.assertEquals(view.list(), [self.per3])

    def test_addList(self):
        from schooltool.browser.model import GroupTeachersView
        from schooltool.membership import Membership
        view = GroupTeachersView(self.group)
        view.request = RequestStub()
        self.assertEquals(view.addList(), [self.teacher])

    def test_update_DELETE(self):
        from schooltool.browser.model import GroupTeachersView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URITeacher
        view = GroupTeachersView(self.group)
        view.request = RequestStub(args={"DELETE":"Remove them",
                                         "CHECK": ['/persons/lj']})
        view.update()
        self.assertEquals(getRelatedObjects(self.group, URITeacher),
                          [])
        self.assertEquals(view.request.applog,
                [(None,
                  "Relationship 'Teaching' between "
                  "/persons/lj and /groups/new removed", INFO)])

    def test_update_ADD(self):
        from schooltool.browser.model import GroupTeachersView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URITeacher
        view = GroupTeachersView(self.group)
        view.request = RequestStub(args={"FINISH_ADD":"Add selected",
                                         "toadd": '/persons/josh'})
        view.update()
        teachers = getRelatedObjects(self.group, URITeacher)
        assert self.teacher in teachers, teachers
        assert self.per3 in teachers, teachers
        self.assertEquals(view.request.applog,
                [(None,
                  "Relationship 'Teaching' between "
                  "/persons/josh and /groups/new created", INFO)])


class TestResourceView(unittest.TestCase, TraversalTestMixin,):

    def test(self):
        from schooltool.model import Resource
        from schooltool.browser.model import ResourceView
        resource = Resource("I'm a resource")
        resource.__name__ = 're123'
        view = ResourceView(resource)
        view.authorization = lambda x, y: True
        request = RequestStub()
        content = view.render(request)

        self.assert_("I'm a resource" in content)
        self.assert_("re123" in content)

    def test_editURL(self):
        from schooltool.model import Resource
        from schooltool.browser.model import ResourceView
        resource = Resource("I'm a resource")
        setPath(resource, '/resources/foo')
        view = ResourceView(resource)
        view.request = RequestStub()
        self.assertEquals(view.editURL(),
                          'http://localhost:7001/resources/foo/edit.html')

    def test_traverse(self):
        from schooltool.model import Resource
        from schooltool.browser.model import ResourceView, ResourceEditView
        from schooltool.browser.cal import BookingView
        resource = Resource()
        view = ResourceView(resource)
        self.assertTraverses(view, 'edit.html', ResourceEditView, resource)
        self.assertTraverses(view, 'book', BookingView, resource)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestResourceEditView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.model import ResourceEditView
        from schooltool.model import Resource
        resource = self.resource = Resource(title=u"Foo resource bar")
        setPath(resource, '/resources/foo')
        view = ResourceEditView(resource)
        view.authorization = lambda x, y: True
        return view

    def test_get(self):
        view = self.createView()
        request = RequestStub()
        content = view.render(request)
        self.assert_("Foo resource bar" in content)

    def test_post(self):
        view = self.createView()
        request = RequestStub(args={'title': 'New \xc4\x85'})
        view.do_POST(request)
        self.assertEquals(self.resource.title, u'New \u0105')
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/resources/foo')
        self.assertEquals(request.applog,
                          [(None, 'Resource /resources/foo modified', INFO)])


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
        view = self.createView(';-) \xff')
        request = RequestStub(authenticated_user='not None')
        photo = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'], 'image/jpeg')
        self.assertEquals(photo, ';-) \xff')

    def test_nophoto(self):
        view = self.createView(None)
        request = RequestStub(authenticated_user='not None')
        result = view.render(request)
        self.assertEquals(request.code, 404)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfoMixin))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestPersonEditView))
    suite.addTest(unittest.makeSuite(TestPersonPasswordView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestGroupEditView))
    suite.addTest(unittest.makeSuite(TestGroupTeachersView))
    suite.addTest(unittest.makeSuite(TestResourceView))
    suite.addTest(unittest.makeSuite(TestResourceEditView))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    return suite


if __name__ == '__main__':
    unittest.main()
