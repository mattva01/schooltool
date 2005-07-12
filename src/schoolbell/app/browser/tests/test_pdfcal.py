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
Tests for SchoolBell calendaring views.

$Id$
"""

import unittest
from datetime import datetime, date, timedelta
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from schoolbell.app.app import Person
from schoolbell.app.cal import CalendarEvent


from schoolbell.app.browser.pdfcal import registerFontPath, setUpMSTTCoreFonts
# XXX temporary workaround -- will not work on systems without msttcorefonts
font_path = '/usr/share/fonts/truetype/msttcorefonts'
registerFontPath(font_path)
setUpMSTTCoreFonts()



def doctest_DailyCalendarView():
    """Tests for DailyCalendarView.

        >>> from schoolbell.app.browser.pdfcal import DailyCalendarView

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> person = Person(title="Mr. Smith")
        >>> view = DailyCalendarView(person.calendar, request)

        >>> print view.pdfdata()
        %PDF-1.3...
        ...

        >>> request.response.getHeader('Content-Type')
        'application/pdf'
        >>> request.response.getHeader('Accept-Ranges')
        'bytes'

    """


def doctest_DailyCalendarView_buildStory():
    r"""Tests for DailyCalendarView.buildStory.

    buildStory returns a list of platypus objects.

        >>> from schoolbell.app.browser.pdfcal import DailyCalendarView
        >>> calendar = Person(title="Mr. Smith").calendar
        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = DailyCalendarView(calendar, request)

#        TODO: test header
        >>> view.buildStory(date(2005, 7, 8))
        [...
        ...
        ...]

        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(minutes=72), "Some event")
        >>> calendar.addEvent(evt)

        >>> story = view.buildStory(date(2005, 7, 8))
        >>> len(story)
        5
        >>> story[1].text
        'Mr. Smith'
        >>> story[2].text
        '2005-07-08'
        >>> story[3]
        Spacer(0, ...)
        >>> story[4]._cellvalues[0][0].text
        '09:10-10:22'
        >>> story[4]._cellvalues[0][1].text
        'Some event'

        >>> evt = CalendarEvent(datetime(2005, 7, 8), timedelta, "Some event")
        >>> calendar.addEvent(evt)

    """


def doctest_DailyCalendarView_buildStory_unicode():
    r"""Tests for DailyCalendarView.buildStory.

    Unicode text is treated properly:

        >>> from schoolbell.app.browser.pdfcal import DailyCalendarView
        >>> person = Person(title=u"\u0105 person")
        >>> calendar = person.calendar
        >>> evt = CalendarEvent(datetime(2005, 7, 8, 9, 10),
        ...                     timedelta(hours=5), u"\u0105 event")
        >>> calendar.addEvent(evt)

        >>> request = TestRequest(form={'date': '2005-07-08'})
        >>> view = DailyCalendarView(calendar, request)
        >>> story = view.buildStory(date(2005, 7, 8))

        >>> len(story)
        5
        >>> story[1].text
        '\xc4\x85 person'
        >>> story[2].text
        '2005-07-08'
        >>> story[4]._cellvalues[0][1].text
        '\xc4\x85 event'

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(optionflags=doctest.ELLIPSIS))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.pdfcal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
