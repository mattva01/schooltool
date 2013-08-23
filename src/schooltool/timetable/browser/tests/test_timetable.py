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
Tests for schooltool timetable schema views.
"""
import datetime
import unittest
import doctest
from pprint import pprint

from zope.component import provideAdapter, provideHandler, provideUtility
from zope.component import adapts
from zope.location.location import locate
from zope.interface import Interface, implements
from zope.interface import directlyProvides
from zope.interface import directlyProvidedBy
from zope.i18n import translate
from zope.publisher.browser import TestRequest
from zope.publisher.browser import BrowserView
from zope.traversing.interfaces import ITraversable
from zope.traversing.interfaces import IContainmentRoot
from zope.app.testing import setup
from zope.traversing import namespace
from zope.schema.vocabulary import getVocabularyRegistry

from schooltool.app.browser import testing
from schooltool.app.app import SimpleNameChooser
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.testing import setup as sbsetup
from schooltool.testing.util import normalize_xml
from schooltool.testing.util import XMLCompareMixin
from schooltool.testing.util import NiceDiffsMixin
from schooltool.timetable.app import activityVocabularyFactory
from schooltool.timetable.daytemplates import DayTemplateSchedule
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period

try:
    from schooltool.timetable.schema import TimetableSchemaContainer
    from schooltool.timetable.model import WeeklyTimetableModel
    from schooltool.timetable.model import SequentialDaysTimetableModel
    from schooltool.timetable.interfaces import ITimetableModelFactory
    from schooltool.timetable.interfaces import ITimetableSchemaContainer
    from schooltool.timetable.browser.tests import test_timetable
    from schooltool.timetable.browser.tests.test_timetable import createDayTemplate
    from schooltool.timetable.browser.timetable import DayTemplatesTableSnippet
    from schooltool.timetable.browser.timetable import TimetableView
except:
    pass # XXX: tests not refactored yet


def setUp(test=None):
    testing.setUp(test)
    sbsetup.setUpApplicationPreferences()

    vr = getVocabularyRegistry()
    vr.register('schooltool.timetable.activityvocbulary',
                activityVocabularyFactory())

tearDown = testing.tearDown


def createSchema(*args):
    tts = test_timetable.createSchema(*args)
    tts.timezone = 'Asia/Tokyo'
    return tts


class TestAdvancedTimetableSchemaAdd(NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        setUp()
        self.app = sbsetup.setUpSchoolToolSite()
        self.ttschemas = TimetableSchemaContainer()
        locate(self.ttschemas, self.app, 'ttschemas')
        IApplicationPreferences(self.app).timezone = 'Asia/Tokyo'

        # Register the timetable models
        provideUtility(SequentialDaysTimetableModel,
                       ITimetableModelFactory,
                       'SequentialDaysTimetableModel')
        provideUtility(WeeklyTimetableModel,
                       ITimetableModelFactory,
                       'WeeklyTimetableModel')
        provideAdapter(SimpleNameChooser, (ITimetableSchemaContainer,))
        provideAdapter(lambda x: self.ttschemas, (Interface,), ITimetableSchemaContainer)

    def tearDown(self):
        tearDown()

    def createView(self, request=None):
        from schooltool.timetable.browser.timetable import \
             AdvancedTimetableSchemaAdd
        context = self.ttschemas
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
        self.assertEquals(schema.timezone, 'Asia/Tokyo')

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


def doctest_DayTemplatesTableSnippet():
    """Test for DayTemplatesTableSnippet.

    The purpose of this snippet is to iterate day templates and render
    them as a table.

        >>> schedule = DayTemplateSchedule()
        >>> schedule.initTemplates()

        >>> class Lesson(object):
        ...     def __init__(self, title, description):
        ...         self.title = title
        ...         self.description = description

        >>> templates = schedule.templates

    Let's add a few days.

        >>> def add_day(templates, title, lessons):
        ...     d = len(templates)
        ...     template = templates[u'%d' % d] = DayTemplate(title)
        ...     for n, lesson in enumerate(lessons):
        ...        template[u'%d' % n] = Lesson(u'lesson %d' % n, lesson)

        >>> lessons = ['math', 'english', 'history']
        >>> add_day(templates, u'Day 1', lessons)
        >>> add_day(templates, u'Day 2', lessons[1:])

    And create the view.

        >>> view = DayTemplatesTableSnippet(schedule, TestRequest())

        >>> [t.title for t in view.templates]
        [u'Day 1', u'Day 2']

    The view knows nothing about items in day templates, so we'll
    need to pass formatters that, given the item, return tuples
    of (title, value) for presentation.

        >>> formatter = lambda item: (item.__name__, item.title)

        >>> pprint(view.extractDays(formatter))
        [(u'Day 1', [(u'0', u'lesson 0'),
                     (u'1', u'lesson 1'),
                     (u'2', u'lesson 2')]),
         (u'Day 2', [(u'0', u'lesson 0'),
                     (u'1', u'lesson 1')])]

    Let's write a formatter better suited to represent our Lesson.

        >>> lesson_formatter = lambda t: (t.title, t.description)

        >>> days = view.extractDays(lesson_formatter)
        >>> pprint(days)
        [(u'Day 1',
          [(u'lesson 0', 'math'),
           (u'lesson 1', 'english'),
           (u'lesson 2', 'history')]),
         (u'Day 2',
          [(u'lesson 0', 'english'),
           (u'lesson 1', 'history')])]

    makeTable massages data into dict, better suited for page templates.

        >>> pprint(view.makeTable(days))
        {'col_width': '50%',
         'header': [u'Day 1', u'Day 2'],
         'rows': [({'title': u'lesson 0', 'value': 'math'},
                   {'title': u'lesson 0', 'value': 'english'}),
                  ({'title': u'lesson 1', 'value': 'english'},
                   {'title': u'lesson 1', 'value': 'history'}),
                  ({'title': u'lesson 2', 'value': 'history'},
                   {})],
         'td_width': '45%',
         'th_width': '5%'}

        >>> print normalize_xml(view(item_formatter=lesson_formatter))
        <table class="timetable">
          <tr>
            <th class="day" colspan="2" width="50%">
              Day 1
            </th>
            <th class="day" colspan="2" width="50%">
              Day 2
            </th>
          </tr>
          <tr>
            <th class="period" width="5%">
              lesson 0
            </th>
            <td class="activity" width="45%">
              math
            </td>
            <th class="period" width="5%">
              lesson 0
            </th>
            <td class="activity" width="45%">
              english
            </td>
          </tr>
          <tr>
            <th class="period" width="5%">
              lesson 1
            </th>
            <td class="activity" width="45%">
              english
            </td>
            <th class="period" width="5%">
              lesson 1
            </th>
            <td class="activity" width="45%">
              history
            </td>
          </tr>
          <tr>
            <th class="period" width="5%">
              lesson 2
            </th>
            <td class="activity" width="45%">
              history
            </td>
            <td class="activity" colspan="2" width="50%"/>
          </tr>
        </table>

    """


def doctest_TimetableView():
    """Test for TimetableView.

    This view queries snippets to render the period and time slot tables.

    The view is responsible for final formatting of period/time slot entries.
    To demonstrate this, we need stub day templates with samples of actual
    objects.

        >>> class IStubDayTemplates(Interface):
        ...     pass

        >>> class StubDayTemplates(object):
        ...     implements(IStubDayTemplates)
        ...     def __init__(self, sample=None):
        ...         self.sample = sample

        >>> period = Period(title='One', activity_type='lesson')
        >>> time_slot = TimeSlot(
        ...     datetime.time(12, 0),
        ...     datetime.timedelta(0, 2700),
        ...     activity_type='lunch')

        >>> class TimetableStub(object):
        ...     pass

        >>> timetable = TimetableStub()
        >>> timetable.periods = StubDayTemplates(sample=period)
        >>> timetable.time_slots = StubDayTemplates(sample=time_slot)

   Let's create our view.

        >>> view = TimetableView(timetable, TestRequest())

  The snippet is not registered yet, so not much action here.

        >>> view.periods_snippet()
        ''

        >>> view.time_snippet()
        ''

   Let's register a snippet that uses a fromatter from the view to render
   the sample object.

        >>> class TableSnippet(BrowserView):
        ...     adapts(IStubDayTemplates, TestRequest)
        ...     def __call__(self, item_formatter=None):
        ...         return item_formatter(self.context.sample)

        >>> from zope.publisher.interfaces.browser import IBrowserView

        >>> provideAdapter(TableSnippet,
        ...                provides=IBrowserView,
        ...                name="day_templates_table_snippet")

        >>> view.periods_snippet()
        ('One', u'Lesson')

        >>> view.time_snippet()
        ('12:00-12:45', u'Lunch')


    """


def doctest_SimpleTimetableSchemaAdd():
    r"""Doctest for the SimpleTimetableSchemaAdd view

        >>> provideUtility(WeeklyTimetableModel,
        ...                ITimetableModelFactory,
        ...                'WeeklyTimetableModel')
        >>> provideAdapter(SimpleNameChooser, (ITimetableSchemaContainer,))
        >>> schemas = TimetableSchemaContainer()
        >>> provideAdapter(lambda x: schemas,
        ...                (Interface,), ITimetableSchemaContainer)

    Suppose we have a SchoolTool instance, and create a view for its
    timetable schemas container:

        >>> app = sbsetup.setUpSchoolToolSite()
        >>> IApplicationPreferences(app).timezone = 'Asia/Tokyo'

        >>> request = TestRequest()
        >>> from schooltool.timetable.browser.timetable import \
        ...      SimpleTimetableSchemaAdd
        >>> view = SimpleTimetableSchemaAdd(schemas, request)

        >>> locate(schemas, app, 'ttschemas')

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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)

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
        >>> schema.timezone
        'Asia/Tokyo'

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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)

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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)
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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)
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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)
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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)

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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)
        >>> from schooltool.timetable.schema import TimetableSchema
        >>> schemas['already'] = TimetableSchema([])
        >>> result = view()
        >>> request.response.getStatus() == 302
        True
        >>> 'already-2' in schemas
        True

    """


def doctest_SimpleTimetableSchemaAdd_errors():
    r"""Doctest for the SimpleTimetableSchemaAdd view

        >>> from schooltool.timetable.model import WeeklyTimetableModel
        >>> from schooltool.timetable.interfaces import ITimetableModelFactory
        >>> provideUtility(WeeklyTimetableModel,
        ...                ITimetableModelFactory,
        ...                'WeeklyTimetableModel')

    Suppose we have a SchoolTool instance, and create a view for its
    timetable schemas container:

        >>> from schooltool.timetable.schema import TimetableSchemaContainer
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> schemas = TimetableSchemaContainer()

    No name specified:

        >>> request = TestRequest(form={
        ...                             'field.title': '',
        ...                             'field.period_name_1': 'p1',
        ...                             'field.period_start_1': '9:00',
        ...                             'field.period_finish_1': '10:00',
        ...                             'CREATE': 'Create'
        ...                            })
        >>> from schooltool.timetable.browser.timetable import \
        ...      SimpleTimetableSchemaAdd
        >>> view = SimpleTimetableSchemaAdd(schemas, request)
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
        >>> view = SimpleTimetableSchemaAdd(schemas, request)
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
        >>> schemas = TimetableSchemaContainer()
        >>> provideAdapter(lambda x: schemas,
        ...                adapts=[Interface],
        ...                provides=ITimetableSchemaContainer)

    Some timetable schemas:

        >>> from schooltool.timetable.schema import TimetableSchema
        >>> schemas["schema1"] = TimetableSchema([])
        >>> schemas["schema2"] = TimetableSchema([])

    Let's create our view:

        >>> from schooltool.timetable.browser.timetable import \
        ...      TimetableSchemaContainerView
        >>> from zope.publisher.browser import TestRequest
        >>> view = TimetableSchemaContainerView(schemas,
        ...                                     TestRequest())

    The default ttschema id should be "schema1":

        >>> schemas.default_id
        'schema1'

    If the view is submited without any data - the default ttschema
    should not change:

        >>> view.update()
        ''
        >>> schemas.default_id
        'schema1'

    We can change the default schema:

        >>> view.request = TestRequest(form={
        ...                                  'ttschema': 'schema2',
        ...                                  'UPDATE_SUBMIT': 'Change'
        ...                                 })
        >>> view.update()
        ''
        >>> schemas.default_id
        'schema2'

    We can set the default_id to none:

        >>> view.request = TestRequest(form={
        ...                                  'ttschema': '',
        ...                                  'UPDATE_SUBMIT': 'Change'
        ...                                 })
        >>> view.update()
        ''
        >>> schemas.default_id is None
        True

    """


def doctest_TimetableDependentDeleteView():
    r"""Tests for TimetableDependentDeleteView.

    This view is used to delete school timetables and terms, and
    recursively deletes all timetables that use the object to be
    deleted.

    First, let's set up:

        >>> from schooltool.timetable import TimetablesAdapter
        >>> from schooltool.timetable.interfaces import ITimetables
        >>> setup.placefulSetUp()
        >>> provideAdapter(TimetablesAdapter)
        >>> setup.setUpAnnotations()
        >>> from schooltool.timetable.schema import clearTimetablesOnDeletion
        >>> from schooltool.timetable.interfaces import ITimetableSchema
        >>> from zope.lifecycleevent.interfaces import IObjectRemovedEvent
        >>> provideHandler(clearTimetablesOnDeletion,
        ...                (ITimetableSchema, IObjectRemovedEvent))

    Now, let's create a couple of timetables to operate on:

        >>> from schooltool.timetable.schema import TimetableSchema
        >>> from schooltool.timetable.schema import TimetableSchemaDay
        >>> from schooltool.timetable.interfaces import IOwnTimetables
        >>> app = sbsetup.setUpSchoolToolSite()
        >>> schemas = TimetableSchemaContainer()
        >>> locate(schemas, app, "ttschemas")
        >>> directlyProvides(app, directlyProvidedBy(app) + IOwnTimetables)

        >>> days = ('A', 'B')
        >>> periods1 = ('Green', 'Blue')
        >>> tts = TimetableSchema(days)
        >>> tts["A"] = TimetableSchemaDay(periods1)
        >>> tts["B"] = TimetableSchemaDay(periods1)

        >>> days = ('C', 'D')
        >>> tts2 = TimetableSchema(days)
        >>> tts2["C"] = TimetableSchemaDay(periods1)
        >>> tts2["D"] = TimetableSchemaDay(periods1)

        >>> schemas['simple'] = tts
        >>> schemas['other'] = tts2

    Let's create a couple of timetables on the application:

        >>> ITimetables(app).timetables['2006.simple'] = tts.createTimetable(None)
        >>> ITimetables(app).timetables['2006.other'] = tts2.createTimetable(None)

    Now, we can run the view:

        >>> from schooltool.timetable.browser.timetable \
        ...     import TimetableDependentDeleteView
        >>> request = TestRequest(form={'delete.simple': 'on',
        ...                             'CONFIRM': 'Confirm'})
        >>> view = TimetableDependentDeleteView(schemas, request)
        >>> view.update()

    The timetable schema is deleted:

        >>> list(schemas.keys())
        [u'other']

    Also, the dependent timetables have been deleted:

        >>> ITimetables(app).timetables.keys()
        ['2006.other']

    The user is redirected to the school timetable index view:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/ttschemas'

    The user can also cancel the deletion:

        >>> from schooltool.timetable.browser.timetable \
        ...     import TimetableDependentDeleteView
        >>> request = TestRequest(form={'delete.other': 'on',
        ...                             'CANCEL': 'Cancel'})
        >>> view = TimetableDependentDeleteView(schemas, request)
        >>> view.update()

    In that case, the data is unchanged:

        >>> list(schemas.keys())
        [u'other']
        >>> ITimetables(app).timetables.keys()
        ['2006.other']

    The user is also redirected to the school timetable index view:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/ttschemas'
    """


class TimetableSchemaMixin(object):

    schema_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <title>Title</title>
          <timezone name="Europe/Vilnius"/>
          <model factory="SequentialDaysTimetableModel">
            <daytemplate>
              <used when="default" />
              <period id="A" tstart="9:00" duration="60" />
              <period id="C" tstart="9:00" duration="60" />
              <period id="B" tstart="10:00" duration="60" />
              <period id="D" tstart="10:00" duration="60" />
            </daytemplate>
            <daytemplate>
              <used when="Friday Thursday" />
              <period id="A" tstart="8:00" duration="60" />
              <period id="C" tstart="8:00" duration="60" />
              <period id="B" tstart="11:00" duration="60" />
              <period id="D" tstart="11:00" duration="60" />
            </daytemplate>
            <daytemplate>
              <used when="2005-07-07" />
              <period id="A" tstart="8:00" duration="30" />
              <period id="B" tstart="8:30" duration="30" />
              <period id="C" tstart="9:00" duration="30" />
              <period id="D" tstart="9:30" duration="30" />
            </daytemplate>
            <day when="2005-07-08" id="Day 2" />
            <day when="2005-07-09" id="Day 1" />
          </model>
          <day id="Day 1">
            <period id="A" homeroom="">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    schema_without_title_xml = schema_xml.replace("<title>Title</title>", "")

    def setUp(self):
        from schooltool.timetable.model import SequentialDaysTimetableModel
        from schooltool.timetable.model import SequentialDayIdBasedTimetableModel
        from schooltool.timetable.interfaces import ITimetableModelFactory

        self.app = sbsetup.createSchoolToolApplication()
        self.schemaContainer = TimetableSchemaContainer()

        setup.placelessSetUp()
        setup.setUpTraversal()

        provideUtility(SequentialDaysTimetableModel,
                       ITimetableModelFactory,
                       "SequentialDaysTimetableModel")

        provideUtility(SequentialDayIdBasedTimetableModel,
                       ITimetableModelFactory,
                       "SequentialDayIdBasedTimetableModel")

        provideAdapter(namespace.view, (None,), ITraversable, 'view')

        directlyProvides(self.schemaContainer, IContainmentRoot)

    def tearDown(self):
        setup.placelessTearDown()

    def createEmptySchema(self):
        from schooltool.timetable.schema import TimetableSchemaDay
        from schooltool.timetable.schema import TimetableSchema
        schema = TimetableSchema(['Day 1', 'Day 2'])
        schema['Day 1'] = TimetableSchemaDay(['A', 'B'], ['A'])
        schema['Day 2'] = TimetableSchemaDay(['C', 'D'])
        schema.title = "A Schema"
        return schema

    def createExtendedSchema(self):
        from schooltool.timetable.model import SequentialDaysTimetableModel
        from schooltool.timetable import SchooldaySlot, SchooldayTemplate
        from datetime import time, timedelta, date

        tt = self.createEmptySchema()

        tt.timezone = 'Europe/Vilnius'

        hour = timedelta(minutes=60)
        half = timedelta(minutes=30)

        day_template1 = SchooldayTemplate()
        day_template1.add(SchooldaySlot(time(9, 0), hour))
        day_template1.add(SchooldaySlot(time(10, 0), hour))
        day_template1.add(SchooldaySlot(time(9, 0), hour))
        day_template1.add(SchooldaySlot(time(10, 0), hour))

        day_template2 = SchooldayTemplate()
        day_template2.add(SchooldaySlot(time(8, 0), hour))
        day_template2.add(SchooldaySlot(time(11, 0), hour))
        day_template2.add(SchooldaySlot(time(8, 0), hour))
        day_template2.add(SchooldaySlot(time(11, 0), hour))

        tm = SequentialDaysTimetableModel(['Day 1', 'Day 2'],
                                          {None: day_template1,
                                           3: day_template2,
                                           4: day_template2})
        tt.model = tm

        short_template = [
            ('A', SchooldaySlot(time(8, 0), half)),
            ('B', SchooldaySlot(time(8, 30), half)),
            ('C', SchooldaySlot(time(9, 0), half)),
            ('D', SchooldaySlot(time(9, 30), half))]
        tt.model.exceptionDays[date(2005, 7, 7)] = short_template
        tt.model.exceptionDayIds[date(2005, 7, 8)] = 'Day 2'
        tt.model.exceptionDayIds[date(2005, 7, 9)] = 'Day 1'
        return tt


class TestTimetableSchemaXMLView(TimetableSchemaMixin, XMLCompareMixin,
                              unittest.TestCase):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <title>A Schema</title>
          <timezone name="Europe/Vilnius"/>
          <model factory="SequentialDaysTimetableModel">
            <daytemplate>
              <used when="2005-07-07"/>
              <period duration="30" id="A" tstart="08:00"/>
              <period duration="30" id="B" tstart="08:30"/>
              <period duration="30" id="C" tstart="09:00"/>
              <period duration="30" id="D" tstart="09:30"/>
            </daytemplate>
            <daytemplate>
              <used when="Friday Thursday"/>
              <period duration="60" tstart="08:00"/>
              <period duration="60" tstart="11:00"/>
            </daytemplate>
            <daytemplate>
              <used when="default"/>
              <period duration="60" tstart="09:00"/>
              <period duration="60" tstart="10:00"/>
            </daytemplate>
            <day when="2005-07-08" id="Day 2" />
            <day when="2005-07-09" id="Day 1" />
          </model>
          <day id="Day 1">
            <period id="A" homeroom="">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    def test_get(self):
        from schooltool.timetable.browser.timetable import TimetableSchemaXMLView
        request = TestRequest()
        view = TimetableSchemaXMLView(self.createExtendedSchema(), request)

        result = view()
        self.assertEquals(request.response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, self.empty_xml)


class DayIdBasedModelMixin:

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <title>Title</title>
          <timezone name="UTC"/>
          <model factory="SequentialDayIdBasedTimetableModel">
            <daytemplate>
              <used when="Day 1"/>
              <period duration="60" tstart="08:00"/>
              <period duration="60" tstart="11:00"/>
            </daytemplate>
            <daytemplate>
              <used when="Day 2"/>
              <period duration="60" tstart="09:00"/>
              <period duration="60" tstart="10:00"/>
            </daytemplate>
            <day when="2005-07-08" id="Day 2" />
            <day when="2005-07-09" id="Day 1" />
          </model>
          <day id="Day 1">
            <period id="A" homeroom="">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    def createExtendedSchema(self):
        from schooltool.timetable.schema import TimetableSchemaDay
        from schooltool.timetable.schema import TimetableSchema
        from schooltool.timetable.model import SequentialDayIdBasedTimetableModel
        from schooltool.timetable import SchooldaySlot, SchooldayTemplate
        from datetime import time, timedelta, date

        tt = TimetableSchema(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableSchemaDay(['A', 'B'], ['A'])
        tt['Day 2'] = TimetableSchemaDay(['C', 'D'])
        tt.title = "Title"

        hour = timedelta(minutes=60)
        half = timedelta(minutes=30)

        day_template1 = SchooldayTemplate()
        day_template1.add(SchooldaySlot(time(8, 0), hour))
        day_template1.add(SchooldaySlot(time(11, 0), hour))
        day_template1.add(SchooldaySlot(time(8, 0), hour))
        day_template1.add(SchooldaySlot(time(11, 0), hour))

        day_template2 = SchooldayTemplate()
        day_template2.add(SchooldaySlot(time(9, 0), hour))
        day_template2.add(SchooldaySlot(time(10, 0), hour))
        day_template2.add(SchooldaySlot(time(9, 0), hour))
        day_template2.add(SchooldaySlot(time(10, 0), hour))

        tm = SequentialDayIdBasedTimetableModel(['Day 1', 'Day 2'],
                                                {'Day 1': day_template1,
                                                 'Day 2': day_template2})
        tt.model = tm

        tt.model.exceptionDayIds[date(2005, 7, 8)] = 'Day 2'
        tt.model.exceptionDayIds[date(2005, 7, 9)] = 'Day 1'
        return tt


class TestTimetableSchemaXMLViewDayIdBased(DayIdBasedModelMixin,
                                           TestTimetableSchemaXMLView):
    pass


def test_suite():
    suite = unittest.TestSuite()
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE)
    # XXX: tests not refactored yet
    #suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
    #                                   optionflags=optionflags))
    #suite.addTest(unittest.makeSuite(TestAdvancedTimetableSchemaAdd))
    #suite.addTest(unittest.makeSuite(TestTimetableSchemaXMLView))
    #suite.addTest(unittest.makeSuite(TestTimetableSchemaXMLViewDayIdBased))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
