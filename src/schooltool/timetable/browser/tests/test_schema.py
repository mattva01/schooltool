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
Tests for schooltool timetable schema views.

$Id: test_timetable.py 4822 2005-08-19 01:35:11Z srichter $
"""

import unittest
from pprint import pprint

from zope.i18n import translate
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.container.interfaces import INameChooser
from zope.app.testing import ztapi

from schooltool.app.app import SimpleNameChooser
from schooltool.testing import setup as sbsetup
from schooltool.testing.util import NiceDiffsMixin
from schooltool.timetable import SequentialDaysTimetableModel
from schooltool.timetable import WeeklyTimetableModel
from schooltool.timetable.interfaces import ITimetableModelFactory
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.browser.tests.test_timetable import setUp, tearDown
from schooltool.timetable.browser.tests.test_timetable import createSchema
from schooltool.timetable.browser.tests.test_timetable import createDayTemplate


class TestAdvancedTimetableSchemaAdd(NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        setUp()
        self.app = sbsetup.setupSchoolToolSite()

        # Register the timetable models
        ztapi.provideUtility(ITimetableModelFactory,
                             SequentialDaysTimetableModel,
                             'SequentialDaysTimetableModel')
        ztapi.provideUtility(ITimetableModelFactory,
                             WeeklyTimetableModel,
                             'WeeklyTimetableModel')
        ztapi.provideAdapter(ITimetableSchemaContainer,
                             INameChooser,
                             SimpleNameChooser)

    def tearDown(self):
        tearDown()

    def createView(self, request=None):
        from schooltool.timetable.browser.schema import \
             AdvancedTimetableSchemaAdd
        context = self.app["ttschemas"]
        context['default'] = createSchema(['Day 1'], ['Period 1'])
        if request is None:
            request = TestRequest()
        view = AdvancedTimetableSchemaAdd(context, request)
        return view

    def test(self):
        view = self.createView()
        result = view()
        self.assert_('name="field.title" size="20" type="text" value="default"'
                     in result)

    def test_with_data(self):
        request = TestRequest(form={'day1': 'Monday',
                                    'field.title': 'something',
                                    'model': 'SequentialDaysTimetableModel',
                                    'time1.period': 'Period 1',
                                    'time1.day0': '9:00-9:45',
                                    })
        view = self.createView(request)
        result = view()
        self.assertEquals(view.ttschema,
                          createSchema(['Monday'], ['Period 1']))
        self.assert_('value="something"' in result, result)
        self.assertEquals(view.title_widget.error(), '')
        self.assertEquals(view.model_name, 'SequentialDaysTimetableModel')
        self.assertEquals(view.model_error, None)
        self.assertEquals(view.day_templates,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([(9, 0, 45)])})

    def test_creation(self):
        request = TestRequest(form={'day1': 'Monday',
                                    'field.title': 'some.thing',
                                    'model': 'SequentialDaysTimetableModel',
                                    'time1.period': 'Period 1',
                                    'time1.day0': '9:00-9:45',
                                    'CREATE': 'Create', })
        view = self.createView(request)
        result = view()
        self.assertEquals(view.model_error, None)
        self.assertEquals(request.response.getStatus(), 302)
        self.assertEquals(request.response.getHeader('location'),
                          'http://127.0.0.1/ttschemas')
        schema = view.context['something']
        self.assertEquals(schema, view.ttschema)
        self.assertEquals(schema.model.timetableDayIds, view.ttschema.keys())
        self.assertEquals(schema.model.dayTemplates, view.day_templates)

    def test_model_error(self):
        request = TestRequest(form={'model': 'xxx',
                                    'CREATE': 'Create'})
        view = self.createView(request)
        view()
        self.assertEquals(view.model_error, "Please select a value")

    def test_model_error_ignored_unless_this_is_the_final_submit(self):
        view = self.createView(TestRequest(form={'field.title': 'Schema',
                                                 'model': 'xxx'}))
        view()
        self.assertEquals(view.model_error, None)

    def test_buildDayTemplates_empty(self):
        view = self.createView()
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {None: createDayTemplate([])})

    def test_buildDayTemplates_simple(self):
        request = TestRequest(form={
            'time1.day0': '9:00',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'field.duration': '45'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([(9, 0, 45),
                                                 (10, 0, 45)]),
                           6: createDayTemplate([(10, 30, 40)])})
        self.assert_(not view.discarded_some_periods)

    def test_buildDayTemplates_copy_day(self):
        request = TestRequest(form={'time1.period': 'Period 1',
                                     'time1.day0': '9:00-9:45',
                                     'time1.day1': '13:00-13:45',
                                     'time2.period': 'Period 2',
                                     'time2.day0': '10:00-10:45',
                                     'time2.day6': '10:30-11:10',
                                     'COPY_PERIODS_1': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([(9, 0, 45),
                                                 (10, 0, 45)]),
                           1: createDayTemplate([(9, 0, 45),
                                                 (10, 0, 45)]),
                           6: createDayTemplate([(10, 30, 40)])})

    def test_buildDayTemplates_copy_empty_day(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00-9:45',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'COPY_PERIODS_6': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([(9, 0, 45),
                                                 (10, 0, 45)])})

    def test_buildDayTemplates_copy_empty_day_over_empty_day(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00-9:45',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'COPY_PERIODS_4': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([(9, 0, 45),
                                                 (10, 0, 45)]),
                           6: createDayTemplate([(10, 30, 40)])})

    def test_buildDayTemplates_copy_first_day_ignored(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': '9:00-9:45',
            'time2.period': 'Period 2',
            'time2.day0': '10:00-10:45',
            'time2.day6': '10:30-11:10',
            'COPY_PERIODS_0': 'C'})
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([(9, 0, 45),
                                                 (10, 0, 45)]),
                           6: createDayTemplate([(10, 30, 40)])})

    def test_buildDayTemplates_errors(self):
        request = TestRequest(form={
            'time1.period': 'Period 1',
            'time1.day0': 'foo',
            # When duration_widget.value is None, both endpoints are required
            'time1.day1': '9:00'
            })
        view = self.createView(request)
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {None: createDayTemplate([])})
        self.assert_(view.discarded_some_periods)

    def test_buildSchema_empty(self):
        view = self.createView()
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1'], ['Period 1']))

    def test_buildSchema_from_request(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': ' Tuesday ',
            'day1.period1': 'A',
            'day1.period2': ' B ',
            'day2.period1': 'C',
            'day2.period2': ''})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B'], ['C']))

    def test_buildSchema_empty_day(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': 'Tuesday',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': '',
            'day2.period2': ''})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B'], ['Period 1']))

    def test_buildSchema_repeated_day_name(self):
        request = TestRequest(form={
            'day1': 'D',
            'day2': 'D',
            'day3': 'D',
            'day1.period1': 'A',
            'day2.period1': 'B',
            'day3.period1': 'C'})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['D', 'D (2)', 'D (3)'],
                                               ['A'], ['B'], ['C']))

    def test_buildSchema_repeated_period_nam(self):
        request = TestRequest(form={
            'day1': 'D',
            'day1.period1': 'A',
            'day1.period2': 'A'})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['D'], ['A', 'A (2)']))

    def test_buildSchema_add_day(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'ADD_DAY': "Add"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Day 2'],
                                               ['Period 1'], ['Period 1']))

    def test_buildSchema_add_period(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': 'Tuesday',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': '',
            'ADD_PERIOD': "Add"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B', 'Period 3'], ['C']))

    def test_buildSchema_add_period_not_first_day(self):
        request = TestRequest(form={
            'day1': 'Monday',
            'day2': 'Tuesday',
            'day1.period1': 'A',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'ADD_PERIOD': "Add"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A'], ['C', 'D', 'Period 3']))

    def test_buildSchema_delete_day(self):
        request = TestRequest(form={
            'day1': 'Day 1',
            'day2': 'Day 1',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'DELETE_DAY_1': "Delete"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1'], ['C', 'D']))

    def test_buildSchema_copy_day(self):
        request = TestRequest(form={
            'day1': 'Day 1',
            'day2': 'Day 2',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'COPY_DAY_1': "Copy"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['A', 'B']))

    def test_buildSchema_copy_first_day_ignored(self):
        request = TestRequest(form={
            'day1': 'Day 1',
            'day2': 'Day 2',
            'day1.period1': 'A',
            'day1.period2': 'B',
            'day2.period1': 'C',
            'day2.period2': 'D',
            'COPY_DAY_0': "Copy"})
        view = self.createView(request)
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['C', 'D']))

    def test_all_periods(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        self.assertEquals(view.all_periods(), ['A', 'C', 'B', 'D', 'F'])

    def test_slot_times(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F', 'G'])
        view.day_templates = {}
        result = view.slot_times()
        # The length of the result is equal to the longest day in the tt.
        self.assertEquals(len(result), 3)
        for row in result:
            self.assertEquals(row, 7 * [None])

    def test_slot_times_with_data(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F', 'G'])
        view.day_templates = {0: createDayTemplate([(9, 0, 45),
                                                    (10, 30, 40),
                                                    (11, 22, 33)]),
                              6: createDayTemplate([(8, 55, 45),
                                                    (0, 0, 24*60)])}
        times = view.slot_times()
        self.assertEquals(len(times), 3)
        self.assertEquals(times[0], ['09:00-09:45', None, None, None,
                                     None, None, '00:00-24:00'])
        self.assertEquals(times[1], ['10:30-11:10', None, None, None,
                                     None, None, '08:55-09:40'])
        self.assertEquals(times[2], ['11:22-11:55'] + [None] * 6)


def doctest_TimetableSchemaView():
    """Test for TimetableView.

        >>> from schooltool.timetable.browser.schema import TimetableSchemaView
        >>> from schooltool.timetable.schema import TimetableSchema
        >>> from schooltool.timetable.schema import TimetableSchemaDay
        >>> from schooltool.timetable import TimetableActivity

    Create some context:

        >>> tts = TimetableSchema(['day 1'])
        >>> tts.__name__ = 'some-schema'
        >>> tts['day 1'] = ttd = TimetableSchemaDay(['A'])

        >>> request = TestRequest()
        >>> view = TimetableSchemaView(tts, request)

    title() returns the view's title:

        >>> translate(view.title())
        u'Timetable schema some-schema'

    ``rows()`` delegates the job to ``format_timetable_for_presentation``:

        >>> view.rows()
        [[{'period': 'A', 'activity': ''}]]

    """


def doctest_SimpleTimetableSchemaAdd():
    r"""Doctest for the SimpleTimetableSchemaAdd view

        >>> from schooltool.timetable import WeeklyTimetableModel
        >>> from schooltool.timetable.interfaces import ITimetableModelFactory
        >>> ztapi.provideUtility(ITimetableModelFactory,
        ...                      WeeklyTimetableModel,
        ...                      'WeeklyTimetableModel')
        >>> from schooltool.timetable.interfaces import \
        ...                           ITimetableSchemaContainer
        >>> from schooltool.app.app import SimpleNameChooser
        >>> from zope.app.container.interfaces import INameChooser
        >>> ztapi.provideAdapter(ITimetableSchemaContainer,
        ...                      INameChooser,
        ...                      SimpleNameChooser)

    Suppose we have a SchoolTool instance, and create a view for its
    timetable schemas container:

        >>> app = sbsetup.setupSchoolToolSite()

        >>> request = TestRequest()
        >>> from schooltool.timetable.browser.schema import \
        ...      SimpleTimetableSchemaAdd
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

    Let's render it.  There is a widget for title there:

        >>> print view()
        <BLANKLINE>
        ...
                  <div class="field"><input class="textType"
                             id="field.title"
                             name="field.title" size="20" type="text"
                             value="default"  /></div>
        ...
          <tr>
            <th>
              <div><input class="textType" id="field.period_name_1"
                          name="field.period_name_1" size="20" type="text"
                          value=""  /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_start_1"
                          name="field.period_start_1" size="20"
                          type="text" value="" /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_finish_1"
                          name="field.period_finish_1" size="20"
                          type="text" value="" /></div>
            </th>
          </tr>
        ...

    getPeriods returns None, as the form is not yet filled:

        >>> view.getPeriods()
        []

    Now, let's create a simple case with all the fields filled:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': 'Period 2',
        ...                             'field.period_start_2': '10:00',
        ...                             'field.period_finish_2': '10:45',
        ...                             'field.period_name_3': '',
        ...                             'field.period_name_4': '',
        ...                             'CREATE': 'Go'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

    getPeriods should extract a list of periods:

        >>> pprint(view.getPeriods())
        [(u'Period 1',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700)),
         (u'Period 2',
          datetime.time(10, 0),
          datetime.timedelta(0, 2700))]

    If we call the view, a new timetable schema is created:

        >>> result = view()
        >>> list(view.context.keys())
        [u'default']
        >>> schema = view.context['default']
        >>> print " ".join(schema.day_ids)
        Monday Tuesday Wednesday Thursday Friday
        >>> print ", ".join(schema['Monday'].periods)
        Period 1, Period 2

    All days are the same

        >>> for day_id, day in schema.items():
        ...     assert day == schema['Monday']

    The schema uses the weekly timetable model

        >>> print schema.model.__class__.__name__
        WeeklyTimetableModel
        >>> print " ".join(schema.model.timetableDayIds)
        Monday Tuesday Wednesday Thursday Friday
        >>> for period in schema.model.dayTemplates[None]:
        ...     print period.tstart, period.duration
        09:00:00 0:45:00
        10:00:00 0:45:00

    We should get redirected to the ttschemas index:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas'

    If period names are not provided, use start times:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': '',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': '',
        ...                             'field.period_start_2': '10:00',
        ...                             'field.period_finish_2': '10:45',
        ...                             'CREATE': 'Go'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

        >>> pprint(view.getPeriods())
        [(u'9:00',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700)),
         (u'10:00',
          datetime.time(10, 0),
          datetime.timedelta(0, 2700))]

    If a cancel button is pressed, nothing is done and the user is
    redirected to ttschemas index:

        >>> request = TestRequest(form={'field.title': 'default2',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': 'Period 2',
        ...                             'field.period_start_2': '10:00',
        ...                             'field.period_finish_2': '10:45',
        ...                             'field.period_name_3': '',
        ...                             'field.period_name_4': '',
        ...                             'CANCEL': 'Cancel'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> result = view()
        >>> list(view.context.keys())
        [u'default']

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('location')
        'http://127.0.0.1/ttschemas'

    If there's a period skipped in a form, consequent periods are not included:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_3': 'Period 2',
        ...                             'field.period_start_3': '10:00',
        ...                             'field.period_finish_3': '10:45',
        ...                             'field.period_name_4': '',
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> view.getPeriods()
        [(u'Period 1',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700)),
         (u'Period 2',
          datetime.time(10, 0),
          datetime.timedelta(0, 2700))]

    If a period does not have a start time or end time specified, it
    is skipped:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': 'Period 2',
        ...                             'field.period_start_2': '',
        ...                             'field.period_finish_2': '10:45',
        ...                             'field.period_name_3': 'Period 3',
        ...                             'field.period_start_3': '11:00',
        ...                             'field.period_finish_3': '',
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> view.getPeriods()
        [(u'Period 1',
          datetime.time(9, 0),
          datetime.timedelta(0, 2700))]

    Incorrect start and end times are handled gracefully:

        >>> request = TestRequest(form={'field.title': 'default',
        ...                             'field.period_name_1': 'Period 1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '9:45',
        ...                             'field.period_name_2': '',
        ...                             'field.period_start_2': '10h',
        ...                             'field.period_finish_2': '',
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)

    getPeriods fails:

        >>> view.getPeriods()
        [(u'Period 1', datetime.time(9, 0), datetime.timedelta(0, 2700))]

    The widgets responsible get an error set on them:

        >>> print view()
        <BLANKLINE>
        ...
            <div class="error">Please use HH:MM format for period start
                               and end times</div>
        ...

        >>> request.response.getStatus() != 302
        True


   One can provide the same title more than once (thought it is not
   advised to do so):

        >>> request = TestRequest(form={
        ...                             'field.title': 'already',
        ...                             'field.period_name_1': 'p1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '10:00',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> from schooltool.timetable.schema import TimetableSchema
        >>> app['ttschemas']['already'] = TimetableSchema([])
        >>> result = view()
        >>> request.response.getStatus() == 302
        True
        >>> 'already-2' in app['ttschemas']
        True

    """


def doctest_SimpleTimetableSchemaAdd_errors():
    r"""Doctest for the SimpleTimetableSchemaAdd view

        >>> from schooltool.timetable import WeeklyTimetableModel
        >>> from schooltool.timetable.interfaces import ITimetableModelFactory
        >>> ztapi.provideUtility(ITimetableModelFactory,
        ...                      WeeklyTimetableModel,
        ...                      'WeeklyTimetableModel')

    Suppose we have a SchoolTool instance, and create a view for its
    timetable schemas container:

        >>> app = sbsetup.setupSchoolToolSite()

    No name specified:

        >>> request = TestRequest(form={
        ...                             'field.title': '',
        ...                             'field.period_name_1': 'p1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '10:00',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> from schooltool.timetable.browser.schema import \
        ...      SimpleTimetableSchemaAdd
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> print view()
        <BLANKLINE>
        ...
                 <div class="label">
                    <label for="field.title" title="">Title</label>
                  </div>
                  <span class="error">Required input is missing.</span>
                  <div class="field"><input class="textType" id="field.title"
                                            name="field.title" size="20"
                                            type="text" value=""  /></div>
        ...
          <tr>
            <th>
              <div><input class="textType" id="field.period_name_1"
                          name="field.period_name_1" size="20" type="text"
                          value="p1"  /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_start_1"
                          name="field.period_start_1" size="20"
                          type="text" value="9:00" /></div>
            </th>
            <th>
              <div><input class="textType" id="field.period_finish_1"
                          name="field.period_finish_1" size="20"
                          type="text" value="10:00" /></div>
            </th>
          </tr>
        ...

        >>> request.response.getStatus() != 302
        True

    No periods:

        >>> request = TestRequest(form={
        ...                             'field.title': 'empty',
        ...                             'field.period_name_1': '',
        ...                             'field.period_start_1': '',
        ...                             'field.period_finish_1': '',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> view = SimpleTimetableSchemaAdd(app['ttschemas'], request)
        >>> print view()
        <BLANKLINE>
        ...
            <div class="error">You must specify at least one period.</div>
        ...
                  <div class="label">
                    <label for="field.title" title="">Title</label>
                  </div>
                  <div class="field"><input class="textType" id="field.title"
                                            name="field.title" size="20"
                                            type="text" value="empty"
                                            /></div>
        ...

        >>> request.response.getStatus() != 302
        True

    """


def doctest_TimetableSchemaContainerView():
    r"""A test for TimetableSchemaContainer view

    We will need an application:

        >>> app = sbsetup.createSchoolToolApplication()

    Some timetable schemas:

        >>> from schooltool.timetable.schema import TimetableSchema
        >>> app["ttschemas"]["schema1"] = TimetableSchema([])
        >>> app["ttschemas"]["schema2"] = TimetableSchema([])

    Let's create our view:

        >>> from schooltool.timetable.browser.schema import \
        ...      TimetableSchemaContainerView
        >>> from zope.publisher.browser import TestRequest
        >>> view = TimetableSchemaContainerView(app["ttschemas"], TestRequest())

    The default ttschema id should be "schema1":

        >>> app["ttschemas"].default_id
        'schema1'

    If the view is submited without any data - the default ttschema
    should not change:

        >>> view.update()
        ''
        >>> app["ttschemas"].default_id
        'schema1'

    We can change the default schema:

        >>> view.request = TestRequest(form={
        ...                                  'ttschema': 'schema2',
        ...                                  'UPDATE_SUBMIT': 'Change'
        ...                                 })
        >>> view.update()
        ''
        >>> app["ttschemas"].default_id
        'schema2'

    We can set the default_id to none:

        >>> view.request = TestRequest(form={
        ...                                  'ttschema': '',
        ...                                  'UPDATE_SUBMIT': 'Change'
        ...                                 })
        >>> view.update()
        ''
        >>> app["ttschemas"].default_id is None
        True

    """


def test_suite():
    suite = unittest.TestSuite()
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.REPORT_ONLY_FIRST_FAILURE |
                   doctest.NORMALIZE_WHITESPACE)
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    suite.addTest(unittest.makeSuite(TestAdvancedTimetableSchemaAdd))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
