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
Tests for schooltool timetabling views.

$Id$
"""

import unittest
import datetime

from zope.i18n import translate
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.testing.doctestunit import pprint

from schooltool.app.browser import testing
from schooltool.testing import setup as sbsetup


def setUp(test=None):
    testing.setUp(test)
    sbsetup.setupTimetabling()
    sbsetup.setUpApplicationPreferences()

tearDown = testing.tearDown


def createSchema(days, *periods_for_each_day):
    """Create a timetable schema.

    Example:

        createSchema(['D1', 'D2', 'D3'], ['A'], ['B', 'C'], ['D'])

    creates a schema with three days, the first of which (D1) has one
    period (A), the second (D2) has two periods (B and C), and the third
    (D3) has again one period (D).
    """

    from schooltool.timetable.schema import TimetableSchema
    from schooltool.timetable.schema import TimetableSchemaDay
    schema = TimetableSchema(days)
    for day, periods in zip(days, periods_for_each_day):
        schema[day] = TimetableSchemaDay(list(periods))
    return schema


def createDayTemplate(periods):
    """Create a SchooldayTemplate.

    Example:

        createDayTemplate([(9, 30, 45),
                           (10, 30, 45)])

    would create a day template containing two periods, the first one starting
    at 9:30, the second one starting at 10:30, both 45 minutes long.
    """
    from schooltool.timetable import SchooldayTemplate
    from schooltool.timetable import SchooldaySlot
    day = SchooldayTemplate()
    for h, m, duration in periods:
        day.add(SchooldaySlot(datetime.time(h, m),
                              datetime.timedelta(minutes=duration)))
    return day




def doctest_TimetablesTraverser():
    """Tests for TimetablesTraverser.

        >>> from schooltool.timetable.browser import TimetablesTraverser
        >>> from schooltool.timetable.interfaces import ITimetables
        >>> class TimetablesStub:
        ...     implements(ITimetables)
        ...     timetables = 'Timetables'
        ...     calendar = 'Calendar'
        >>> request = TestRequest()
        >>> t = TimetablesTraverser(TimetablesStub(), request)

    If we ask for timetables, the corresponding object will be returned:

        >>> t.publishTraverse(request, 'timetables')
        'Timetables'
    """


def print_cal(calendar, day_format='%(number)3d'):
    """Print a calendar as returned by TermRenderer.calendar."""
    for month in calendar:
        title = '%s %d' % (month['month'], month['year'])
        print '*%35s' % title
        print '         Mon Tue Wed Thu Fri Sat Sun'
        for week in month['weeks']:
            s = ['Week %-2d:' % week['number']]
            for day in week['days']:
                if day['number'] is None:
                    s.append('   ')
                else:
                    s.append(day_format % day)
            print ' '.join(s).rstrip()


def doctest_TimetableView():
    '''Test for TimetableView.

        >>> from schooltool.timetable.browser import TimetableView
        >>> from schooltool.timetable import Timetable
        >>> from schooltool.timetable import TimetableDay, TimetableActivity
        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from schooltool.course.section import Section

    Create some context:

        >>> s = Section()
        >>> ITimetables(s).timetables['term.schema'] = tt = Timetable(['day 1'])
        >>> tt['day 1'] = ttd = TimetableDay(['A'])
        >>> ttd.add('A', TimetableActivity('Something'))

        >>> request = TestRequest()
        >>> view = TimetableView(tt, request)

    title() returns the view's title:

        >>> translate(view.title())
        u"Section\'s timetable"

    rows() delegates the job to format_timetable_for_presentation:

        >>> view.rows()
        [[{'period': 'A', 'activity': 'Something'}]]

    '''


def doctest_PersonTimetableSetupView():
    '''Doctest for the PersonTimetableSetupView view

    We will need an application object

        >>> app = sbsetup.setupSchoolToolSite()

    and a Person from that application

        >>> from schooltool.person.person import Person
        >>> from schooltool.group.group import Group
        >>> context = Person("student", "Steven Udent")
        >>> app["persons"]["whatever"] = context
        >>> app["groups"]["juniors"] = juniors = Group("Juniors")
        >>> juniors.members.add(context)

    We will need some sections

        >>> from schooltool.course.section import Section
        >>> app["sections"]["math"] = math = Section("Math")
        >>> app["sections"]["biology"] = biology = Section("Biology")
        >>> app["sections"]["physics"] = physics = Section("Physics")
        >>> app["sections"]["history"] = history = Section("History")

    We will also need a timetable schema, and a term.  Two of each, in fact.

        >>> app["ttschemas"]["default"] = createSchema(["Mon", "Tue"],
        ...                                            ["9:00", "10:00"],
        ...                                            ["9:00", "10:00"])
        >>> app["ttschemas"]["other"] = createSchema([], [])

        >>> from schooltool.timetable.term import Term
        >>> app["terms"]["2005-spring"] = Term('2005 Spring',
        ...                                    datetime.date(2004, 2, 1),
        ...                                    datetime.date(2004, 6, 30))
        >>> app["terms"]["2005-fall"] = Term('2005 Fall',
        ...                                    datetime.date(2004, 9, 1),
        ...                                    datetime.date(2004, 12, 31))

    We can now create the view.

        >>> from schooltool.timetable.browser import PersonTimetableSetupView
        >>> request = TestRequest()
        >>> view = PersonTimetableSetupView(context, request)

    There are two helper methods, getSchema and getTerm, that extract the
    schema and term from the request, or pick suitable defaults.

        >>> view.getSchema() is app["ttschemas"].getDefault()
        True
        >>> request.form['ttschema'] = 'other'
        >>> view.getSchema() is app["ttschemas"]["other"]
        True
        >>> request.form['ttschema'] = 'default'
        >>> view.getSchema() is app["ttschemas"]["default"]
        True

    The default for a term is "the current term", or, if there\'s none, the
    next one.  Since this depends on today\'s date, we can\'t explicitly test
    it here.

        >>> (view.getTerm() is app["terms"]["2005-spring"] or
        ...  view.getTerm() is app["terms"]["2005-fall"])
        True
        >>> request.form['term'] = '2005-spring'
        >>> view.getTerm() is app["terms"]["2005-spring"]
        True
        >>> request.form['term'] = '2005-fall'
        >>> view.getTerm() is app["terms"]["2005-fall"]
        True

    sectionMap finds out which sections are scheduled in which timetable slots.

        >>> term = app["terms"]["2005-fall"]
        >>> ttschema = app["ttschemas"]["default"]
        >>> section_map = view.sectionMap(term, ttschema)

        >>> from zope.testing.doctestunit import pprint
        >>> pprint(section_map)
        {('Mon', '10:00'): Set([]),
         ('Mon', '9:00'): Set([]),
         ('Tue', '10:00'): Set([]),
         ('Tue', '9:00'): Set([])}

    It gets more interesting when sections actually have some scheduled
    activities:

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from schooltool.timetable import TimetableActivity
        >>> ttkey = "2005-fall.default"
        >>> ITimetables(math).timetables[ttkey] = ttschema.createTimetable()
        >>> ITimetables(math).timetables[ttkey]['Tue'].add('10:00',
        ...                                   TimetableActivity('Math'))

        >>> ITimetables(history).timetables[ttkey] = ttschema.createTimetable()
        >>> ITimetables(history).timetables[ttkey]['Tue'].add('10:00',
        ...                                   TimetableActivity('History'))

        >>> section_map = view.sectionMap(term, ttschema)
        >>> pprint(section_map)
        {('Mon', '10:00'): Set([]),
         ('Mon', '9:00'): Set([]),
         ('Tue', '10:00'): Set([<schooltool.course.section.Section ...>]),
         ('Tue', '9:00'): Set([])}

    allSections simply takes a union of a number of sets containing sections.

        >>> from sets import Set
        >>> sections = view.allSections({1: Set([math]),
        ...                              2: Set([math, biology]),
        ...                              3: Set([])})
        >>> sections = [s.title for s in sections]
        >>> sections.sort()
        >>> sections
        ['Biology', 'Math']

    getDays does most of the work

        >>> def printDays(days):
        ...     for day in days:
        ...         print day['title']
        ...         for period in day['periods']:
        ...             sections = [s.title for s in period['sections']]
        ...             selected = [s and s.title or "none"
        ...                         for s in period['selected']]
        ...             print "%7s: [%s] [%s]" % (period['title'],
        ...                                       ', '.join(sections),
        ...                                       ', '.join(selected))

        >>> days = view.getDays(ttschema, section_map)
        >>> printDays(days)
        Mon
           9:00: [] [none]
          10:00: [] [none]
        Tue
           9:00: [] [none]
          10:00: [History, Math] [none]

        >>> math.members.add(context)

        >>> days = view.getDays(ttschema, section_map)
        >>> printDays(days)
        Mon
           9:00: [] [none]
          10:00: [] [none]
        Tue
           9:00: [] [none]
          10:00: [History, Math] [Math]

    And finally, __call__ ties everything together -- it processes the form and
    renders a page template.

        >>> print view()
        <BLANKLINE>
        ...
        <title> Scheduling for Steven Udent </title>
        ...
        <h1> Scheduling for Steven Udent </h1>
        ...
        <form class="plain" method="post" action="http://127.0.0.1">
        ...
            <label for="term">Term</label>
            <select id="term" name="term">
              <option value="2005-spring">2005 Spring</option>
              <option selected="selected" value="2005-fall">2005 Fall</option>
            </select>
            <label for="ttschema">Schema</label>
            <select id="ttschema" name="ttschema">
              <option selected="selected" value="default">default</option>
              <option value="other">other</option>
            </select>
        ...
        </form>
        <form class="plain" method="post" action="http://127.0.0.1">
          <input type="hidden" name="term" value="2005-fall" />
          <input type="hidden" name="ttschema" value="default" />
        ...
            <h2>Mon</h2>
        ...
                <th>9:00</th>
                <td>
                  <select name="sections:list">
                    <option value="" selected="selected">none</option>
                  </select>
        ...
            <h2>Tue</h2>
        ...
                <th>10:00</th>
                <td>
                  <select name="sections:list">
                    <option value="">none</option>
                    <option value="history"> -- </option>
                    <option selected="selected" value="math"> -- </option>
                  </select>
        ...
        </form>
        ...

    If the form contains 'SAVE', the form gets processed.  Suppose we unselect
    Math

        >>> request.form['SAVE'] = 'Save'
        >>> request.form['sections'] = ['']
        >>> content = view()

        >>> context in math.members
        False

    If we select it back

        >>> request.form['SAVE'] = 'Save'
        >>> request.form['sections'] = ['math']
        >>> content = view()

        >>> context in math.members
        True

        >>> math.members.remove(context)

        >>> days = view.getDays(ttschema, section_map)
        >>> printDays(days)
        Mon
           9:00: [] [none]
          10:00: [] [none]
        Tue
           9:00: [] [none]
          10:00: [History, Math] [none]

    When people are members of a section as part of a form (group) we don\'t
    allow changing that period from here.  They must be removed from the
    group.

        >>> math.members.add(juniors)

        >>> print view()
        <BLANKLINE>
        ...
        <title> Scheduling for Steven Udent </title>
        ...
            <h2>Tue</h2>
        ...
                <th>10:00</th>
                <td>
                  <a href="http://127.0.0.1/sections/math">Math</a>
                  <span class="hint">
                    <span>as part of</span>
                    <a href="http://127.0.0.1/groups/juniors">Juniors</a>
                  </span>
                </td>
        ...


        >>> history.members.add(juniors)
        >>> print view()
        <BLANKLINE>
        ...
        <title> Scheduling for Steven Udent </title>
        ...
            <h2>Tue</h2>
        ...
        <BLANKLINE>
              <tr class="conflict">
                <th>10:00</th>
                <td>
                  <a href="http://127.0.0.1/sections/history">History</a>
                  <span class="hint">
                  <span>as part of</span>
                  <a href="http://127.0.0.1/groups/juniors">Juniors</a>
                </span>
              </td>
                <td>
                  <a href="http://127.0.0.1/sections/math">Math</a>
                  <span class="hint">
                    <span>as part of</span>
                    <a href="http://127.0.0.1/groups/juniors">Juniors</a>
                  </span>
                </td>
              <td class="conflict">
              Scheduling conflict.
              </td>
            </tr>
        <BLANKLINE>
        ...

    '''


def doctest_PersonTimetableSetupView_no_timetables():
    '''Doctest for the PersonTimetableSetupView view

    What if there are no terms/timetable schemas?

    We will need an application object

        >>> app = sbsetup.setupSchoolToolSite()

    and a Person from that application

        >>> from schooltool.person.person import Person
        >>> context = Person("student", "Steven Udent")
        >>> app["persons"]["whatever"] = context

    We can now create the view.

        >>> from schooltool.timetable.browser import PersonTimetableSetupView
        >>> request = TestRequest()
        >>> view = PersonTimetableSetupView(context, request)

    What does __call__ do?

        >>> print view()
        <BLANKLINE>
        ...
        <title> Scheduling for Steven Udent </title>
        ...
        <h1> Scheduling for Steven Udent </h1>
        ...
        <p>There are no terms or timetable schemas defined.</p>
        ...

    '''


def doctest_PersonTimetableSetupView_no_default_ttschema():
    '''Doctest for the PersonTimetableSetupView view

    What if there is no default timetable schema?

    We will need an application object

        >>> app = sbsetup.setupSchoolToolSite()

    and a Person from that application

        >>> from schooltool.person.person import Person
        >>> context = Person("student", "Steven Udent")
        >>> app["persons"]["whatever"] = context

    There is one timetable schema, but it is not the default one.

        >>> app["ttschemas"]["default"] = createSchema(["Mon", "Tue"],
        ...                                            ["9:00", "10:00"],
        ...                                            ["9:00", "10:00"])
        >>> app["ttschemas"]["other"] = createSchema([], [])
        >>> del app["ttschemas"]["default"]
        >>> app["ttschemas"].default_id is None
        True

    We can now create the view.

        >>> from schooltool.timetable.browser import PersonTimetableSetupView
        >>> request = TestRequest()
        >>> view = PersonTimetableSetupView(context, request)

    What does getSchema return?

        >>> view.getSchema() is app["ttschemas"]["other"]
        True

    '''


def doctest_SectionTimetableSetupView():
    '''Doctest for the SectionTimetableSetupView view

    We will need an application object

        >>> app = sbsetup.setupSchoolToolSite()

    We will need a section

        >>> from schooltool.course.section import Section
        >>> from schooltool.timetable.interfaces import ITimetables
        >>> app["sections"]["math"] = math = Section("Math")
        >>> ITimetables(math).timetables.keys()
        []

    We will also need a timetable schema, and a term.

        >>> app["ttschemas"]["default"] = createSchema(["Mon", "Tue"],
        ...                                            ["9:00", "10:00"],
        ...                                            ["9:00", "10:00"])


        >>> from schooltool.timetable.term import Term
        >>> app["terms"]["2005-spring"] = Term('2005 Spring',
        ...                                    datetime.date(2004, 2, 1),
        ...                                    datetime.date(2004, 6, 30))

    We can now create the view to look at the Math timetable

        >>> from schooltool.timetable.browser import SectionTimetableSetupView
        >>> context = math
        >>> request = TestRequest()
        >>> view = SectionTimetableSetupView(context, request)

    We have some helper methods to simplify the form if there\'s only one
    option for terms or schemas:

        >>> view.app = app
        >>> view.singleTerm()
        True
        >>> view.singleSchema()
        True

    Another term and schema:

        >>> app["ttschemas"]["other"] = createSchema([], [])
        >>> app["terms"]["2005-fall"] = Term('2005 Fall',
        ...                                    datetime.date(2004, 9, 1),
        ...                                    datetime.date(2004, 12, 31))

        >>> view.singleTerm()
        False
        >>> view.singleSchema()
        False

    We have getSchema from the Mixin class to get the schema from the request
    or choose a default.

        >>> view.getSchema() is app["ttschemas"].getDefault()
        True
        >>> request.form['ttschema'] = 'other'
        >>> view.getSchema() is app["ttschemas"]["other"]
        True
        >>> request.form['ttschema'] = 'default'
        >>> view.getSchema() is app["ttschemas"]["default"]
        True

    getTerms will give us a list of available terms from the request or a list
    with just the current term if we're working at a time not during any term.

    Without any terms in the request we get the output of getNextTermForDate
    today

        >>> import datetime
        >>> from schooltool.timetable.term import getNextTermForDate
        >>> getNextTermForDate(datetime.date.today()) in view.getTerms()
        True
        >>> len(view.getTerms())
        1

        >>> request.form['terms'] = ['2005-spring', '2005-fall']
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-spring', u'2005-fall']

        >>> request.form['terms'] = ['2005-spring']
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-spring']

        >>> request.form['terms'] = ['2005-fall']
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-fall']

    Single terms may be returned as a single string, rather than a list:

        >>> request.form['terms'] = '2005-spring'
        >>> [t.__name__ for t in view.getTerms()]
        [u'2005-spring']

    If we cancel the form, we get redirected to the section

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/sections/math'

    If we save the form, we\'re redirected to the timetable view for the schema
    that we just saved:

        >>> request = TestRequest(form={'SAVE': 'Save'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/sections/math/timetables/2005-fall.default'

    An empty save request will create an empty timetable:

        >>> ITimetables(math).timetables['2005-fall.default']
        <Timetable: ...>
        >>> ITimetables(math).timetables['2005-fall.default']['Mon'].items()
        [('9:00', Set([])), ('10:00', Set([]))]
        >>> ITimetables(math).timetables['2005-fall.default']['Tue'].items()
        [('9:00', Set([])), ('10:00', Set([]))]

    Let\'s add some scheduled classes:

        >>> request = TestRequest(form={'ttschema': 'default',
        ...                             'term': '2005-fall',
        ...                             'Mon.9:00':'ON',
        ...                             'Tue.9:00':'ON',
        ...                             'SAVE': 'Save'})

        >>> view = SectionTimetableSetupView(context, request)

    The first time we view the page all the events are off:

        >>> print view()
        ...
        <BLANKLINE>
        ...
                            id="Mon.9:00" value="Mon.9:00"
        ...
                            id="Mon.10:00" value="Mon.10:00"
        ...
                            id="Tue.9:00" value="Tue.9:00"
        ...
                            id="Tue.10:00" value="Tue.10:00"
        ...


    Now we have a schedule for our course:

        >>> ITimetables(math).timetables['2005-fall.default']['Mon']['9:00']
        Set([TimetableActivity('', ...
        >>> ITimetables(math).timetables['2005-fall.default']['Mon']['10:00']
        Set([])
        >>> ITimetables(math).timetables['2005-fall.default']['Tue']['9:00']
        Set([TimetableActivity('', ...
        >>> ITimetables(math).timetables['2005-fall.default']['Tue']['10:00']
        Set([])

        >>> request = TestRequest(form={'ttschema': 'default',
        ...                             'term': '2005-fall',
        ...                             'Mon.9:00':'ON',
        ...                             'SAVE': 'Save'})

    Since we don\'t have an update() method, we call the page again to see our
    last changes, all the periods that were 'ON' are now checked:

        >>> view = SectionTimetableSetupView(context, request)
        >>> print view()
        ...
        <BLANKLINE>
        ...
                            checked="checked" id="Mon.9:00"
        ...
                            id="Mon.10:00" value="Mon.10:00"
        ...
                            checked="checked" id="Tue.9:00"
        ...
                            id="Tue.10:00" value="Tue.10:00"
        ...

    To remove a period from our schedule we create a new save request without
    that period listed.

        >>> view = SectionTimetableSetupView(context, request)
        >>> print view()
        ...
        <BLANKLINE>
        ...
                            checked="checked" id="Mon.9:00"
        ...
                            id="Mon.10:00" value="Mon.10:00"
        ...
                            id="Tue.9:00" value="Tue.9:00"
        ...
                            id="Tue.10:00" value="Tue.10:00"
        ...

    Tuesday\'s Activity is no longer there:

        >>> ITimetables(math).timetables['2005-fall.default']['Tue']['9:00']
        Set([])


    '''


def test_suite():
    suite = unittest.TestSuite()
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.REPORT_ONLY_FIRST_FAILURE |
                   doctest.NORMALIZE_WHITESPACE)
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    suite.addTest(doctest.DocTestSuite('schooltool.timetable.browser',
                                       optionflags=optionflags))
    suite.addTest(doctest.DocFileSuite(
        'emergencydays.txt', setUp=setUp, tearDown=tearDown,
        globs={'createSchema': createSchema,
               'createDayTemplate': createDayTemplate,
               'pprint': pprint},
        optionflags=optionflags))
    suite.addTest(doctest.DocFileSuite(
        'specialdays.txt', setUp=setUp, tearDown=tearDown,
        globs={'createSchema': createSchema,
               'createDayTemplate': createDayTemplate,
               'pprint': pprint},
        optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
