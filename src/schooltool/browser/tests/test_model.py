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

from zope.interface import implements
from zope.app.traversing.api import getPath
from zope.testing import doctest

from schooltool.interfaces import IPerson, IGroup, IResource
from schooltool.browser.tests import HTMLDocument
from schooltool.browser.tests import RequestStub, setPath
from schooltool.browser.tests import TraversalTestMixin
from schooltool.tests.utils import NiceDiffsMixin
from schooltool.tests.utils import AppSetupMixin, SchoolToolSetup
from schooltool.tests.helpers import sorted

__metaclass__ = type


#
# Stubs
#

class UnknownObjectStub:

    def __init__(self, name=None, title=None):
        self.__name__ = name
        self.title = title


class PersonStub(UnknownObjectStub):
    implements(IPerson)


class GroupStub(UnknownObjectStub):
    implements(IGroup)


class ResourceStub(UnknownObjectStub):
    implements(IResource)


class UserStub:
    title = 'Mango'
    __name__ = 'mango'

    def listLinks(self, uri):
        return []


#
# Tests
#

class TestPersonView(TraversalTestMixin, AppSetupMixin, NiceDiffsMixin,
                     unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

        from schooltool import relationship
        relationship.setUp()

        from schooltool.cal import SchooldayModel
        from schooltool.timetable import Timetable
        self.app.timePeriodService['2003-fall'] = SchooldayModel(
                datetime.date(2003, 9, 1), datetime.date(2003, 12, 31))
        self.app.timePeriodService['2004-spring'] = SchooldayModel(
                datetime.date(2004, 1, 1), datetime.date(2004, 5, 31))
        self.app.timetableSchemaService['default'] = Timetable([])
        self.app.timetableSchemaService['another'] = Timetable([])

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
        self.assert_('Merge calendars' not in result)

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
        from schooltool.browser.cal import CalendarView
        from schooltool.rest.cal import CalendarView as RestCalendarView
        from schooltool.rest.cal import CalendarReadView as RestCalReadView
        view = PersonView(self.person)
        self.assertTraverses(view, 'photo.jpg', PhotoView, self.person)
        self.assertTraverses(view, 'edit.html', PersonEditView, self.person)
        self.assertTraverses(view, 'password.html', PersonPasswordView,
                             self.person)
        self.assertTraverses(view, 'timetables', TimetableTraverseView,
                             self.person)
        self.assertTraverses(view, 'calendar', CalendarView,
                             self.person.calendar)
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

    def test_timetables(self):
        from schooltool.browser.model import PersonView
        from schooltool.timetable import Timetable
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.timetables(), [])

        view.context.timetables['2004-spring', 'default'] = Timetable([])
        view.context.timetables['2003-fall', 'another'] = Timetable([])
        self.root.timetables['2003-fall', 'default'] = Timetable([])
        pp = 'http://localhost:7001/persons/johndoe'
        self.assertEquals(view.timetables(),
                          [{'title': '2003-fall, another',
                            'url': '%s/timetables/2003-fall/another' % pp,
                            'empty': False},
                           {'title': '2003-fall, default',
                            'url': '%s/timetables/2003-fall/default' % pp,
                            'empty': False},
                           {'title': '2004-spring, default',
                            'url': '%s/timetables/2004-spring/default' % pp,
                            'empty': False}])

    def test_dynamicfacets(self):
        from schooltool.browser.model import PersonView
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.getDynamicFacets(), [])

    def test_timetables_empty(self):
        from schooltool.browser.model import PersonView
        from schooltool.timetable import Timetable
        view = PersonView(self.person)
        view.request = RequestStub()
        self.assertEquals(view.timetables(), [])

        view.context.timetables['2004-spring', 'default'] = Timetable([])
        view.context.timetables['2003-fall', 'another'] = Timetable([])
        self.root.timetables['2003-fall', 'default'] = Timetable([])
        pp = 'http://localhost:7001/persons/johndoe'
        self.assertEquals(view.timetables(True),
                          [{'title': '2003-fall, another',
                            'url': '%s/timetables/2003-fall/another' % pp,
                            'empty': False},
                           {'title': '2003-fall, default',
                            'url': '%s/timetables/2003-fall/default' % pp,
                            'empty': False},
                           {'title': '2004-spring, another',
                            'url': '%s/timetables/2004-spring/another' % pp,
                            'empty': True},
                           {'title': '2004-spring, default',
                            'url': '%s/timetables/2004-spring/default' % pp,
                            'empty': False}])

    def test_allObjects(self):
        from schooltool.browser.model import PersonView

        view = PersonView(self.person)
        view.getParentGroups = lambda: groups

        self.assert_(self.pupils in view.allGroups())
        self.assert_(self.pupils not in view.allPersons())
        self.assert_(self.pupils not in view.allResources())
        self.assert_(self.manager in view.allPersons())
        self.assert_(self.manager not in view.allGroups())
        self.assert_(self.manager not in view.allResources())

    def test_disabledResource(self):
        from schooltool.browser.model import PersonView

        view = PersonView(self.person)
        groups = [self.teachers, self.managers]
        view.getParentGroups = lambda: groups

        self.assertEquals('disabled', view.disabledResource(self.teachers))
        self.assertEquals(False, view.disabledResource(self.pupils))

    def test_POST(self):
        from schooltool.browser.model import PersonView
        from schooltool.timetable import Timetable
        from schooltool.uris import URICalendarProvider
        from schooltool.uris import URICalendarListed

        view = PersonView(self.person)
        groups = [self.teachers, self.managers, self.pupils]
        view.getParentGroups = lambda: groups

        self.assertEquals(len(view.context.listLinks(URICalendarProvider)), 0)
        self.assertEquals(len(view.context.listLinks(URICalendarListed)), 0)

        request = RequestStub(method='POST', args={'groups': 'teachers',
                                                   'groups': 'managers',
                                                   'CHOOSE_CALENDARS': ''},
                              authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(len(view.context.listLinks(URICalendarListed)), 1)

        request = RequestStub(method='POST', args={'CHOOSE_CALENDARS': ''},
                              authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(len(view.context.listLinks(URICalendarListed)), 0)

    def test_POST_unauthorized(self):
        from schooltool.browser.model import PersonView
        from schooltool.uris import URICalendarProvider
        view = PersonView(self.person)
        request = RequestStub(method='POST', args={'group.teachers': '',
                                                   'CHOOSE_CALENDARS': ''},
                              authenticated_user=self.person2)
        groups = [self.teachers, self.managers, self.pupils]
        view.getParentGroups = lambda: groups
        result = view.render(request)
        self.assertEquals(len(view.context.listLinks(URICalendarProvider)), 0)


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


class TestPersonEditView(SchoolToolSetup):

    def createView(self):
        from schooltool.browser.model import PersonEditView
        from schooltool.component import FacetManager
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Person

        app = self.app = Application()
        persons = app['persons'] = ApplicationObjectContainer(Person)
        self.person = persons.new('somebody', title="Mr. Wise Guy")
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
        view.request = request
        view.do_POST(request)

        self.assertEquals(request.applog,
            [(None, u'Person info updated on I Changed \u0105'
                    u' My Name \u010d Recently (/persons/somebody)', INFO),
             (None, u'Photo added on I Changed \u0105'
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

    def test_post_no_full_name(self):
        view = self.createView()
        request = RequestStub()
        view.request = request
        body = view.do_POST(request)
        assert 'required' in view.first_name_widget.error
        assert 'required' in view.last_name_widget.error
        assert not view.request.applog

    def test_post_full_name_conflict(self):
        from schooltool.component import FacetManager
        view = self.createView()
        other = self.app['persons'].new()
        infofacet = FacetManager(other).facetByName('person_info')
        infofacet.first_name = 'George'
        infofacet.last_name = 'William'
        request = RequestStub(args={'first_name': 'George',
                                    'last_name': 'William'})
        view.request = request
        body = view.do_POST(request)
        assert 'Another user with this name already exists.' in body
        assert not view.request.applog
        assert 'CONFIRM' in body

    def test_post_full_name_conflict_overriden_by_user(self):
        from schooltool.component import FacetManager
        view = self.createView()
        other = self.app['persons'].new()
        infofacet = FacetManager(other).facetByName('person_info')
        infofacet.first_name = 'George'
        infofacet.last_name = 'William'
        request = RequestStub(args={'first_name': 'George',
                                    'last_name': 'William',
                                    'CONFIRM': 'Yes, really do it'})
        view.request = request
        body = view.do_POST(request)
        self.assertEquals(request.applog,
            [(None, u'Person info updated on George William'
                    u' (/persons/somebody)', INFO)])

    def test_post_full_name_conflict_canceled(self):
        from schooltool.component import FacetManager
        view = self.createView()
        other = self.app['persons'].new()
        infofacet = FacetManager(other).facetByName('person_info')
        infofacet.first_name = 'George'
        infofacet.last_name = 'William'
        request = RequestStub(args={'first_name': 'George',
                                    'last_name': 'William',
                                    'CANCEL': 'No, never!'})
        view.request = request
        body = view.do_POST(request)
        self.assertEquals(request.applog, [])
        assert 'George' not in body

    def test_post_errors(self):
        for dob in ['bwahaha', '2004-13-01', '2004-08-05-01']:
            view = self.createView()
            request = RequestStub(args={'first_name': 'I Changed',
                                        'last_name': 'My Name Recently',
                                        'date_of_birth': dob,
                                        'comment': 'For various reasons.',
                                        'photo': 'P6\n1 1\n255\n\xff\xff\xff'})
            view.request = request
            body = view.do_POST(request)
            self.assert_('Invalid date' in body)

        view = self.createView()
        request = RequestStub(args={'first_name': 'I Changed',
                                    'last_name': 'My Name Recently',
                                    'date_of_birth': '2004-08-05',
                                    'comment': 'For various reasons.',
                                    'photo': 'eeevill'})
        view.request = request
        body = view.do_POST(request)
        self.assert_('Invalid photo' in body, body)

    def test_remove_photo(self):
        view = self.createView()
        self.info.photo = 'pretend this is jpeg'
        request = RequestStub(args={'first_name': 'I Changed',
                                    'last_name': 'My Name Recently',
                                    'date_of_birth': '2004-08-05',
                                    'comment': 'For some reason.',
                                    'REMOVE_PHOTO': 'remove'})
        view.request = request
        view.do_POST(request)
        self.assertEquals(request.applog,
            [(None, u'Person info updated on I Changed'
                    u' My Name Recently (/persons/somebody)', INFO),
             (None, u'Photo removed from I Changed'
                    u' My Name Recently (/persons/somebody)', INFO)])
        self.assert_(self.info.photo is None)


class TestPersonInfoMixin(SchoolToolSetup):

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


class TestGroupView(SchoolToolSetup, TraversalTestMixin, NiceDiffsMixin):

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
        self.community = app['groups'].new("community", title="Community")
        self.group = app['groups'].new("new", title="Teachers")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.community, member=self.group)
        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)

        from schooltool.cal import SchooldayModel
        from schooltool.timetable import Timetable
        app.timePeriodService['2003-fall'] = SchooldayModel(
                datetime.date(2003, 9, 1), datetime.date(2003, 12, 31))
        app.timePeriodService['2004-spring'] = SchooldayModel(
                datetime.date(2004, 1, 1), datetime.date(2004, 5, 31))
        app.timetableSchemaService['default'] = Timetable([])
        app.timetableSchemaService['another'] = Timetable([])

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
        self.assertEquals(view.getParentGroups(), [self.community])

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
        from schooltool.browser.model import GroupSubgroupView
        from schooltool.browser.model import GroupTeachersView
        from schooltool.browser.timetable import TimetableTraverseView
        from schooltool.browser.cal import CalendarView
        from schooltool.browser.acl import ACLView
        request = RequestStub()
        view = GroupView(self.group)
        self.assertTraverses(view, 'edit.html', GroupEditView, self.group)
        self.assertTraverses(view, 'edit_subgroups.html',
                             GroupSubgroupView, self.group)
        self.assertTraverses(view, 'teachers.html',
                             GroupTeachersView, self.group)
        self.assertTraverses(view, 'acl.html',
                             ACLView, self.group.acl)
        self.assertTraverses(view, 'calendar',
                             CalendarView, self.group.calendar)
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
        self.community.timetables['2003-fall', 'default'] = Timetable([])
        pp = 'http://localhost:7001/groups/new'
        self.assertEquals(view.timetables(),
                          [{'title': '2003-fall, another',
                            'url': '%s/timetables/2003-fall/another' % pp,
                            'empty': False},
                           {'title': '2003-fall, default',
                            'url': '%s/timetables/2003-fall/default' % pp,
                            'empty': False},
                           {'title': '2004-spring, another',
                            'url': '%s/timetables/2004-spring/another' % pp,
                            'empty': False},
                           {'title': '2004-spring, default',
                            'url': '%s/timetables/2004-spring/default' % pp,
                            'empty': False}])


def doctest_RelationshipViewMixin():
    """RelationshipViewMixin needs some attributes defined in the view class

        >>> from schooltool.browser import View
        >>> from schooltool.browser.model import RelationshipViewMixin
        >>> from schooltool.uris import URITeacher
        >>> class MyRelationshipView(View, RelationshipViewMixin):
        ...     linkrole = URITeacher
        ...     relname = 'Teaching'
        ...     errormessage = 'Could not create the relationship'
        ...     def createRelationship(self, other):
        ...         print 'Relating %s to %s' % (self.context, other)
        ...         self.context.addTeacher(other)

    The context of such a view needs to be able to participate in relationships

        >>> from schooltool.interfaces import IQueryLinks
        >>> from zope.interface import implements

        >>> class Frog(object):
        ...     implements(IQueryLinks)
        ...     def __init__(self):
        ...         self.links = []
        ...     title = property(lambda self: self.__name__.title())
        ...     def __repr__(self):
        ...         return self.title
        ...     def addTeacher(self, teacher):
        ...         self.links.append(LinkStub(self, teacher, URITeacher))
        ...     def listLinks(self, role=None):
        ...         return [link for link in self.links if link.role == role]

        >>> class LinkStub:
        ...     def __init__(self, this, other, role):
        ...         self.this = this
        ...         self.target = other
        ...         self.role = role
        ...     def unlink(self):
        ...         print "Unlinking %s and %s" % (self.this, self.target)
        ...         self.this.links.remove(self)

    We also need to be able to get object paths and traverse to objects

        >>> from zope.app.tests import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpTraversal()

        >>> from schooltool.tests.utils import setPath
        >>> from schooltool.app import Application, ApplicationObjectContainer
        >>> app = Application()
        >>> pond = app['frogs'] = ApplicationObjectContainer(Frog)

    Let's see if this stub magic works right:

        >>> from schooltool.component import getRelatedObjects
        >>> luke = pond.new('luke')
        >>> yoda = pond.new('yoda')
        >>> kermit = pond.new('kermit')
        >>> bobo = pond.new('bobo')

        >>> luke.addTeacher(yoda)
        >>> getRelatedObjects(luke, URITeacher)
        [Yoda]

    We can now create a view

        >>> from schooltool.rest.tests import RequestStub
        >>> view = MyRelationshipView(luke)
        >>> view.request = RequestStub()

    The `list` method of RelationshipViewMixin returns dicts with information
    for all related objects for the given relationship role:

        >>> from pprint import pprint
        >>> pprint(view.list())
        [{'icon_text': 'Frog',
          'icon_url': None,
          'path': u'/frogs/yoda',
          'title': 'Yoda',
          'url': 'http://localhost:7001/frogs/yoda'}]

    The `update` method handles form submissions, letting the user establish
    and remove relationships.

    To create one or more relationships, define a web form that has a submit
    button with name 'FINISH_ADD' and one or more 'toadd' elements (checkboxes
    or selections):

        >>> view.request = RequestStub(args={'FINISH_ADD': 'Add',
        ...                                  'toadd': ['/frogs/kermit',
        ...                                            '/frogs/bobo']})
        >>> view.update()
        Relating Luke to Kermit
        Relating Luke to Bobo

    As you can see, our implementation of createRelationship was called (it
    printed "Relating ...").  Also, some entries appeared in the application
    log

        >>> for user, msg, level in view.request.applog:
        ...    print msg
        Relationship 'Teaching' between /frogs/kermit and /frogs/luke created
        Relationship 'Teaching' between /frogs/bobo and /frogs/luke created

    It is up to the application to ensure that a relationship is not created
    more than once (if it is necessary).

        >>> view.request = RequestStub(args={'FINISH_ADD': 'Add',
        ...                                  'toadd': ['/frogs/kermit']})
        >>> view.update()
        Relating Luke to Kermit

    If a path in the request refers to a nonexistent object, update ignores
    the path silently.  This situation can arise when an object is deleted
    by another user, and the form is not reloaded before submission.

        >>> view.request = RequestStub(args={'FINISH_ADD': 'Add',
        ...                                  'toadd': ['/frogs/old_jones']})
        >>> view.update()

    (Nothing was printed -- see?)

    To remove one or more relationships, define a web form that has a submit
    button with name 'DELETE' and one or more 'CHECK' elements (checkboxes
    or selections):

        >>> view.request = RequestStub(args={'DELETE': 'Delete',
        ...                                  'CHECK': ['/frogs/kermit',
        ...                                            '/frogs/bobo']})
        >>> view.update()
        Unlinking Luke and Kermit
        Unlinking Luke and Bobo
        Unlinking Luke and Kermit

    Note that we had two instances of Luke -> Kermit teaching relationships.
    Both were removed.

    Log:

        >>> for user, msg, level in view.request.applog:
        ...    print msg
        Relationship 'Teaching' between /frogs/kermit and /frogs/luke removed
        Relationship 'Teaching' between /frogs/bobo and /frogs/luke removed
        Relationship 'Teaching' between /frogs/kermit and /frogs/luke removed

    That's it.

        >>> setup.placelessTearDown()

    """

class TestGroupEditView(SchoolToolSetup):

    def setUp(self):
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
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
        self.community = app['groups'].new("community", title="Community")
        self.group = app['groups'].new("new", title="Teachers")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.group2 = app['groups'].new("group2", title="Random group")
        self.per = app['persons'].new("p", title="Pete")
        self.per2 = app['persons'].new("j", title="John")
        self.per3 = app['persons'].new("lj", title="Longjohn")
        self.res = app['resources'].new("hall", title="Hall")
        self.res2 = app['resources'].new("book", title="Book")

        Membership(group=self.community, member=self.group)
        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.group, member=self.per2)
        Membership(group=self.group, member=self.res2)

    def createView(self):
        from schooltool.browser.model import GroupEditView
        return GroupEditView(self.group)

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
        from schooltool.rest import absoluteURL
        view = GroupEditView(self.group)
        view.request = RequestStub()
        list = view.list()
        expected = [self.per2, self.per, self.res2]
        self.assertEquals([item['title'] for item in list],
                          [item.title for item in expected])
        self.assertEquals([item['path'] for item in list],
                          [getPath(item) for item in expected])
        self.assertEquals([item['url'] for item in list],
                          [absoluteURL(view.request, item)
                           for item in expected])
        self.assertEquals([item['icon_url'] for item in list],
                          ['/person.png', '/person.png', '/resource.png'])
        self.assertEquals([item['icon_text'] for item in list],
                          ['Person', 'Person', 'Resource'])

    def test_addList(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.rest import absoluteURL
        view = GroupEditView(self.group)
        view.request = RequestStub(args={'SEARCH': ''})
        list = view.addList()
        expected = [self.per3, self.res]
        self.assertEquals([item['title'] for item in list],
                          [item.title for item in expected])
        self.assertEquals([item['path'] for item in list],
                          [getPath(item) for item in expected])
        self.assertEquals([item['url'] for item in list],
                          [absoluteURL(view.request, item)
                           for item in expected])
        self.assertEquals([item['icon_url'] for item in list],
                          ['/person.png', '/resource.png'])
        self.assertEquals([item['icon_text'] for item in list],
                          ['Person', 'Resource'])

        view.request = RequestStub(args={'SEARCH': 'john'})
        self.assertEquals(view.addList(),
                          [{'title': self.per3.title,
                            'icon_text': 'Person',
                            'icon_url': '/person.png',
                            'path': '/persons/lj',
                            'url': 'http://localhost:7001/persons/lj'}])

    def test_addList_restricted(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.rest import absoluteURL
        from schooltool.membership import Membership

        Person = self.app['persons'].new

        john = Person('john', title='John')
        pete = Person('pete', title='Pete')
        Membership(group=self.community, member=john)
        Membership(group=self.community, member=pete)

        self.app.restrict_membership = True

        view = GroupEditView(self.group)
        view.request = RequestStub(args={'SEARCH': ''})
        list = view.addList()
        expected = [john, pete]
        self.assertEquals([item['title'] for item in list],
                          [item.title for item in expected])
        self.assertEquals([item['path'] for item in list],
                          [getPath(item) for item in expected])
        self.assertEquals([item['url'] for item in list],
                          [absoluteURL(view.request, item)
                           for item in expected])
        self.assertEquals([item['icon_url'] for item in list],
                          ['/person.png', '/person.png'])
        self.assertEquals([item['icon_text'] for item in list],
                          ['Person', 'Person'])

        view.request = RequestStub(args={'SEARCH': 'et'})
        self.assertEquals(view.addList(),
                          [{'title': pete.title,
                            'icon_text': 'Person',
                            'icon_url': '/person.png',
                            'path': '/persons/pete',
                            'url': 'http://localhost:7001/persons/pete'}])

    def test_update_DELETE(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URIMember
        view = GroupEditView(self.group)
        request = RequestStub(args={"DELETE":"Remove them",
                                    "CHECK": ['/groups/sub', '/persons/p']})
        view.request = request
        view.update()
        self.assertEquals(sorted(getRelatedObjects(self.group, URIMember)),
                          sorted([self.per2, self.res2]))
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

    def test_update_ADD_loop(self):
        from schooltool.browser.model import GroupEditView
        from schooltool.component import getRelatedObjects
        view = GroupEditView(self.group)
        request = RequestStub(args={"FINISH_ADD":"Add selected",
                                    "toadd": ['/groups/new']})
        view.request = request
        result = view.update()
        self.assertEquals(sorted(request.applog), [])
        self.assertEquals(result, 'Cannot add Teachers to Teachers')

    def test_update_facets(self):
        from zope.component import getUtility
        from schooltool.interfaces import IFacetFactory
        from schooltool.facet import FacetManager

        facet_factory = getUtility(IFacetFactory, 'teacher_group')
        facet = facet_factory()
        FacetManager(self.group).setFacet(facet, name=facet_factory.facet_name)

        view = self.createView()
        view.request = RequestStub(args={"FINISH_ADD": "Add selected",
                                         "toadd": '/persons/lj'})
        result = view.update()
        fm = FacetManager(self.per3)
        self.assert_(fm.facetByName('teacher'))


class TestGroupSubgroupView(SchoolToolSetup):

    def setUp(self):
        # XXX Clone of TestGroupEditView.setUp().
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
        self.community = app['groups'].new("community", title="Community")
        self.group = app['groups'].new("new", title="Teachers")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.group2 = app['groups'].new("group2", title="Random group")
        self.per = app['persons'].new("p", title="Pete")
        self.per2 = app['persons'].new("j", title="John")
        self.per3 = app['persons'].new("lj", title="Longjohn")
        self.res = app['resources'].new("hall", title="Hall")
        self.res2 = app['resources'].new("book", title="Book")

        Membership(group=self.community, member=self.group)
        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.group, member=self.per2)
        Membership(group=self.group, member=self.res2)

    def test_addList(self):
        from schooltool.browser.model import GroupSubgroupView
        from schooltool.rest import absoluteURL
        view = GroupSubgroupView(self.group)
        view.request = RequestStub(args={'SEARCH': ''})
        list = view.addList()
        expected = [self.community, self.group2, self.group]
        self.assertEquals([item['title'] for item in list],
                          [item.title for item in expected])
        self.assertEquals([item['path'] for item in list],
                          [getPath(item) for item in expected])
        self.assertEquals([item['url'] for item in list],
                          [absoluteURL(view.request, item)
                           for item in expected])
        self.assertEquals([item['icon_url'] for item in list],
                          ['/group.png', '/group.png', '/group.png'])
        self.assertEquals([item['icon_text'] for item in list],
                          ['Group', 'Group', 'Group'])

    def test_list(self):
        from schooltool.browser.model import GroupSubgroupView
        from schooltool.rest import absoluteURL
        view = GroupSubgroupView(self.group)
        view.request = RequestStub()
        list = view.list()
        expected = [self.sub]
        self.assertEquals([item['title'] for item in list],
                          [item.title for item in expected])
        self.assertEquals([item['path'] for item in list],
                          [getPath(item) for item in expected])
        self.assertEquals([item['url'] for item in list],
                          [absoluteURL(view.request, item)
                           for item in expected])
        self.assertEquals([item['icon_url'] for item in list],
                          ['/group.png'])
        self.assertEquals([item['icon_text'] for item in list],
                          ['Group'])


class TestGroupTeachersView(SchoolToolSetup, NiceDiffsMixin):

    def setUp(self):
        # XXX This text fixture is way too fat...
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool.teaching import Teaching
        from schooltool import membership
        from schooltool import relationship
        from schooltool import teaching
        from zope.component import getUtility
        from schooltool.interfaces import IFacetFactory
        from schooltool.facet import FacetManager
        from schooltool.uris import URIMembership, URIGroup

        self.setUpRegistries()
        membership.setUp()
        relationship.setUp()
        teaching.setUp()
        self.app = app = Application()

        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        self.community = app['groups'].new("community", title="Community")
        self.group = app['groups'].new("new", title="Group")
        self.per = app['persons'].new("p", title="Pete")
        self.per3 = app['persons'].new("lj", title="Longjohn")
        self.teacher = self.app['persons'].new('josh', title='Josh')

        # Set up the teacher group.
        self.teachers = self.app['groups'].new('teachers', title='Teachers')
        facet_factory = getUtility(IFacetFactory, 'teacher_group')
        facet = facet_factory()
        fm = FacetManager(self.teachers)
        fm.setFacet(facet, name=facet_factory.facet_name)

        # Add people who may be teachers to the teacher group.
        val = self.teachers.getValencies()[URIMembership, URIGroup]
        val.schema(group=self.teachers, member=self.teacher)
        val.schema(group=self.teachers, member=self.per3)

        Membership(group=self.community, member=self.group)
        Membership(group=self.group, member=self.per)
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
        self.assertEquals(view.list(),
                          [{'title': self.per3.title,
                            'icon_text': 'Person',
                            'icon_url': '/person.png',
                            'path': '/persons/lj',
                            'url': 'http://localhost:7001/persons/lj'}])

    def test_addList(self):
        from schooltool.browser.model import GroupTeachersView
        view = GroupTeachersView(self.group)
        view.request = RequestStub()
        self.assertEquals(view.addList(),
                          [{'title': self.teacher.title,
                            'icon_text': 'Person',
                            'icon_url': '/person.png',
                            'path': '/persons/josh',
                            'url': 'http://localhost:7001/persons/josh'}])

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

    def test_update_ADD_nothing_is_selected(self):
        from schooltool.browser.model import GroupTeachersView
        view = GroupTeachersView(self.group)
        view.request = RequestStub(args={"FINISH_ADD":"Add selected",
                                         "toadd": ''})
        view.update()
        self.assertEquals(view.request.applog, [])

    def test_update_ADD_loop(self):
        from schooltool.browser.model import GroupTeachersView
        view = GroupTeachersView(self.group)
        view.request = RequestStub(args={"FINISH_ADD":"Add selected",
                                         "toadd": ['/persons/josh']})
        result = view.update()
        del view.request.applog[:]
        result = view.update() # second update will fail
        self.assertEquals(sorted(view.request.applog), [])
        self.assertEquals(result, 'Cannot add teacher Josh to Group')

    def test_update_ADD_error(self):
        from schooltool.browser.model import GroupTeachersView
        from schooltool.component import getRelatedObjects
        from schooltool.uris import URITeacher
        view = GroupTeachersView(self.group)
        view.request = RequestStub(args={"FINISH_ADD":"Add selected",
                                         "toadd": '/persons/p'})
        result = view.update()
        self.assertEquals(result, "Cannot add teacher Pete to Group")
        teachers = getRelatedObjects(self.group, URITeacher)
        assert self.per not in teachers, teachers
        self.assertEquals(view.request.applog, [])


class TestResourceView(AppSetupMixin, unittest.TestCase, TraversalTestMixin):

    def test(self):
        from schooltool.browser.model import ResourceView
        resource = self.resource
        view = ResourceView(resource)
        view.authorization = lambda x, y: True
        request = RequestStub()
        content = view.render(request)

        self.assert_("Kitchen sink" in content)
        self.assert_("resource" in content)

    def test_editURL(self):
        from schooltool.browser.model import ResourceView
        resource = self.resource
        view = ResourceView(resource)
        view.request = RequestStub()
        self.assertEquals(view.editURL(),
                          'http://localhost:7001/resources/resource/edit.html')

    def test_traverse(self):
        from schooltool.model import Resource
        from schooltool.browser.model import ResourceView, ResourceEditView
        from schooltool.browser.cal import BookingView, BookingViewPopUp
        from schooltool.browser.timetable import TimetableTraverseView
        from schooltool.browser.cal import CalendarView
        from schooltool.browser.acl import ACLView
        resource = self.resource
        view = ResourceView(resource)
        self.assertTraverses(view, 'edit.html', ResourceEditView, resource)
        self.assertTraverses(view, 'book', BookingView, resource)
        self.assertTraverses(view, 'acl.html', ACLView, self.resource.acl)
        self.assertTraverses(view, 'calendar',
                             CalendarView, self.resource.calendar)
        self.assertTraverses(view, 'timetables', TimetableTraverseView,
                             self.resource)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestResourceEditView(SchoolToolSetup):

    def createView(self):
        from schooltool.browser.model import ResourceEditView
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Resource

        app = Application()
        resources = app['resources'] = ApplicationObjectContainer(Resource)
        resources.new(title=u"Already Used")
        self.resource = resources.new('foo', title=u"Foo Title")
        view = ResourceEditView(self.resource)
        view.authorization = lambda x, y: True
        return view

    def test_get(self):
        view = self.createView()
        request = RequestStub()
        content = view.render(request)
        assert "Foo Title" in content
        assert "CONFIRM" not in content

    def test_post(self):
        view = self.createView()
        request = RequestStub(args={'title': 'New \xc4\x85'})
        view.request = request
        view.do_POST(request)
        self.assertEquals(self.resource.title, u'New \u0105')
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/resources/foo')
        self.assertEquals(request.applog,
                          [(None, 'Resource /resources/foo modified', INFO)])

    def test_post_duplicate_title(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Already Used'})
        view.request = request
        result = view.do_POST(request)
        assert "This title is already used for another resource." in result
        assert "CONFIRM" in result
        self.assertEquals(request.applog, [])
        self.assertEquals(request.applog, [])

    def test_post_duplicate_title_confirmed(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Already Used',
                                    'CONFIRM': 'Save anyway'})
        view.request = request
        result = view.do_POST(request)
        self.assertEquals(self.resource.title, u'Already Used')
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/resources/foo')
        self.assertEquals(request.applog,
                          [(None, 'Resource /resources/foo modified', INFO)])

    def test_post_duplicate_title_cancel(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Already Used',
                                    'CANCEL': 'Cancel'})
        view.request = request
        result = view.do_POST(request)
        self.assertEquals(request.applog, [])
        assert "Foo Title" in result
        assert "CONFIRM" not in result


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
        request = RequestStub(authenticated_user=UserStub())
        result = view.render(request)
        self.assertEquals(request.code, 404)


class TestNoteView(AppSetupMixin, unittest.TestCase, TraversalTestMixin):

    def test(self):
        from schooltool.browser.model import NoteView
        note = self.note1
        view = NoteView(note)
        view.authorization = lambda x, y: True
        request = RequestStub()
        content = view.render(request)

        self.assert_("Note 1 Title" in content)
        self.assert_("Note 1 Body" in content)


class TestResidenceMoveView(SchoolToolSetup):

    def setUp(self):
        from schooltool.model import Residence, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.occupies import Occupies
        from schooltool import occupies
        from schooltool import relationship
        self.setUpRegistries()
        occupies.setUp()
        relationship.setUp()
        app = Application()
        self.app = app
        app['persons'] = ApplicationObjectContainer(Person)
        app['residences'] = ApplicationObjectContainer(Residence)
        self.per = app['persons'].new("p", title="Pete")
        self.per2 = app['persons'].new("j", title="John")

        self.res = app['residences'].new(None, title="Home")
        self.res2 = app['residences'].new(None, title="Home2")

        Occupies(residence=self.res, resides=self.per)
        Occupies(residence=self.res2, resides=self.per2)

    def test(self):
        from schooltool.browser.model import ResidenceMoveView
        view = ResidenceMoveView(self.res)
        view.authorization = lambda x, y: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('Home' in result, result)


class TestHelpers(unittest.TestCase):

    def test_app_object_icon(self):
        from schooltool.browser.model import app_object_icon
        self.assertEquals(app_object_icon(PersonStub()),
                          ('/person.png', 'Person'))
        self.assertEquals(app_object_icon(GroupStub()),
                          ('/group.png', 'Group'))
        self.assertEquals(app_object_icon(ResourceStub()),
                          ('/resource.png', 'Resource'))
        self.assertEquals(app_object_icon(UnknownObjectStub()),
                          (None, 'UnknownObjectStub'))

    def test_app_object_list(self):
        from schooltool.browser.model import app_object_list
        p1 = PersonStub('p1', 'Person A')
        p2 = PersonStub('p2', 'Person B')
        r1 = ResourceStub('r1', 'A Resource')
        self.assertEquals(app_object_list([p2, r1, p1]),
                          [{'title': 'Person A',
                            'obj': p1,
                            'icon_url': '/person.png',
                            'icon_text': 'Person'},
                           {'title': 'Person B',
                            'obj': p2,
                            'icon_url': '/person.png',
                            'icon_text': 'Person'},
                           {'title': 'A Resource',
                            'obj': r1,
                            'icon_url': '/resource.png',
                            'icon_text': 'Resource'}])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(unittest.makeSuite(TestPersonInfoMixin))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestPersonEditView))
    suite.addTest(unittest.makeSuite(TestPersonPasswordView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestGroupEditView))
    suite.addTest(unittest.makeSuite(TestGroupSubgroupView))
    suite.addTest(unittest.makeSuite(TestGroupTeachersView))
    suite.addTest(unittest.makeSuite(TestResourceView))
    suite.addTest(unittest.makeSuite(TestResourceEditView))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    suite.addTest(unittest.makeSuite(TestNoteView))
    suite.addTest(unittest.makeSuite(TestResidenceMoveView))
    suite.addTest(unittest.makeSuite(TestHelpers))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
