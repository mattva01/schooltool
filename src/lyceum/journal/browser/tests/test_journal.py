#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Unit tests for lyceum journal.

$Id$
"""
import unittest
from pytz import timezone
from pytz import utc
from datetime import datetime

from zope.app.testing import setup
from zope.component import provideAdapter
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.traversing.interfaces import IContainmentRoot
from zope.interface import directlyProvides


def doctest_today():
    """Test for today.

    Today returns the date of today, according to the application
    prefered timezone:

        >>> from lyceum.journal.browser.journal import today
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> tz_name = "Europe/Vilnius"
        >>> class PrefStub(object):
        ...     @property
        ...     def timezone(self):
        ...         return tz_name

        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         pass
        ...     def __conform__(self, iface):
        ...         if iface == IApplicationPreferences:
        ...             return PrefStub()

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> current_time = timezone('UTC').localize(datetime.utcnow())

        >>> tz_name = 'Pacific/Midway'
        >>> tz = timezone(tz_name)
        >>> today_date = current_time.astimezone(tz).date()
        >>> today() == today_date
        True

        >>> tz_name = 'Pacific/Funafuti'
        >>> tz = timezone('Pacific/Funafuti')
        >>> today_date = current_time.astimezone(tz).date()
        >>> today() == today_date
        True

    """


def doctest_JournalCalendarEventViewlet():
    """Tests for JournalCalendarEventViewlet.

        >>> from lyceum.journal.browser.journal import JournalCalendarEventViewlet
        >>> viewlet = JournalCalendarEventViewlet()

        >>> class ManagerStub(object):
        ...     pass
        >>> class EFDStub(object):
        ...     pass
        >>> class EventStub(object):
        ...     pass
        >>> manager = ManagerStub()
        >>> manager.event = EFDStub()
        >>> manager.event.context = EventStub()

    If the event is not adaptable to a journal, nothing is shown:

        >>> viewlet.manager = manager
        >>> viewlet.attendanceLink() is None
        True

    Though if it has a journal, you should get a URL for the journal
    with the event id passed as a parameter:

        >>> from schooltool.timetable.interfaces import ITimetableCalendarEvent
        >>> from lyceum.journal.interfaces import ILyceumJournal
        >>> class JournalStub(object):
        ...     __name__ = 'journal'

        >>> class TTEventStub(object):
        ...     implements(ITimetableCalendarEvent)
        ...     def __init__(self):
        ...         self.unique_id = "unique&id"
        ...     def __conform__(self, iface):
        ...         if iface == ILyceumJournal:
        ...             journal = JournalStub()
        ...             journal.__parent__ = self
        ...             return journal

        >>> manager.event.context = TTEventStub()
        >>> viewlet.request = TestRequest()
        >>> directlyProvides(manager.event.context, IContainmentRoot)
        >>> viewlet.attendanceLink()
        'http://127.0.0.1/journal/index.html?event_id=unique%26id'

    """


def doctest_PersonGradesColumn():
    """Tests for PersonGradesColumn.

        >>> from lyceum.journal.browser.journal import PersonGradesColumn
        >>> dtstart = datetime(2005, 1, 1, 23, 0)
        >>> dtstart = utc.localize(dtstart)

        >>> from lyceum.journal.interfaces import ILyceumJournal
        >>> class JournalStub(object):
        ...     __name__ = 'journal'
        ...     def getGrade(self, person, meeting, default=None):
        ...         return "<Grade for %s in %s, default='%s'>" % (
        ...             person, meeting.unique_id, default)

        >>> class MeetingStub(object):
        ...     dtstart = dtstart
        ...     def __conform__(self, iface):
        ...         if iface == ILyceumJournal:
        ...             journal = JournalStub()
        ...             journal.__parent__ = self
        ...             return journal

        >>> meeting = MeetingStub()
        >>> meeting.unique_id = "uid"
        >>> column = PersonGradesColumn(meeting)

        >>> tz_name = "Europe/Vilnius"
        >>> class PrefStub(object):
        ...     @property
        ...     def timezone(self):
        ...         return tz_name

        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         pass
        ...     def __conform__(self, iface):
        ...         if iface == IApplicationPreferences:
        ...             return PrefStub()

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> column.meetingDate()
        datetime.date(2005, 1, 2)

        >>> tz_name = "UTC"

        >>> column.meetingDate()
        datetime.date(2005, 1, 1)


        >>> student = "John"
        >>> column.getCellValue(student)
        "<Grade for John in uid, default=''>"

    """


def doctest_SelectedPersonGradesColumn():
    """
    """


def doctest_LyceumJournalView():
    """
    """


def doctest_JournalAbsoluteURL():
    """
    """


def doctest_JournalBreadcrumbs():
    """
    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
