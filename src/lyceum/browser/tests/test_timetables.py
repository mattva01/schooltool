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
Unit tests for group timetable views.

$Id$
"""
import unittest
from pytz import utc

from zope.app.testing import setup
from zope.testing import doctest
from zope.testing.doctestunit import pprint
from zope.interface import implements
from zope.component import provideAdapter


def doctest_PersonTimetableView_collectTimetableSourceObjects():
    """Tests for PersonTimetableView.

        >>> from lyceum.browser.timetables import PersonTimetableView
        >>> class GroupStub(object):
        ...     def __init__(self):
        ...         self.members = []


        >>> from schooltool.timetable.interfaces import ICompositeTimetables
        >>> class CTTStub(object):
        ...     def __init__(self, source_objects):
        ...         self.source_objects = source_objects
        ...     def collectTimetableSourceObjects(self):
        ...         return self.source_objects

        >>> class PersonStub(object):
        ...     source_objects = []
        ...     def __conform__(self, iface):
        ...         if iface == ICompositeTimetables:
        ...             return CTTStub(self.source_objects)

        >>> group = GroupStub()
        >>> group.__name__ = "teachers"
        >>> person = PersonStub()
        >>> person.gradeclass = ""
        >>> view = PersonTimetableView(person, None)
        >>> view.schooltt_ids
        ['i-ii-kursui', 'iii-iv-kursui']

        >>> person.gradeclass = "1a"
        >>> view.schooltt_ids
        ['i-ii-kursui']

        >>> person.gradeclass = "4b"
        >>> view.schooltt_ids
        ['iii-iv-kursui']

    If there are no members in the group - there are no timetables to
    show:

        >>> view.collectTimetableSourceObjects()
        []

    If there are some members a set of all of their composite
    timetable source objects:

        >>> person.source_objects = ['s1', 's2']
        >>> sorted(list(view.collectTimetableSourceObjects()))
        ['s1', 's2']

    """


def doctest_PersonTimetableView_days():
    """Tests for PersonTimetableView days.

        >>> from schooltool.app.interfaces import ISchoolToolApplication

        >>> class EmptyTimetableStub(dict):
        ...     pass

        >>> from lyceum.browser.timetables import PersonTimetableView
        >>> view = PersonTimetableView(None, None)
        >>> view.makeCompositeTimetable = lambda: EmptyTimetableStub()

    Days is a generator:

        >>> view.days()
        <generator object at ...>

    That returns a list of weekdays when iterated through, but as the
    timetable has no days, the list is empty:

        >>> list(view.days())
        []

    Now if we add a few days with some activities to the timetable:

        >>> class TTDayStub(dict):
        ...     def __init__(self, periods=[]):
        ...         self.periods = periods
        ...         for period in periods:
        ...             self[period] = "<Activities for %s>" % period

        >>> class TimetableStub(dict):
        ...     def __init__(self, keys):
        ...         self._keys = keys
        ...         for key in keys:
        ...             self[key] = TTDayStub()
        ...     def keys(self):
        ...         return self._keys
        >>> timetable = TimetableStub(['Monday', 'Tuesday', 'Wednesday'])
        >>> view.makeCompositeTimetable = lambda: timetable
        >>> list(view.days())
        [{'periods': [], 'title': u'Monday'},
         {'periods': [], 'title': u'Tuesday'},
         {'periods': [], 'title': u'Wednesday'}]

    Days are grouped nicely into 2 columns by the function rows:

        >>> view.rows()
        [({'periods': [], 'title': u'Monday'}, {'periods': [], 'title': u'Tuesday'}),
         ({'periods': [], 'title': u'Wednesday'}, None)]

        >>> timetable = TimetableStub(['Monday', 'Tuesday'])
        >>> view.rows()
        [({'periods': [], 'title': u'Monday'}, {'periods': [], 'title': u'Tuesday'})]

    Slots for every period in the day with all the activities in it
    are displayed as well:

        >>> timetable['Monday'] = TTDayStub(['a', 'b'])
        >>> timetable['Tuesday'] = TTDayStub(['c', 'd'])
        >>> pprint(list(view.days()))
        [{'periods': [{'activities': '<Activities for a>', 'title': 'a'},
                      {'activities': '<Activities for b>', 'title': 'b'}],
          'title': u'Monday'},
         {'periods': [{'activities': '<Activities for c>', 'title': 'c'},
                      {'activities': '<Activities for d>', 'title': 'd'}],
          'title': u'Tuesday'}]

    """

class TimetableStub(dict):
    _activities = []
    def activities(self):
        return self._activities


class TimetableDayStub(object):
    def __init__(self, day_id):
        self.day_id = day_id
        self.periods = []
    def add(self, period, activity, send_events):
        self.periods.append([('id', period),
                             ('activity', activity),
                             ('sent_events', send_events)])
    def __repr__(self):
        return '<Day id=%s periods=%s>' % (self.day_id, self.periods)


def doctest_PersonTimetableView_makeCompositeTimetable():
    """Tests PersonTimetableView makeCompositeTimetable.

        >>> timetable = "School timetable"
        >>> class STTStub(object):
        ...     def createTimetable(self):
        ...         return timetable

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class AppStub(dict):
        ...     implements(ISchoolToolApplication)
        ...     def __init__(self, context):
        ...         self['ttschemas'] = {'i-ii-kursui': STTStub()}

        >>> class PersonStub(object):
        ...     gradeclass = '1a'

        >>> from lyceum.browser.timetables import PersonTimetableView
        >>> view = PersonTimetableView(PersonStub(), None)
        >>> view.collectTimetableSourceObjects = lambda: []

        >>> provideAdapter(AppStub, adapts=[None])

    When there are no timetable source objects, the original timetable
    (created from the school timetable) is returned:

        >>> view.makeCompositeTimetable()
        'School timetable'

    But if there are source objects all the activites in them are put
    into the result timetable.

        >>> class TimetablesStub(object):
        ...     def __init__(self):
        ...         self.timetables = {'term.i-ii-kursui': TimetableStub()}

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> class TimetableSourceStub(object):
        ...     def __init__(self):
        ...         self.timetables = TimetablesStub()
        ...     def __conform__(self, iface):
        ...         if iface == ITimetables:
        ...             return self.timetables

     The initial timetable that we normaly get out of the school
     timetable storage is empty, but has 3 days:

        >>> timetable = TimetableStub()
        >>> timetable._activiites = []
        >>> timetable["day1"] = TimetableDayStub("day1")
        >>> timetable["day2"] = TimetableDayStub("day2")
        >>> timetable["day3"] = TimetableDayStub("day3")

     Both sources must have at most 3 days with identical ids and
     every day has a list of activities:

        >>> source1 = TimetableSourceStub()
        >>> source1.timetables.timetables['term.i-ii-kursui']._activities = [
        ...     ("day1", "period1", "History"),
        ...     ("day1", "period2", "Math"),
        ...     ("day2", "period4", "Art")]
        >>> source2 = TimetableSourceStub()
        >>> source2.timetables.timetables['term.i-ii-kursui']._activities = [
        ...     ("day1", "period1", "Algebra"),
        ...     ("day3", "period2", "Physics"),
        ...     ("day3", "period4", "Art")]

     We stub the view method to return our fake timetable source objects:

        >>> view.collectTimetableSourceObjects = lambda: [source1, source2]
        >>> view.term_id = lambda : 'term'

     And the timetable composition code gets all the activities from
     all the days and puts them into the composite timetable, no
     events are being sent so that subscribers that act upon changes
     in timetables would not do anything with our temporary timetable:

        >>> pprint(view.makeCompositeTimetable())
        {'day1': <Day id=day1
           periods=[[('id', 'period1'), ('activity', 'History'), ('sent_events', False)],
                    [('id', 'period2'), ('activity', 'Math'), ('sent_events', False)],
                    [('id', 'period1'), ('activity', 'Algebra'), ('sent_events', False)]]>,
         'day2': <Day id=day2
           periods=[[('id', 'period4'), ('activity', 'Art'), ('sent_events', False)]]>,
         'day3': <Day id=day3
           periods=[[('id', 'period2'), ('activity', 'Physics'), ('sent_events', False)],
                    [('id', 'period4'), ('activity', 'Art'), ('sent_events', False)]]>}

    """


def doctest_GroupTimetableView():
    """Tests for GroupTimetableView.

        >>> from lyceum.browser.timetables import GroupTimetableView
        >>> class GroupStub(object):
        ...     def __init__(self):
        ...         self.members = []

        >>> group = GroupStub()
        >>> group.__name__ = "teachers"
        >>> view = GroupTimetableView(group, None)
        >>> view.schooltt_ids
        ['i-ii-kursui', 'iii-iv-kursui']

        >>> group.__name__ = "1a"
        >>> view.schooltt_ids
        ['i-ii-kursui']

        >>> group.__name__ = "4b"
        >>> view.schooltt_ids
        ['iii-iv-kursui']

    If there are no members in the group - there are no timetables to
    show:

        >>> view.collectTimetableSourceObjects()
        set([])

    If there are some members a set of all of their composite
    timetable source objects:

        >>> from schooltool.timetable.interfaces import ICompositeTimetables
        >>> class CTTStub(object):
        ...     def __init__(self, source_objects):
        ...         self.source_objects = source_objects
        ...     def collectTimetableSourceObjects(self):
        ...         return self.source_objects

        >>> class Member(object):
        ...     def __init__(self, *source_objects):
        ...         self.source_objects = source_objects
        ...     def __conform__(self, iface):
        ...         if iface == ICompositeTimetables:
        ...             return CTTStub(self.source_objects)
        >>> group.members = [Member("s1", "s2"), Member("s2", "s3")]
        >>> sorted(list(view.collectTimetableSourceObjects()))
        ['s1', 's2', 's3']

    """


def doctest_ResourceTimetableView():
    """Tests for ResourceTimetableView.

        >>> events = []

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> from lyceum.browser.timetables import ResourceTimetableView
        >>> class PersonStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == ISchoolToolCalendar:
        ...             return events

        >>> view = ResourceTimetableView(PersonStub(), None)
        >>> view.schooltt_ids
        ['i-ii-kursui', 'iii-iv-kursui']

        >>> class STTStub(object):
        ...     def createTimetable(self):
        ...         timetable = TimetableStub()
        ...         timetable["Monday"] = TimetableDayStub("Monday")
        ...         timetable["Tuesday"] = TimetableDayStub("Tuseday")
        ...         timetable["Wednesday"] = TimetableDayStub("Wednesday")
        ...         return timetable

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class AppStub(dict):
        ...     implements(ISchoolToolApplication)
        ...     def __init__(self, context):
        ...         self['ttschemas'] = {'i-ii-kursui': STTStub()}

        >>> provideAdapter(AppStub, adapts=[None])

    If there are no events in the calendar, the timetable is empty:

        >>> pprint(view.makeCompositeTimetable())
        {'Monday': <Day id=Monday periods=[]>,
         'Tuesday': <Day id=Tuseday periods=[]>,
         'Wednesday': <Day id=Wednesday periods=[]>}

    Non-timetable events are ignored as well:

        >>> events = ["event1", "event2"]
        >>> pprint(view.makeCompositeTimetable())
        {'Monday': <Day id=Monday periods=[]>,
         'Tuesday': <Day id=Tuseday periods=[]>,
         'Wednesday': <Day id=Wednesday periods=[]>}

    Now if there are timetable events, their activities get added to
    the composite timetable:

        >>> from schooltool.timetable.interfaces import ITimetableCalendarEvent
        >>> class TTEventStub(object):
        ...     implements(ITimetableCalendarEvent)
        ...     def __init__(self, day_id, period_id, activity):
        ...         self.day_id = day_id
        ...         self.period_id = period_id
        ...         self.activity = activity
        >>> events = [TTEventStub("Monday", "Period 1", "History"),
        ...           TTEventStub("Tuesday", "Period 2", "Art"),
        ...           TTEventStub("Wednesday", "Period 1", "English")]
        >>> pprint(view.makeCompositeTimetable())
        {'Monday': <Day id=Monday periods=[[('id', 'Period 1'),
                                            ('activity', 'History'),
                                            ('sent_events', False)]]>,
         'Tuesday': <Day id=Tuseday periods=[[('id', 'Period 2'),
                                              ('activity', 'Art'),
                                              ('sent_events', False)]]>,
         'Wednesday': <Day id=Wednesday periods=[[('id', 'Period 1'),
                                                  ('activity', 'English'),
                                                  ('sent_events', False)]]>}

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
