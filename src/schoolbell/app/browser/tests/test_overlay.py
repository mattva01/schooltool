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
