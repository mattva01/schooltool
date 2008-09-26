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

from zope.component import adapter
from zope.component import provideAdapter
from zope.interface import Interface
from zope.interface import implementer
from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.testing.doctestunit import pprint
from zope.app.testing import ztapi

from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.schoolyear import getSchoolYearContainer
from schooltool.app.browser import testing
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import IOwnTimetables
from schooltool.app.app import getSchoolToolApplication
from schooltool.timetable import TimetablesAdapter
from schooltool.term.term import getTermContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.testing import setup as sbsetup


def setUp(test=None):
    testing.setUp(test)
    sbsetup.setUpTimetabling()
    sbsetup.setUpApplicationPreferences()
    ztapi.provideAdapter(None, ISchoolToolApplication,
                         getSchoolToolApplication)
    provideAdapter(getTermContainer, [Interface], ITermContainer)
    provideAdapter(getSchoolYearContainer)


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
    """Test for TimetableView.

        >>> from schooltool.timetable.browser import TimetableView
        >>> from schooltool.timetable import Timetable
        >>> from schooltool.timetable import TimetableDay, TimetableActivity

        >>> from schooltool.course.section import Section as STSection
        >>> class Section(STSection):
        ...     implements(IOwnTimetables)

    Create some context:

        >>> s = Section()
        >>> ITimetables(s).timetables['term.schema'] = tt = Timetable(['day 1'])
        >>> tt['day 1'] = ttd = TimetableDay(['A'])
        >>> ttd.add('A', TimetableActivity('Something'))

        >>> request = TestRequest()
        >>> view = TimetableView(tt, request)

    rows() delegates the job to format_timetable_for_presentation:

        >>> view.rows()
        [[{'period': 'A', 'activity': 'Something'}]]

    """


def doctest_SectionTimetableSetupView():
    """Doctest for the SectionTimetableSetupView view

    We will need an application object

        >>> app = sbsetup.setUpSchoolToolSite()
        >>> from schooltool.timetable.schema import TimetableSchemaContainer
        >>> schemas = TimetableSchemaContainer()

        >>> from schooltool.timetable.interfaces import ITimetableSchemaContainer
        >>> ztapi.provideAdapter(Interface, ITimetableSchemaContainer,
        ...                      lambda x: schemas)

        >>> ztapi.provideAdapter(IOwnTimetables, ITimetables,
        ...                      TimetablesAdapter)
        >>> from zope.app.container.interfaces import INameChooser
        >>> from schooltool.timetable.interfaces import ITimetableDict
        >>> from schooltool.timetable import TimetableNameChooser
        >>> ztapi.provideAdapter(ITimetableDict, INameChooser,
        ...                      TimetableNameChooser)

        >>> from schooltool.course.section import Section as STSection
        >>> class Section(STSection):
        ...     implements(IOwnTimetables)

    We will need a section

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from schooltool.course.section import SectionContainer
        >>> from zope.location.location import locate
        >>> sections = SectionContainer()
        >>> locate(sections, app, 'sections')
        >>> sections["math"] = math = Section("Math")
        >>> ITimetables(math).timetables.keys()
        []

    We will also need a timetable schema, and a term.

        >>> schemas["default"] = createSchema(["Mon", "Tue"],
        ...                                   ["9:00", "10:00"],
        ...                                   ["9:00", "10:00"])


        >>> from schooltool.schoolyear.schoolyear import SchoolYear
        >>> schoolyears = ISchoolYearContainer(app)
        >>> schoolyears['2005'] = SchoolYear("2005",
        ...                                  datetime.date(2004, 2, 1),
        ...                                  datetime.date(2004, 12, 31))

        >>> from schooltool.term.term import Term
        >>> term = Term('2005 Spring',
        ...             datetime.date(2004, 2, 1),
        ...             datetime.date(2004, 6, 30))
        >>> ITermContainer(app)["2005-spring"] = term

        >>> from schooltool.course.interfaces import ISection
        >>> from schooltool.term.interfaces import ITerm
        >>> @adapter(ISection)
        ... @implementer(ITerm)
        ... def getTerm(section):
        ...     return term
        >>> provideAdapter(getTerm)

    We can now create the view to look at the Math timetable

        >>> from schooltool.timetable.browser import SectionTimetableSetupView
        >>> context = math
        >>> request = TestRequest()
        >>> view = SectionTimetableSetupView(context, request)

    We have some helper methods to simplify the form if there's only one
    option for terms or schemas:

        >>> view.app = app
        >>> view.singleSchema()
        True

    Another term and schema:

        >>> schemas["other"] = createSchema([], [])
        >>> ITermContainer(app)["2005-fall"] = Term('2005 Fall',
        ...                                         datetime.date(2004, 9, 1),
        ...                                         datetime.date(2004, 12, 31))

        >>> view.singleSchema()
        False

    We have getSchema from the Mixin class to get the schema from the request
    or choose a default.

        >>> view.getSchema() is schemas.getDefault()
        True
        >>> request.form['ttschema'] = 'other'
        >>> view.getSchema() is schemas["other"]
        True
        >>> request.form['ttschema'] = 'default'
        >>> view.getSchema() is schemas["default"]
        True

    If we cancel the form, we get redirected to the section

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/sections/math'

    If we save the form, we're redirected to the timetable view for the schema
    that we just saved:

        >>> request = TestRequest(form={'SAVE': 'Save'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/sections/math/timetables/1'

    An empty save request will create an empty timetable:

        >>> ITimetables(math).timetables['1']
        <Timetable: ...>
        >>> ITimetables(math).timetables['1']['Mon'].items()
        [('9:00', Set([])), ('10:00', Set([]))]
        >>> ITimetables(math).timetables['1']['Tue'].items()
        [('9:00', Set([])), ('10:00', Set([]))]

    Let's add some scheduled classes:

        >>> request = TestRequest(form={'ttschema': 'default',
        ...                             'term': '2005-fall',
        ...                             'Mon.9:00':'ON',
        ...                             'Tue.9:00':'ON',
        ...                             'SAVE': 'Save'})

        >>> view = SectionTimetableSetupView(context, request)

    First we submit the view::

        >>> result = view()
        >>> view.request.response.getStatus()
        302
        >>> view.request.response.getHeader('location')
        'http://127.0.0.1/sections/math/timetables/1'

    Now we have a schedule for our course:

        >>> ITimetables(math).timetables['1']['Mon']['9:00']
        Set([TimetableActivity('', ...
        >>> ITimetables(math).timetables['1']['Mon']['10:00']
        Set([])
        >>> ITimetables(math).timetables['1']['Tue']['9:00']
        Set([TimetableActivity('', ...
        >>> ITimetables(math).timetables['1']['Tue']['10:00']
        Set([])

    All the periods that were 'ON' are now checked:

        >>> view = SectionTimetableSetupView(context, TestRequest())
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

        >>> request = TestRequest(form={'ttschema': 'default',
        ...                             'term': '2005-fall',
        ...                             'Mon.9:00':'ON',
        ...                             'SAVE': 'Save'})
        >>> view = SectionTimetableSetupView(context, request)
        >>> result = view()

        >>> view = SectionTimetableSetupView(context, TestRequest())
        >>> print view()
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

    Tuesday's Activity is no longer there:

        >>> ITimetables(math).timetables['1']['Tue']['9:00']
        Set([])

    """


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
        'specialdays.txt', setUp=setUp, tearDown=tearDown,
        globs={'createSchema': createSchema,
               'createDayTemplate': createDayTemplate,
               'pprint': pprint},
        optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
