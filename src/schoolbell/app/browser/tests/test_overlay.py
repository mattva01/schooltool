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
Tests for schoolbell views.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.app.component.hooks import setSite

from schoolbell.app.browser.tests.setup import setUp, tearDown
from schoolbell.app.browser.tests.setup import setUpSchoolBellSite


def doctest_CalendarOverlayView():
    r"""Tests for CalendarOverlayView

        >>> from schoolbell.app.browser.overlay import CalendarOverlayView
        >>> View = SimpleViewClass('../templates/calendar_overlay.pt',
        ...                        bases=(CalendarOverlayView,))

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

        >>> from schoolbell.app.app import Person
        >>> from schoolbell.app.security import Principal
        >>> app = setUpSchoolBellSite()
        >>> person = app['persons']['whatever'] = Person('fred')
        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> view = View(person.calendar, request)

        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        </div>

    If the request has 'OVERLAY_MORE', CalendarOverlayView redirects to
    calendar_selection.html

        >>> request.form['OVERLAY_MORE'] = u"More..."
        >>> content = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/fred/calendar_selection.html?nexturl=http%3A//127.0.0.1'

    """


def doctest_CalendarOverlayView_items():
    """Tests for CalendarOverlayView.items().

        >>> from schoolbell.app.browser.overlay import CalendarOverlayView

    We will need some persons and groups for the demonstration.

        >>> from schoolbell.app.app import Person, Group
        >>> app = setUpSchoolBellSite()
        >>> person = app['persons']['p1'] = Person('p1', title="Person")
        >>> group1 = app['groups']['g1'] = Group(title="Group 1")
        >>> group2 = app['groups']['g2'] = Group(title="Group 2")

    When the person has no calendars in his overlay list, items returns
    an empty list

        >>> from zope.publisher.browser import TestRequest
        >>> from schoolbell.app.security import Principal
        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('', '', person))
        >>> context = person.calendar
        >>> view = CalendarOverlayView(context, request)
        >>> view.items()
        []

    When the person has calendars in his overlay list

        >>> person.overlaid_calendars.add(group2.calendar)
        >>> person.overlaid_calendars.add(group1.calendar, show=False)

        >>> from zope.testing.doctestunit import pprint
        >>> pprint(view.items())
        [{'calendar': <schoolbell.app.cal.Calendar object at ...>,
          'checked': '',
          'color1': '#eed680',
          'color2': '#d1940c',
          'id': u'/groups/g1',
          'title': 'Group 1'},
         {'calendar': <schoolbell.app.cal.Calendar object at ...>,
          'checked': 'checked',
          'color1': '#e0b6af',
          'color2': '#c1665a',
          'id': u'/groups/g2',
          'title': 'Group 2'}]

    """

def doctest_CalendarSelectionView():
    """Tests for CalendarSelectionView

        >>> from schoolbell.app.browser.overlay import CalendarSelectionView
        >>> View = SimpleViewClass('../templates/calendar_selection.pt',
        ...                        bases=(CalendarSelectionView,))

    CalendarSelectionView is a view on IPerson

        >>> from schoolbell.app.app import Person
        >>> from schoolbell.app.security import Principal
        >>> app = setUpSchoolBellSite()
        >>> persons = app['persons']
        >>> fred = persons['fred'] = Person('fred', 'Fred F.')
        >>> eric = persons['eric'] = Person('eric', 'Eric Bjornsen')
        >>> igor = persons['igor'] = Person('igor', 'Igor')
        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('fred', '', fred))
        >>> view = View(fred, request)

    It lists Eric's and Igor's calendars as available for selection

        >>> print view()
        <BLANKLINE>
        ...
          Select calendars to display
        ...
        <fieldset>
          <legend>People</legend>
          <select multiple="multiple" id="people" name="people:list">
            <option value="eric">Eric Bjornsen</option>
            <option value="igor">Igor</option>
          </select>
        </fieldset>
        ...

    If a person's calendar is added to your overlaid calendars list, you
    can see that in the form.

        >>> fred.overlaid_calendars.add(eric.calendar, show=False)

        >>> print view()
        <BLANKLINE>
        ...
          <select multiple="multiple" id="people" name="people:list">
            <option selected="selected" value="eric">Eric Bjornsen</option>
            <option value="igor">Igor</option>
          </select>
        ...

    Note that the user does not see his own calendar in that list:

        >>> 'value="fred"' in view()
        False

    We can submit that form

        >>> request.form["people"] = [u"eric", u"igor"]
        >>> request.form["UPDATE_SUBMIT"] = u"Apply"
        >>> print view()
        <BLANKLINE>
        ...
          <select multiple="multiple" id="people" name="people:list">
            <option selected="selected" value="eric">Eric Bjornsen</option>
            <option selected="selected" value="igor">Igor</option>
          </select>
        ...

    We can see that igor's calendar was added to the list

        >>> igor.calendar in fred.overlaid_calendars
        True

    We can also remove calendars

        >>> request.form["people"] = [u"igor"]
        >>> request.form["UPDATE_SUBMIT"] = u"Apply"
        >>> print view()
        <BLANKLINE>
        ...
          <select multiple="multiple" id="people" name="people:list">
            <option value="eric">Eric Bjornsen</option>
            <option selected="selected" value="igor">Igor</option>
          </select>
        ...

        >>> eric.calendar in fred.overlaid_calendars
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

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                            doctest.REPORT_NDIFF|
                                            doctest.NORMALIZE_WHITESPACE))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.overlay'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
