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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Tests for schooltool views.
"""

import unittest
import doctest

from zope.interface import classImplements
from zope.component import provideAdapter
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.browser.testing import setUp as browserSetUp, tearDown
from schooltool.testing import setup


def setUp(test=None):
    browserSetUp(test)
    setup.setUpCalendaring()

    from schooltool.app.overlay import CalendarOverlayInfo
    from schooltool.app.app import ShowTimetables
    provideAdapter(ShowTimetables)
    classImplements(CalendarOverlayInfo, IAttributeAnnotatable)


# def doctest_CalendarOverlayView():
#     r"""Tests for CalendarOverlayView

#     Some initial setup:

#         >>> from schooltool.app.browser.overlay import CalendarOverlayView
#         >>> View = SimpleViewClass('../templates/calendar_overlay.pt',
#         ...                        bases=(CalendarOverlayView,))

#     CalendarOverlayView is a view on anything.

#         >>> context = object()
#         >>> request = TestRequest()
#         >>> view = View(context, request, None, None)

#     It renders to an empty string unless its context is the calendar of the
#     authenticated user

#         >>> view()
#         u'\n'

#     If you are an authenticated user looking at your own calendar, this view
#     renders a calendar selection portlet.

#         >>> from schooltool.group.group import Group
#         >>> from schooltool.person.person import Person
#         >>> from schooltool.app.security import Principal
#         >>> app = setup.setUpSchoolToolSite()
#         >>> person = app['persons']['whatever'] = Person('fred')
#         >>> group1 = app['groups']['g1'] = Group(title="Group 1")
#         >>> group2 = app['groups']['g2'] = Group(title="Group 2")
#         >>> person.overlaid_calendars.add(ISchoolToolCalendar(group1))
#         <...CalendarOverlayInfo object at ...>
#         >>> person.overlaid_calendars.add(ISchoolToolCalendar(group2),
#         ...                               show=False)
#         <...CalendarOverlayInfo object at ...>

#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('id', 'title', person))
#         >>> view = View(ISchoolToolCalendar(person), request, None, None)

#         >>> print view()
#         <div id="portlet-calendar-overlay" class="portlet">
#         ...
#         <td><input type="checkbox" name="overlay:list"
#                checked="checked" value="/groups/g1" /></td>
#         ...
#         <td><input type="checkbox" name="overlay:list"
#                value="/groups/g2" /></td>
#         ...
#         </div>

#     If the request has 'OVERLAY_APPLY', CalendarOverlayView applies your
#     changes

#         >>> request.form['overlay'] = [u'/groups/g2']
#         >>> request.form['OVERLAY_APPLY'] = u"Apply"
#         >>> print view()
#         <div id="portlet-calendar-overlay" class="portlet">
#         ...
#         <td><input type="checkbox" name="overlay:list"
#                value="/groups/g1" /></td>
#         ...
#         <td><input type="checkbox" name="overlay:list"
#                checked="checked" value="/groups/g2" /></td>
#         ...
#         </div>

#     It also redirects you to request.URL:

#         >>> request.response.getStatus()
#         302
#         >>> request.response.getHeader('Location')
#         'http://127.0.0.1'

#     There are two reasons for the redirect: first, part of the page template
#     just rendered might have become invalid when calendar overlay selection
#     changed, second, this lets the user refresh the page without having to
#     experience confirmations dialogs that say "Do you want to POST this form
#     again?".

#     If the request has 'OVERLAY_MORE', CalendarOverlayView redirects to
#     calendar_selection.html

#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('id', 'title', person))
#         >>> request.form['OVERLAY_MORE'] = u"More..."
#         >>> view = View(ISchoolToolCalendar(person), request, None, None)
#         >>> content = view()
#         >>> request.response.getStatus()
#         302
#         >>> request.response.getHeader('Location')
#         'http://127.0.0.1/persons/fred/calendar_selection.html?nexturl=http%3A//127.0.0.1'

#     """

# def doctest_CalendarOverlayView_items():
#     """Tests for CalendarOverlayView.items().

#         >>> from schooltool.app.browser.overlay import CalendarOverlayView

#     We will need some persons and groups for the demonstration.

#         >>> from schooltool.group.group import Group
#         >>> from schooltool.person.person import Person
#         >>> app = setup.setUpSchoolToolSite()
#         >>> person = app['persons']['p1'] = Person('p1', title="Person")
#         >>> group1 = app['groups']['g1'] = Group(title="Group 1")
#         >>> group2 = app['groups']['g2'] = Group(title="Group 2")

#     When the person has no calendars in his overlay list, items returns
#     an empty list

#         >>> from zope.publisher.browser import TestRequest
#         >>> from schooltool.app.security import Principal
#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('', '', person))
#         >>> context = ISchoolToolCalendar(person)
#         >>> view = CalendarOverlayView(context, request, None, None)
#         >>> view.items()
#         []

#     When the person has calendars in his overlay list

#         >>> person.overlaid_calendars.add(ISchoolToolCalendar(group2))
#         <...CalendarOverlayInfo object at ...>
#         >>> person.overlaid_calendars.add(ISchoolToolCalendar(group1),
#         ...                               show=False)
#         <...CalendarOverlayInfo object at ...>

#         >>> from zope.testing.doctestunit import pprint
#         >>> pprint(view.items())
#         [{'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': '',
#           'color1': '#eed680',
#           'color2': '#d1940c',
#           'id': u'/groups/g1',
#           'title': 'Group 1'},
#          {'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': 'checked',
#           'color1': '#e0b6af',
#           'color2': '#c1665a',
#           'id': u'/groups/g2',
#           'title': 'Group 2'}]

#     """


# def doctest_CalendarOverlayView_items_with_identical_titles():
#     """Tests for CalendarOverlayView.items().

#         >>> from schooltool.app.browser.overlay import CalendarOverlayView

#     We will need some persons and groups for the demonstration.

#         >>> from schooltool.group.group import Group
#         >>> from schooltool.person.person import Person
#         >>> app = setup.setUpSchoolToolSite()
#         >>> person = app['persons']['p1'] = Person('p1', title="Person")
#         >>> group1 = app['groups']['g1'] = Group(title="Group")
#         >>> group5 = app['groups']['g5'] = Group(title="Group")
#         >>> group3 = app['groups']['g3'] = Group(title="Group")
#         >>> group4 = app['groups']['g4'] = Group(title="Group")
#         >>> group2 = app['groups']['g2'] = Group(title="Group")

#     When the person has calendars in his overlay list

#         >>> from zope.publisher.browser import TestRequest
#         >>> from schooltool.app.security import Principal
#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('', '', person))
#         >>> context = ISchoolToolCalendar(person)

#         >>> for group in app['groups'].values():
#         ...     link = person.overlaid_calendars.add(ISchoolToolCalendar(group))

#         >>> view = CalendarOverlayView(context, request, None, None)
#         >>> from zope.testing.doctestunit import pprint
#         >>> pprint(view.items())
#         [{'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': 'checked',
#           'color1': '#e0b6af',
#           'color2': '#c1665a',
#           'id': u'/groups/g1',
#           'title': 'Group'},
#          {'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': 'checked',
#           'color1': '#eed680',
#           'color2': '#d1940c',
#           'id': u'/groups/g2',
#           'title': 'Group'},
#          {'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': 'checked',
#           'color1': '#c5d2c8',
#           'color2': '#83a67f',
#           'id': u'/groups/g3',
#           'title': 'Group'},
#          {'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': 'checked',
#           'color1': '#efe0cd',
#           'color2': '#e0c39e',
#           'id': u'/groups/g4',
#           'title': 'Group'},
#          {'calendar': <schooltool.app.cal.Calendar object at ...>,
#           'checked': 'checked',
#           'color1': '#ada7c8',
#           'color2': '#887fa3',
#           'id': u'/groups/g5',
#           'title': 'Group'}]

#     """


# def doctest_CalendarSelectionView():
#     """Tests for CalendarSelectionView

#         >>> from schooltool.app.interfaces import ISchoolToolApplication
#         >>> from schooltool.app.interfaces import IApplicationPreferences
#         >>> from schooltool.app.app import getApplicationPreferences
#         >>> provideAdapter(getApplicationPreferences,
#         ...                (ISchoolToolApplication,), IApplicationPreferences)
#         >>> from schooltool.app.browser.overlay import CalendarSelectionView
#         >>> View = SimpleViewClass('../templates/calendar_selection.pt',
#         ...                        bases=(CalendarSelectionView,))

#     CalendarSelectionView is a view on IPerson

#         >>> from schooltool.resource.resource import Resource
#         >>> from schooltool.group.group import Group
#         >>> from schooltool.person.person import Person
#         >>> from schooltool.app.security import Principal
#         >>> app = setup.setUpSchoolToolSite()
#         >>> persons = app['persons']
#         >>> groups = app['groups']
#         >>> resources = app['resources']
#         >>> fred = persons['fred'] = Person('fred', 'Fred F.')
#         >>> eric = persons['eric'] = Person('eric', 'Eric Bjornsen')
#         >>> igor = persons['igor'] = Person('igor', 'Igor')
#         >>> admins = groups['admins'] = Group('Administrators')
#         >>> car = resources['car'] = Resource('Company car')
#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('fred', '', fred))
#         >>> view = View(fred, request)

#     It lists Eric's, Igor's calendars and the site-wide calendar as available
#     for selection

#         >>> print view()
#         <BLANKLINE>
#         ...
#             Select calendars to display
#         ...
#               <legend>Public Calendar</legend>
#               <label>
#                 <input type="checkbox" name="application"
#                        value="application" />
#         ...
#             <fieldset class="inline">
#               <legend>People</legend>
#               <select size="8" multiple="multiple" id="people"
#                       name="persons:list">
#                 <option value="eric">Eric Bjornsen</option>
#                 <option value="igor">Igor</option>
#               </select>
#             </fieldset>
#         <BLANKLINE>
#             <fieldset class="inline">
#               <legend>Groups</legend>
#               <select size="8" multiple="multiple" id="groups"
#                       name="groups:list">
#                 <option value="admins">Administrators</option>
#               </select>
#             </fieldset>
#         <BLANKLINE>
#             <fieldset class="inline">
#               <legend>Resources</legend>
#               <select size="8" multiple="multiple" id="resources"
#                       name="resources:list">
#                 <option value="car">Company car</option>
#               </select>
#             </fieldset>
#         ...

#     If a person's calendar is added to your overlaid calendars list, you
#     can see that in the form.

#         >>> fred.overlaid_calendars.add(ISchoolToolCalendar(eric), show=False)
#         <...CalendarOverlayInfo object at ...>

#         >>> print view()
#         <BLANKLINE>
#         ...
#               <select size="8" multiple="multiple" id="people"
#                       name="persons:list">
#                 <option selected="selected" value="eric">Eric Bjornsen</option>
#                 <option value="igor">Igor</option>
#               </select>
#         ...

#     Note that the user does not see his own calendar in that list:

#         >>> 'value="fred"' in view()
#         False

#     We can submit that form

#         >>> request.form["persons"] = [u"eric", u"igor"]
#         >>> request.form["groups"] = [u"admins"]
#         >>> request.form["resources"] = [u"car"]
#         >>> request.form["UPDATE_SUBMIT"] = u"Apply"
#         >>> print view()
#         <BLANKLINE>
#         ...
#               <select size="8" multiple="multiple" id="people"
#                       name="persons:list">
#                 <option selected="selected" value="eric">Eric Bjornsen</option>
#                 <option selected="selected" value="igor">Igor</option>
#               </select>
#         ...

#     We can see that the calendars we selected were added to the list

#         >>> ISchoolToolCalendar(igor) in fred.overlaid_calendars
#         True
#         >>> ISchoolToolCalendar(admins) in fred.overlaid_calendars
#         True
#         >>> ISchoolToolCalendar(car) in fred.overlaid_calendars
#         True

#     We can also remove calendars

#         >>> request.form["persons"] = [u"igor"]
#         >>> request.form["UPDATE_SUBMIT"] = u"Apply"
#         >>> print view()
#         <BLANKLINE>
#         ...
#               <select size="8" multiple="multiple" id="people"
#                       name="persons:list">
#                 <option value="eric">Eric Bjornsen</option>
#                 <option selected="selected" value="igor">Igor</option>
#               </select>
#         ...

#         >>> ISchoolToolCalendar(eric) in fred.overlaid_calendars
#         False

#     When you submit the form, you are redirected back to the original view

#         >>> request.form["nexturl"] = 'http://localhost/persons/fred/calendar'
#         >>> request.form["UPDATE_SUBMIT"] = u"Apply"
#         >>> output = view()
#         >>> request.response.getStatus()
#         302
#         >>> request.response.getHeader('Location')
#         'http://localhost/persons/fred/calendar'

#     The same thing happens if you press Cancel:

#         >>> request = TestRequest()
#         >>> request.form["nexturl"] = 'http://localhost/persons/fred/calendar'
#         >>> request.form["CANCEL"] = u"Cancel"
#         >>> view = View(fred, request)
#         >>> output = view()
#         >>> request.response.getStatus()
#         302
#         >>> request.response.getHeader('Location')
#         'http://localhost/persons/fred/calendar'

#     Regression test for issue328 (traceback when adding overlays).  This was
#     caused by getApplicationCalendar returning None if it could not access the
#     application calendar.  To solve this we now return an empty dict and check
#     the result in update()

#         >>> view.getApplicationCalendar()
#         {}
#         >>> view.update()

#     """


# def doctest_CalendarSelectionView_updateSelection():
#     """Test for CalendarSelectionView._updateSelection

#         >>> from schooltool.app.browser.overlay import CalendarSelectionView
#         >>> from schooltool.app.interfaces import IShowTimetables
#         >>> from schooltool.person.person import Person
#         >>> from schooltool.group.group import Group
#         >>> from schooltool.resource.resource import Resource
#         >>> from schooltool.app.cal import Calendar
#         >>> request = TestRequest()
#         >>> context = None
#         >>> view = CalendarSelectionView(context, request)
#         >>> user = Person()
#         >>> book = Resource('A book')
#         >>> beamer = Resource('A beamer')
#         >>> friends = Group('Friends')
#         >>> joe = Person(title='Joe')
#         >>> appcal = Calendar(Resource('Application'))

#         >>> def stub_getCalendars(container):
#         ...     if container == 'persons':
#         ...         return [{'id': 'joe',
#         ...                  'title': 'Joe',
#         ...                  'selected': ISchoolToolCalendar(joe)
#         ...                                 in user.overlaid_calendars,
#         ...                  'calendar': ISchoolToolCalendar(joe)}]
#         ...     elif container == 'groups':
#         ...         return [{'id': 'friends',
#         ...                  'title': 'Friends',
#         ...                  'selected': ISchoolToolCalendar(friends)
#         ...                                 in user.overlaid_calendars,
#         ...                  'calendar': ISchoolToolCalendar(friends)}]
#         ...     elif container == 'resources':
#         ...         return [{'id': 'book',
#         ...                  'title': 'The book',
#         ...                  'selected': ISchoolToolCalendar(book)
#         ...                                 in user.overlaid_calendars,
#         ...                  'calendar': ISchoolToolCalendar(book)},
#         ...                 {'id': 'beamer',
#         ...                  'title': 'A beamer',
#         ...                  'selected': ISchoolToolCalendar(beamer)
#         ...                                 in user.overlaid_calendars,
#         ...                  'calendar': ISchoolToolCalendar(beamer)}]
#         ...     else:
#         ...         return []
#         >>> view.getCalendars = stub_getCalendars
#         >>> def stub_getApplicationCalendar():
#         ...     return {'title': 'Applcation',
#         ...             'selected': appcal in user.overlaid_calendars,
#         ...             'calendar': appcal}
#         >>> view.getApplicationCalendar = stub_getApplicationCalendar

#         >>> def print_overlays(user=user):
#         ...     l = [(cal.calendar.title, cal)
#         ...          for cal in user.overlaid_calendars]
#         ...     l.sort()
#         ...     for title, info in l:
#         ...         showtt = IShowTimetables(info).showTimetables
#         ...         print '[%s][%s] %s' % (info.show and '+' or '-',
#         ...                                showtt and '+' or '-',
#         ...                                title)

#     So, we have two calendars available for selection, but we choose none of
#     them.  Nothing happens.

#         >>> view._updateSelection(user)
#         >>> print_overlays()

#     We can choose one, and it appears in the overlay list.

#         >>> request.form['resources'] = ['beamer']
#         >>> view._updateSelection(user)
#         >>> print_overlays()
#         [+][-] A beamer

#     Note that the calendar overlay is visible by default (indicated by '+' in
#     the first checkbox), but the timetable is hidden (indicated by '-' in the
#     second checkbox).

#     We can choose both

#         >>> request.form['resources'] = ['beamer', 'book']
#         >>> view._updateSelection(user)
#         >>> print_overlays()
#         [+][-] A beamer
#         [+][-] A book

#     We can choose one again, and the other disappears

#         >>> request.form['resources'] = ['book']
#         >>> view._updateSelection(user)
#         >>> print_overlays()
#         [+][-] A book

#     It works with persons and groups as well

#         >>> request.form['persons'] = ['joe']
#         >>> request.form['groups'] = ['friends']
#         >>> request.form['resources'] = []
#         >>> view._updateSelection(user)
#         >>> print_overlays()
#         [+][-] Friends
#         [+][+] Joe

#     Note that for persons (and only for persons), both the calendar, and the
#     timetable are visible.

#         >>> request.form['persons'] = []
#         >>> request.form['groups'] = []
#         >>> request.form['resources'] = []
#         >>> view._updateSelection(user)
#         >>> print_overlays()

#     You can choose the application calendar as well

#         >>> request.form['application'] = ''
#         >>> view._updateSelection(user)
#         >>> print_overlays()
#         [+][+] Application

#     Avoid duplicate additions:

#         >>> request.form['application'] = ''
#         >>> view._updateSelection(user)
#         >>> print_overlays()
#         [+][+] Application

#     And remove it

#         >>> del request.form['application']
#         >>> view._updateSelection(user)
#         >>> print_overlays()

#     """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                            doctest.REPORT_NDIFF|
                                            doctest.NORMALIZE_WHITESPACE))
    suite.addTest(doctest.DocTestSuite('schooltool.app.browser.overlay'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
