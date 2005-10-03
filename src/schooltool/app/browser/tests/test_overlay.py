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
Tests for schooltool views.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass

from schooltool.app.browser.testing import setUp as browserSetUp, tearDown
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.testing import setup

def setUp(test=None):
    browserSetUp(test)
    #from zope.app.testing.setup import setUpAnnotations
    #setUpAnnotations()
    setup.setupCalendaring()


def doctest_CalendarOverlayView():
    r"""Tests for CalendarOverlayView

    Some initial setup:

        >>> from schooltool.app.overlay import CalendarOverlayInfo
        >>> from schooltool.app.interfaces import IShowTimetables
        >>> from schooltool.app.app import ShowTimetables
        >>> from zope.app.testing import ztapi
        >>> ztapi.provideAdapter(CalendarOverlayInfo, IShowTimetables,
        ...                      ShowTimetables)

        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> from zope.app.annotation.attribute import AttributeAnnotations
        >>> ztapi.provideAdapter(CalendarOverlayInfo, IAnnotations,
        ...                      AttributeAnnotations)

        >>> from schooltool.app.browser.cal import CalendarSTOverlayView
        >>> View = SimpleViewClass('../templates/calendar_overlay.pt',
        ...                        bases=(CalendarSTOverlayView,))

    CalendarOverlayView is a view on anything.

        >>> context = object()
        >>> request = TestRequest()
        >>> view = View(context, request)

    It renders to an empty string unless its context is the calendar of the
    authenticated user

        >>> view()
        u'\n'

    If you are an authenticated user looking at your own calendar, this view
    renders a calendar selection portlet.

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
        >>> from schooltool.app.security import Principal
        >>> app = setup.setupSchoolToolSite()
        >>> person = app['persons']['whatever'] = Person('fred')
        >>> group1 = app['groups']['g1'] = Group(title="Group 1")
        >>> group2 = app['groups']['g2'] = Group(title="Group 2")
        >>> person.overlaid_calendars.add(ISchoolToolCalendar(group1))
        <...CalendarOverlayInfo object at ...>
        >>> person.overlaid_calendars.add(ISchoolToolCalendar(group2),
        ...                               show=False)
        <...CalendarOverlayInfo object at ...>

        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> view = View(ISchoolToolCalendar(person), request)

        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        <td><input type="checkbox" name="overlay:list"
               checked="checked" value="/groups/g1" /></td>
        ...
        <td><input type="checkbox" name="overlay:list"
               value="/groups/g2" /></td>
        ...
        </div>

    If the request has 'OVERLAY_APPLY', CalendarOverlayView applies your
    changes

        >>> request.form['overlay'] = [u'/groups/g2']
        >>> request.form['OVERLAY_APPLY'] = u"Apply"
        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        <td><input type="checkbox" name="overlay:list"
               value="/groups/g1" /></td>
        ...
        <td><input type="checkbox" name="overlay:list"
               checked="checked" value="/groups/g2" /></td>
        ...
        </div>

    It also redirects you to request.URL:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    There are two reasons for the redirect: first, part of the page template
    just rendered might have become invalid when calendar overlay selection
    changed, second, this lets the user refresh the page without having to
    experience confirmations dialogs that say "Do you want to POST this form
    again?".

    If the request has 'OVERLAY_MORE', CalendarOverlayView redirects to
    calendar_selection.html

        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> request.form['OVERLAY_MORE'] = u"More..."
        >>> view = View(ISchoolToolCalendar(person), request)
        >>> content = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/fred/calendar_selection.html?nexturl=http%3A//127.0.0.1'

    """


def doctest_CalendarOverlayView_items():
    """Tests for CalendarOverlayView.items().

        >>> from schooltool.app.browser.overlay import CalendarOverlayView

    We will need some persons and groups for the demonstration.

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
        >>> app = setup.setupSchoolToolSite()
        >>> person = app['persons']['p1'] = Person('p1', title="Person")
        >>> group1 = app['groups']['g1'] = Group(title="Group 1")
        >>> group2 = app['groups']['g2'] = Group(title="Group 2")

    When the person has no calendars in his overlay list, items returns
    an empty list

        >>> from zope.publisher.browser import TestRequest
        >>> from schooltool.app.security import Principal
        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('', '', person))
        >>> context = ISchoolToolCalendar(person)
        >>> view = CalendarOverlayView(context, request)
        >>> view.items()
        []

    When the person has calendars in his overlay list

        >>> person.overlaid_calendars.add(ISchoolToolCalendar(group2))
        <...CalendarOverlayInfo object at ...>
        >>> person.overlaid_calendars.add(ISchoolToolCalendar(group1),
        ...                               show=False)
        <...CalendarOverlayInfo object at ...>

        >>> from zope.testing.doctestunit import pprint
        >>> pprint(view.items())
        [{'calendar': <schooltool.app.cal.Calendar object at ...>,
          'checked': '',
          'color1': '#eed680',
          'color2': '#d1940c',
          'id': u'/groups/g1',
          'title': 'Group 1'},
         {'calendar': <schooltool.app.cal.Calendar object at ...>,
          'checked': 'checked',
          'color1': '#e0b6af',
          'color2': '#c1665a',
          'id': u'/groups/g2',
          'title': 'Group 2'}]

    """

def doctest_CalendarSelectionView():
    """Tests for CalendarSelectionView

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> from zope.app.testing import ztapi
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)
        >>> from schooltool.app.browser.overlay import CalendarSelectionView
        >>> View = SimpleViewClass('../templates/calendar_selection.pt',
        ...                        bases=(CalendarSelectionView,))

    CalendarSelectionView is a view on IPerson

        >>> from schooltool.resource.resource import Resource
        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
        >>> from schooltool.app.security import Principal
        >>> app = setup.setupSchoolToolSite()
        >>> persons = app['persons']
        >>> groups = app['groups']
        >>> resources = app['resources']
        >>> fred = persons['fred'] = Person('fred', 'Fred F.')
        >>> eric = persons['eric'] = Person('eric', 'Eric Bjornsen')
        >>> igor = persons['igor'] = Person('igor', 'Igor')
        >>> admins = groups['admins'] = Group('Administrators')
        >>> car = resources['car'] = Resource('Company car')
        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('fred', '', fred))
        >>> view = View(fred, request)

    It lists Eric's, Igor's calendars and the site-wide calendar as available
    for selection

        >>> print view()
        <BLANKLINE>
        ...
            Select calendars to display
        ...
              <legend>Public Calendar</legend>
              <label>
                <input type="checkbox" name="application"
                       value="application" />
        ...
            <fieldset class="inline">
              <legend>People</legend>
              <select size="8" multiple="multiple" id="people"
                      name="persons:list">
                <option value="eric">Eric Bjornsen</option>
                <option value="igor">Igor</option>
              </select>
            </fieldset>
        <BLANKLINE>
            <fieldset class="inline">
              <legend>Groups</legend>
              <select size="8" multiple="multiple" id="groups"
                      name="groups:list">
                <option value="admins">Administrators</option>
              </select>
            </fieldset>
        <BLANKLINE>
            <fieldset class="inline">
              <legend>Resources</legend>
              <select size="8" multiple="multiple" id="resources"
                      name="resources:list">
                <option value="car">Company car</option>
              </select>
            </fieldset>
        ...

    If a person's calendar is added to your overlaid calendars list, you
    can see that in the form.

        >>> fred.overlaid_calendars.add(ISchoolToolCalendar(eric), show=False)
        <...CalendarOverlayInfo object at ...>

        >>> print view()
        <BLANKLINE>
        ...
              <select size="8" multiple="multiple" id="people"
                      name="persons:list">
                <option selected="selected" value="eric">Eric Bjornsen</option>
                <option value="igor">Igor</option>
              </select>
        ...

    Note that the user does not see his own calendar in that list:

        >>> 'value="fred"' in view()
        False

    We can submit that form

        >>> request.form["persons"] = [u"eric", u"igor"]
        >>> request.form["groups"] = [u"admins"]
        >>> request.form["resources"] = [u"car"]
        >>> request.form["UPDATE_SUBMIT"] = u"Apply"
        >>> print view()
        <BLANKLINE>
        ...
              <select size="8" multiple="multiple" id="people" 
                      name="persons:list">
                <option selected="selected" value="eric">Eric Bjornsen</option>
                <option selected="selected" value="igor">Igor</option>
              </select>
        ...

    We can see that the calendars we selected were added to the list

        >>> ISchoolToolCalendar(igor) in fred.overlaid_calendars
        True
        >>> ISchoolToolCalendar(admins) in fred.overlaid_calendars
        True
        >>> ISchoolToolCalendar(car) in fred.overlaid_calendars
        True

    We can also remove calendars

        >>> request.form["persons"] = [u"igor"]
        >>> request.form["UPDATE_SUBMIT"] = u"Apply"
        >>> print view()
        <BLANKLINE>
        ...
              <select size="8" multiple="multiple" id="people"
                      name="persons:list">
                <option value="eric">Eric Bjornsen</option>
                <option selected="selected" value="igor">Igor</option>
              </select>
        ...

        >>> ISchoolToolCalendar(eric) in fred.overlaid_calendars
        False

    When you submit the form, you are redirected back to the original view

        >>> request.form["nexturl"] = 'http://localhost/persons/fred/calendar'
        >>> request.form["UPDATE_SUBMIT"] = u"Apply"
        >>> output = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://localhost/persons/fred/calendar'

    The same thing happens if you press Cancel:

        >>> request = TestRequest()
        >>> request.form["nexturl"] = 'http://localhost/persons/fred/calendar'
        >>> request.form["CANCEL"] = u"Cancel"
        >>> view = View(fred, request)
        >>> output = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://localhost/persons/fred/calendar'

    Regression test for issue328 (traceback when adding overlays).  This was
    caused by getApplicationCalendar returning None if it could not access the
    application calendar.  To solve this we now return an empty dict and check
    the result in update()

        >>> view.getApplicationCalendar()
        {}
        >>> view.update()

    """


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
