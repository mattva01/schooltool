#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for schooltool.browser.timetable

$Id$
"""

import unittest
import datetime
from logging import INFO

from zope.testing.doctestunit import DocTestSuite
from schooltool.browser.tests import RequestStub
from schooltool.browser.tests import TraversalTestMixin
from schooltool.tests.utils import EqualsSortedMixin
from schooltool.tests.utils import NiceDiffsMixin, AppSetupMixin
from schooltool.tests.helpers import sorted
from schooltool.common import dedent

__metaclass__ = type


def createSchema(days, *periods_for_each_day):
    """Create a timetable schema.

    Example:

        createSchema(['D1', 'D2', 'D3'], ['A'], ['B', 'C'], ['D'])

    creates a schema with three days, the first of which (D1) has one
    period (A), the second (D2) has two periods (B and C), and the third
    (D3) has again one period (D).
    """

    from schooltool.timetable import Timetable
    from schooltool.timetable import TimetableDay
    schema = Timetable(days)
    for day, periods in zip(days, periods_for_each_day):
        schema[day] = TimetableDay(list(periods))
    return schema


def createDayTemplate(periods):
    """Create a SchooldayTemplate.

    Example:

        createDayTemplate([('Period 1', 9, 30, 45),
                           ('Period 2', 10, 30, 45)])

    would create a day template containing two periods, the first one starting
    at 9:30, the second one starting at 10:30, both 45 minutes long.
    """
    from schooltool.timetable import SchooldayTemplate
    from schooltool.timetable import SchooldayPeriod
    day = SchooldayTemplate()
    for period, h, m, duration in periods:
        day.add(SchooldayPeriod(period, datetime.time(h, m),
                                datetime.timedelta(minutes=duration)))
    return day


class TestTimetableTraverseView(AppSetupMixin, TraversalTestMixin,
                                unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.browser.timetable import TimetableTraverseView
        return TimetableTraverseView(self.person)

    def assertTraversesEq(self, view, name, viewclass, context=None):
        """Assert that traversal returns the appropriate view.

        Checks that view._traverse(name, request) returns an instance of
        viewclass, and that the context attribute of the new view is
        equivalent (as opposed to identical) to context.

        """
        request = RequestStub()
        destination = view._traverse(name, request)
        self.assert_(isinstance(destination, viewclass))
        self.assertEquals(destination.context, context)
        return destination

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_traverse(self):
        from schooltool.browser.timetable import TimetableTraverseView
        from schooltool.browser.timetable import TimetableView
        from schooltool.timetable import Timetable
        view = self.createView()
        t1 = self.person.timetables['2004-spring', 'default'] = Timetable([])
        t2 = self.person.timetables['2004-spring', 'another'] = Timetable([])
        t3 = self.person.timetables['2003-fall', 'another'] = Timetable([])
        t4 = self.root.timetables['2003-fall', 'default'] = Timetable([])
        view2 = self.assertTraverses(view, '2004-spring',
                                     TimetableTraverseView, view.context)
        v1 = self.assertTraversesEq(view2, 'default', TimetableView, t1)
        v2 = self.assertTraversesEq(view2, 'another', TimetableView, t2)
        self.assertRaises(KeyError, view2._traverse, 'missing', RequestStub())
        view2 = self.assertTraverses(view, '2003-fall',
                                     TimetableTraverseView, view.context)
        v3 = self.assertTraversesEq(view2, 'another', TimetableView, t3)
        v4 = self.assertTraversesEq(view2, 'default', TimetableView, t4)
        self.assertRaises(KeyError, view2._traverse, 'missing', RequestStub())

        self.assertEquals(v1.key, ('2004-spring', 'default'))
        self.assertEquals(v2.key, ('2004-spring', 'another'))
        self.assertEquals(v3.key, ('2003-fall', 'another'))
        self.assertEquals(v4.key, ('2003-fall', 'default'))


class TestTimetableView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.timetable import Timetable
        from schooltool.browser.timetable import TimetableView
        key = ('2004 fall', 'default')
        self.person.timetables[key] = Timetable([])
        self.person.title = 'John Smith'
        return TimetableView(self.person.timetables[key], key)

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 200, result)

    def test_title(self):
        view = self.createView()
        self.assertEquals(view.title(),
                          "John Smith's timetable for 2004 fall, default")


class TestTimetableSchemaView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.timetable import Timetable
        from schooltool.browser.timetable import TimetableSchemaView
        self.app.timetableSchemaService['weekly'] = Timetable([])
        return TimetableSchemaView(self.app.timetableSchemaService['weekly'])

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200, result)

    def test_title(self):
        view = self.createView()
        self.assertEquals(view.title(), "Timetable schema weekly")


class TestTimetableSchemaWizard(AppSetupMixin, NiceDiffsMixin,
                                unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.browser.timetable import TimetableSchemaWizard
        context = self.app.timetableSchemaService
        context['default'] = createSchema(['Day 1'], ['Period 1'])
        view = TimetableSchemaWizard(context)
        view.request = RequestStub(authenticated_user=self.manager)
        return view

    def test(self):
        view = self.createView()
        request = view.request
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(view.name_widget.value, 'default')
        self.assertEquals(view.name_widget.raw_value, 'default')
        self.assertEquals(view.name_widget.error, None)

    def test_with_data(self):
        view = self.createView()
        request = view.request
        view.request.args['day1'] = ['Monday']
        view.request.args['name'] = [' something ']
        view.request.args['model'] = ['SequentialDaysTimetableModel']
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(view.ttschema,
                          createSchema(['Monday'], ['Period 1']))
        self.assertEquals(view.name_widget.value, 'something')
        self.assertEquals(view.name_widget.error, None)
        self.assertEquals(view.model_name, 'SequentialDaysTimetableModel')
        self.assertEquals(view.model_error, None)
        self.assertEquals(view.day_templates,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45)])})

    def test_creation(self):
        view = self.createView()
        request = view.request
        view.request.args['day1'] = ['Monday']
        view.request.args['name'] = [' something ']
        view.request.args['model'] = ['SequentialDaysTimetableModel']
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        view.request.args['CREATE'] = ['Create']
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/ttschemas')
        schema = view.context['something']
        self.assertEquals(schema, view.ttschema)
        self.assertEquals(schema.model.timetableDayIds, view.ttschema.keys())
        self.assertEquals(schema.model.dayTemplates, view.day_templates)
        self.assertEquals(request.applog,
                          [(self.manager,
                            'Timetable schema /ttschemas/something created',
                            INFO)])

    def test_name_missing(self):
        view = self.createView()
        view.request.args['name'] = ['']
        view.render(view.request)
        self.assertEquals(view.name_widget.error,
                          "Timetable schema name must not be empty")

    def test_name_error(self):
        view = self.createView()
        view.request.args['name'] = ['not valid']
        view.render(view.request)
        self.assert_(view.name_widget.error.startswith(
                            "Timetable schema name can only contain "))

    def test_name_duplicate(self):
        view = self.createView()
        view.request.args['name'] = ['default']
        view.render(view.request)
        self.assertEquals(view.name_widget.error,
                          "Timetable schema with this name already exists.")

    def test_model_error(self):
        view = self.createView()
        view.request.args['model'] = ['xxx']
        view.request.args['CREATE'] = ['Create']
        view.render(view.request)
        self.assertEquals(view.model_error, "Please select a value")

    def test_model_error_ignored_unless_this_is_the_final_submit(self):
        view = self.createView()
        view.request.args['model'] = ['xxx']
        view.render(view.request)
        self.assertEquals(view.model_error, None)

    def test_buildDayTemplates_empty(self):
        view = self.createView()
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {None: createDayTemplate([])})

    def test_buildDayTemplates_simple(self):
        view = self.createView()
        view.duration_widget.setValue(45)
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00']
        view.request.args['time2.period'] = ['Period 2']
        view.request.args['time2.day0'] = ['10:00-10:45']
        view.request.args['time2.day6'] = ['10:30-11:10']
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})
        self.assert_(not view.discarded_some_periods)

    def test_buildDayTemplates_copy_day(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        view.request.args['time1.day1'] = ['13:00-13:45']
        view.request.args['time2.period'] = ['Period 2']
        view.request.args['time2.day0'] = ['10:00-10:45']
        view.request.args['time2.day6'] = ['10:30-11:10']
        view.request.args['COPY_PERIODS_1'] = ['C']
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           1: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_copy_empty_day(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        view.request.args['time2.period'] = ['Period 2']
        view.request.args['time2.day0'] = ['10:00-10:45']
        view.request.args['time2.day6'] = ['10:30-11:10']
        view.request.args['COPY_PERIODS_6'] = ['C']
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)])})

    def test_buildDayTemplates_copy_empty_day_over_empty_day(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        view.request.args['time2.period'] = ['Period 2']
        view.request.args['time2.day0'] = ['10:00-10:45']
        view.request.args['time2.day6'] = ['10:30-11:10']
        view.request.args['COPY_PERIODS_4'] = ['C']
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_copy_first_day_ignored(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        view.request.args['time2.period'] = ['Period 2']
        view.request.args['time2.day0'] = ['10:00-10:45']
        view.request.args['time2.day6'] = ['10:30-11:10']
        view.request.args['COPY_PERIODS_0'] = ['C']
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {None: createDayTemplate([]),
                           0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_errors(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['foo']
        # When duration_widget.value is None, both endpoints are required
        view.request.args['time1.day1'] = ['9:00']
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {None: createDayTemplate([])})
        self.assert_(view.discarded_some_periods)

    def test_buildSchema_empty(self):
        view = self.createView()
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1'], ['Period 1']))

    def test_buildSchema_from_request(self):
        view = self.createView()
        view.request.args['day1'] = ['Monday']
        view.request.args['day2'] = [' Tuesday ']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = [' B ']
        view.request.args['day2.period1'] = ['C']
        view.request.args['day2.period2'] = ['']
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                                    ['A', 'B'], ['C']))

    def test_buildSchema_empty_day(self):
        view = self.createView()
        view.request.args['day1'] = ['Monday']
        view.request.args['day2'] = ['Tuesday']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = ['B']
        view.request.args['day2.period1'] = ['']
        view.request.args['day2.period2'] = ['']
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B'], ['Period 1']))

    def test_buildSchema_repeated_day_name(self):
        view = self.createView()
        view.request.args['day1'] = ['D']
        view.request.args['day2'] = ['D']
        view.request.args['day3'] = ['D']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day2.period1'] = ['B']
        view.request.args['day3.period1'] = ['C']
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['D', 'D (2)', 'D (3)'],
                                               ['A'], ['B'], ['C']))

    def test_buildSchema_repeated_period_nam(self):
        view = self.createView()
        view.request.args['day1'] = ['D']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = ['A']
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['D'], ['A', 'A (2)']))

    def test_buildSchema_add_day(self):
        view = self.createView()
        view.request.args['day1'] = ['Monday']
        view.request.args['ADD_DAY'] = ["Add"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Day 2'],
                                               ['Period 1'], ['Period 1']))

    def test_buildSchema_add_period(self):
        view = self.createView()
        view.request.args['day1'] = ['Monday']
        view.request.args['day2'] = ['Tuesday']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = ['B']
        view.request.args['day2.period1'] = ['C']
        view.request.args['day2.period2'] = ['']
        view.request.args['ADD_PERIOD'] = ["Add"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A', 'B', 'Period 3'], ['C']))

    def test_buildSchema_add_period_not_first_day(self):
        view = self.createView()
        view.request.args['day1'] = ['Monday']
        view.request.args['day2'] = ['Tuesday']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day2.period1'] = ['C']
        view.request.args['day2.period2'] = ['D']
        view.request.args['ADD_PERIOD'] = ["Add"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Monday', 'Tuesday'],
                                               ['A'], ['C', 'D', 'Period 3']))

    def test_buildSchema_delete_day(self):
        view = self.createView()
        view.request.args['day1'] = ['Day 1']
        view.request.args['day2'] = ['Day 1']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = ['B']
        view.request.args['day2.period1'] = ['C']
        view.request.args['day2.period2'] = ['D']
        view.request.args['DELETE_DAY_1'] = ["Delete"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1'], ['C', 'D']))

    def test_buildSchema_copy_day(self):
        view = self.createView()
        view.request.args['day1'] = ['Day 1']
        view.request.args['day2'] = ['Day 2']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = ['B']
        view.request.args['day2.period1'] = ['C']
        view.request.args['day2.period2'] = ['D']
        view.request.args['COPY_DAY_1'] = ["Copy"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['A', 'B']))

    def test_buildSchema_copy_first_day_ignored(self):
        view = self.createView()
        view.request.args['day1'] = ['Day 1']
        view.request.args['day2'] = ['Day 2']
        view.request.args['day1.period1'] = ['A']
        view.request.args['day1.period2'] = ['B']
        view.request.args['day2.period1'] = ['C']
        view.request.args['day2.period2'] = ['D']
        view.request.args['COPY_DAY_0'] = ["Copy"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['C', 'D']))

    def test_all_periods(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        self.assertEquals(view.all_periods(), ['A', 'C', 'B', 'D', 'F'])

    def test_period_times(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        view.day_templates = {}
        titles = [p['title'] for p in view.period_times()]
        self.assertEquals(titles, ['A', 'C', 'B', 'D', 'F'])
        for p in view.period_times():
            self.assertEquals(p['times'], 7 * [None])

    def test_period_times_with_data(self):
        view = self.createView()
        view.ttschema = createSchema(['Day 1', 'Day 2', 'Day 3'],
                                     ['A', 'C'], ['B', 'D'], ['A', 'F'])
        view.day_templates = {0: createDayTemplate([('A', 9, 0, 45),
                                                    ('F', 10, 30, 40),
                                                    ('X', 11, 22, 33)]),
                              6: createDayTemplate([('A', 8, 55, 45),
                                                    ('D', 0, 0, 24*60)])}
        times = view.period_times()
        titles = [p['title'] for p in times]
        self.assertEquals(titles, ['A', 'C', 'B', 'D', 'F'])
        self.assertEquals(times[0]['times'], ['09:00-09:45', None, None, None,
                                              None, None, '08:55-09:40'])  # A
        self.assertEquals(times[1]['times'], [None] * 7)                   # C
        self.assertEquals(times[2]['times'], [None] * 7)                   # B
        self.assertEquals(times[3]['times'], [None] * 6 + ['00:00-24:00']) # D
        self.assertEquals(times[4]['times'], ['10:30-11:10'] + [None] * 6) # F


class TestTimetableSchemaServiceView(AppSetupMixin, unittest.TestCase,
                                     TraversalTestMixin):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.timetable import Timetable
        from schooltool.browser.timetable import TimetableSchemaServiceView
        context = self.app.timetableSchemaService
        context['weekly'] = Timetable([])
        context['bimonthly'] = Timetable([])
        return TimetableSchemaServiceView(context)

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        assert 'weekly' in result
        assert 'bimonthly' in result

    def test__traverse(self):
        from schooltool.browser.timetable import TimetableSchemaView
        view = self.createView()
        self.assertTraverses(view, 'weekly', TimetableSchemaView)

    def test_list(self):
        from schooltool.timetable import Timetable
        view = self.createView()
        self.assertEquals(list(view.list()), [Timetable([]), Timetable([])])

    def test_update_delete_nothing(self):
        view = self.createView()
        view.request = RequestStub(args={'DELETE': 'Why not'})
        result = view.update()
        self.assertEquals(sorted(view.context.keys()), ['bimonthly', 'weekly'])
        self.assertEquals(view.request.applog, [])
        self.assertEquals(result, None)

    def test_update_delete(self):
        view = self.createView()
        view.request = RequestStub(args={'DELETE': 'Why not',
                                         'CHECK': ['weekly', 'nosuchthing']})
        result = view.update()
        self.assertEquals(view.context.keys(), ['bimonthly'])
        self.assertEquals(view.request.applog,
                          [(None, 'Timetable schema /ttschemas/weekly deleted',
                            INFO)])
        self.assertEquals(result, "Deleted weekly.")

    def test_update_add(self):
        view = self.createView()
        view.request = RequestStub(args={'ADD': 'Why not'})
        view.update()
        self.assertEquals(view.request.code, 302)
        self.assertEquals(view.request.headers['location'],
                          'http://localhost:7001/newttschema')


class TestTimePeriodServiceView(AppSetupMixin, unittest.TestCase,
                                TraversalTestMixin, EqualsSortedMixin):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.cal import SchooldayModel
        from schooltool.browser.timetable import TimePeriodServiceView
        context = self.app.timePeriodService
        d = datetime.date
        context['semester1'] = SchooldayModel(d(2004, 2, 1), d(2004, 5, 31))
        context['semester2'] = SchooldayModel(d(2004, 9, 1), d(2004, 12, 24))
        return TimePeriodServiceView(context)

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        assert 'semester1' in result
        assert 'semester2' in result

    def test__traverse(self):
        from schooltool.browser.timetable import TimePeriodView
        view = self.createView()
        self.assertTraverses(view, 'semester1', TimePeriodView)

    def test_list(self):
        view = self.createView()
        self.assertEqualsSorted(list(view.list()),
                                [view.context['semester1'],
                                 view.context['semester2']])

    def test_update_delete_nothing(self):
        view = self.createView()
        view.request = RequestStub(args={'DELETE': 'Why not'})
        result = view.update()
        self.assertEquals(sorted(view.context.keys()),
                          ['semester1', 'semester2'])
        self.assertEquals(view.request.applog, [])
        self.assertEquals(result, None)

    def test_update_delete(self):
        view = self.createView()
        view.request = RequestStub(args={'DELETE': 'Why not',
                                         'CHECK': ['x', 'semester2']})
        result = view.update()
        self.assertEquals(view.context.keys(), ['semester1'])
        self.assertEquals(view.request.applog,
                          [(None,
                            'Time period /time-periods/semester2 deleted',
                            INFO)])
        self.assertEquals(result, "Deleted semester2.")

    def test_update_add(self):
        view = self.createView()
        view.request = RequestStub(args={'ADD': 'Why not'})
        view.update()
        self.assertEquals(view.request.code, 302)
        self.assertEquals(view.request.headers['location'],
                          'http://localhost:7001/newtimeperiod')


class TestTimePeriodViewBase(AppSetupMixin, NiceDiffsMixin,
                             unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.cal import SchooldayModel
        from schooltool.browser.timetable import TimePeriodViewBase
        context = self.app.timePeriodService
        context['2004-fall'] = SchooldayModel(None, None)
        view = TimePeriodViewBase(context)
        view.title = lambda: u'title'
        view.request = RequestStub(authenticated_user=self.manager)
        return view

    def test_buildModel(self):
        view = self.createView()
        request = view.request
        request.args['start'] = ['2004-09-01']
        request.args['end'] = ['2004-09-30']
        request.args['holiday'] = ['2004-09-07', '2004-09-12', 'ignore errors']
        view.start_widget.update(request)
        view.end_widget.update(request)
        model = view._buildModel(request)
        self.assertEquals(model.first, datetime.date(2004, 9, 1))
        self.assertEquals(model.last, datetime.date(2004, 9, 30))
        self.assert_(model.isSchoolday(datetime.date(2004, 9, 6)))
        self.assert_(not model.isSchoolday(datetime.date(2004, 9, 7)))
        self.assert_(model.isSchoolday(datetime.date(2004, 9, 8)))
        self.assert_(not model.isSchoolday(datetime.date(2004, 9, 12)))

    def test_buildModel_toggle(self):
        view = self.createView()
        request = view.request
        request.args['start'] = ['2004-09-01']
        request.args['end'] = ['2004-09-30']
        request.args['holiday'] = ['2004-09-07', '2004-09-12', 'ignore errors']
        request.args['TOGGLE_0'] = ['Toggle']
        request.args['TOGGLE_6'] = ['Toggle']
        view.start_widget.update(request)
        view.end_widget.update(request)
        model = view._buildModel(request)
        self.assertEquals(model.first, datetime.date(2004, 9, 1))
        self.assertEquals(model.last, datetime.date(2004, 9, 30))
        self.assert_(not model.isSchoolday(datetime.date(2004, 9, 6)))
        self.assert_(not model.isSchoolday(datetime.date(2004, 9, 7)))
        self.assert_(model.isSchoolday(datetime.date(2004, 9, 8)))
        self.assert_(model.isSchoolday(datetime.date(2004, 9, 12)))
        self.assert_(not model.isSchoolday(datetime.date(2004, 9, 27)))

    def test_calendar(self):
        self.checkCalendar(2004, 8, 1, 2004, 8, 31, """
                *                        August 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 31:                           1
                Week 32:   2   3   4   5   6   7   8
                Week 33:   9  10  11  12  13  14  15
                Week 34:  16  17  18  19  20  21  22
                Week 35:  23  24  25  26  27  28  29
                Week 36:  30  31
                """)
        self.checkCalendar(2004, 8, 2, 2004, 9, 1, """
                *                        August 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 32:   2   3   4   5   6   7   8
                Week 33:   9  10  11  12  13  14  15
                Week 34:  16  17  18  19  20  21  22
                Week 35:  23  24  25  26  27  28  29
                Week 36:  30  31
                *                     September 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 36:           1
                """)
        self.checkCalendar(2004, 8, 3, 2004, 8, 3, """
                *                        August 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 32:       3
                """)
        self.checkCalendar(2004, 12, 30, 2005, 1, 3, """
                *                      December 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:              30  31
                *                       January 2005
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:                       1   2
                Week 1 :   3
                """)

    def test_calendar_day_indices(self):
        self.checkCalendar(2004, 12, 30, 2005, 1, 3, """
                *                      December 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:               1   2
                *                       January 2005
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:                       3   4
                Week 1 :   5
                """, day_format='%(index)4s')

    def test_calendar_dates(self):
        self.checkCalendar(2004, 12, 30, 2005, 1, 3, """
                *                      December 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:             2004-12-30 2004-12-31
                *                       January 2005
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:                     2005-01-01 2005-01-02
                Week 1 : 2005-01-03
                """, day_format=' %(date)s')

    def test_calendar_checked(self):
        self.checkCalendar(2004, 12, 30, 2005, 1, 3, """
                *                      December 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:             False False
                *                       January 2005
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:                     True True
                Week 1 : False
                """, day_format=' %(checked)s')

    def test_calendar_class(self):
        self.checkCalendar(2004, 12, 30, 2005, 1, 3, """
                *                      December 2004
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:             schoolday schoolday
                *                       January 2005
                         Mon Tue Wed Thu Fri Sat Sun
                Week 53:                     holiday holiday
                Week 1 : schoolday
                """, day_format=' %(class)s')

    def checkCalendar(self, y1, m1, d1, y2, m2, d2, expected,
                      day_format='%(number)4d', no_day_format='    '):
        from schooltool.cal import SchooldayModel
        view = self.createView()
        view.model = SchooldayModel(datetime.date(y1, m1, d1),
                                    datetime.date(y2, m2, d2))
        view.model.addWeekdays(0, 1, 2, 3, 4)
        result = self.format_calendar(view.calendar(), day_format=day_format,
                                      no_day_format=no_day_format)
        self.assertEquals(result, dedent(expected).rstrip())

    def format_calendar(self, calendar,
                        day_format='%(number)4d', no_day_format='    '):
        output = []
        for month in calendar:
            output.append('*%35s' % month['title'])
            output.append('         Mon Tue Wed Thu Fri Sat Sun')
            for week in month['weeks']:
                row = ['%-7s:' % week['title']]
                for day in week['days']:
                    if day['number'] is None:
                        row.append(no_day_format % day)
                    else:
                        row.append(day_format % day)
                output.append(''.join(row).rstrip())
        return '\n'.join(output)


class TestTimePeriodView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.cal import SchooldayModel
        from schooltool.browser.timetable import TimePeriodView
        service = self.app.timePeriodService
        service['2004-fall'] = SchooldayModel(datetime.date(2004, 2, 1),
                                              datetime.date(2004, 5, 31))
        view = TimePeriodView(service['2004-fall'])
        view._service_for_unit_test = service
        view.request = RequestStub(authenticated_user=self.manager)
        return view

    def test(self):
        view = self.createView()
        request = view.request
        result = view.render(view.request)
        self.assertEquals(request.code, 200)
        self.assertEquals(view.start_widget.raw_value, '2004-02-01')
        self.assertEquals(view.start_widget.error, None)
        self.assertEquals(view.end_widget.raw_value, '2004-05-31')
        self.assertEquals(view.end_widget.error, None)
        self.assertEquals(view.model, view.context)
        self.assertEquals(view.status, None)

    def test_with_dates(self):
        view = self.createView()
        request = view.request
        request.args['start'] = ['2004-09-01']
        request.args['end'] = ['2004-09-30']
        result = view.render(view.request)
        self.assertEquals(request.code, 200)
        model = view.model
        self.assertEquals(model.first, datetime.date(2004, 9, 1))
        self.assertEquals(model.last, datetime.date(2004, 9, 30))
        self.assertNotEquals(model, view.context)
        self.assertEquals(view.status, None)

    def test_save(self):
        view = self.createView()
        request = view.request
        request.args['start'] = ['2005-01-01']
        request.args['end'] = ['2005-05-31']
        request.args['holiday'] = ['2005-05-30']
        request.args['UPDATE'] = ['Save']
        result = view.render(view.request)
        self.assertEquals(request.code, 200)
        service = view._service_for_unit_test
        model = view.model
        self.assertEquals(model, view.context)
        self.assertEquals(service['2004-fall'], model)
        self.assertEquals(model.first, datetime.date(2005, 1, 1))
        self.assertEquals(model.last, datetime.date(2005, 5, 31))
        self.assert_(model.isSchoolday(datetime.date(2005, 5, 31)))
        self.assert_(not model.isSchoolday(datetime.date(2005, 5, 30)))
        self.assertEquals(view.status, "Saved changes.")
        self.assertEquals(request.applog,
                          [(self.manager,
                            'Time period /time-periods/2004-fall updated',
                            INFO)])

    def test_start_date_missing(self):
        view = self.createView()
        view.request.args['start'] = ['']
        view.render(view.request)
        self.assertEquals(view.start_widget.value, view.context.first)
        self.assertEquals(view.start_widget.error, None)

    def test_start_date_error(self):
        view = self.createView()
        view.request.args['start'] = ['xyzzy']
        view.render(view.request)
        self.assertEquals(view.start_widget.error,
                          "Invalid date.  Please specify YYYY-MM-DD.")

    def test_start_date_ok(self):
        view = self.createView()
        view.request.args['start'] = ['2004-01-02']
        view.render(view.request)
        self.assertEquals(view.start_widget.value, datetime.date(2004, 1, 2))
        self.assertEquals(view.start_widget.error, None)

    def test_end_date_missing(self):
        view = self.createView()
        view.request.args['end'] = ['']
        view.render(view.request)
        self.assertEquals(view.end_widget.value, view.context.last)
        self.assertEquals(view.end_widget.error, None)

    def test_end_date_error(self):
        view = self.createView()
        view.request.args['end'] = ['xyzzy']
        view.render(view.request)
        self.assertEquals(view.end_widget.error,
                          "Invalid date.  Please specify YYYY-MM-DD.")

    def test_end_date_early(self):
        view = self.createView()
        view.request.args['start'] = ['2004-01-02']
        view.request.args['end'] = ['2004-01-01']
        view.render(view.request)
        self.assertEquals(view.end_widget.error,
                          "End date cannot be earlier than start date.")

    def test_end_date_ok(self):
        view = self.createView()
        view.request.args['end'] = ['2004-01-02']
        view.render(view.request)
        self.assertEquals(view.end_widget.value, datetime.date(2004, 1, 2))
        self.assertEquals(view.end_widget.error, None)


class TestNewTimePeriodView(AppSetupMixin, NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.cal import SchooldayModel
        from schooltool.browser.timetable import NewTimePeriodView
        context = self.app.timePeriodService
        context['2004-fall'] = SchooldayModel(None, None)
        view = NewTimePeriodView(context)
        view.request = RequestStub(authenticated_user=self.manager)
        return view

    def test(self):
        view = self.createView()
        request = view.request
        result = view.render(view.request)
        self.assertEquals(request.code, 200)
        self.assertEquals(view.name_widget.value, None)
        self.assertEquals(view.name_widget.error, None)
        self.assertEquals(view.start_widget.value, None)
        self.assertEquals(view.start_widget.error, None)
        self.assertEquals(view.end_widget.value, None)
        self.assertEquals(view.end_widget.error, None)
        self.assertEquals(view.model, None)

    def test_create_without_data(self):
        view = self.createView()
        request = view.request
        request.args['CREATE'] = ['Create']
        result = view.render(view.request)
        self.assertEquals(request.code, 200)
        self.assertEquals(view.name_widget.value, None)
        self.assertNotEquals(view.name_widget.error, None)
        self.assertEquals(view.start_widget.value, None)
        self.assertNotEquals(view.start_widget.error, None)
        self.assertEquals(view.end_widget.value, None)
        self.assertNotEquals(view.end_widget.error, None)
        self.assertEquals(view.model, None)

    def test_create(self):
        view = self.createView()
        request = view.request
        request.args['name'] = ['2005-spring']
        request.args['start'] = ['2005-01-01']
        request.args['end'] = ['2005-05-31']
        request.args['holiday'] = ['2005-05-30']
        request.args['CREATE'] = ['Create']
        result = view.render(view.request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/time-periods')
        model = view.service['2005-spring']
        self.assertEquals(model, view.model)
        self.assertEquals(model.first, datetime.date(2005, 1, 1))
        self.assertEquals(model.last, datetime.date(2005, 5, 31))
        self.assert_(model.isSchoolday(datetime.date(2005, 5, 31)))
        self.assert_(not model.isSchoolday(datetime.date(2005, 5, 30)))
        self.assertEquals(request.applog,
                          [(self.manager,
                            'Time period /time-periods/2005-spring created',
                            INFO)])

    def test_with_dates(self):
        view = self.createView()
        request = view.request
        request.args['start'] = ['2004-09-01']
        request.args['end'] = ['2004-09-30']
        result = view.render(view.request)
        self.assertEquals(request.code, 200)
        model = view.model
        self.assertEquals(model.first, datetime.date(2004, 9, 1))
        self.assertEquals(model.last, datetime.date(2004, 9, 30))

    def test_name_missing(self):
        view = self.createView()
        view.request.args['name'] = ['']
        view.render(view.request)
        self.assertEquals(view.name_widget.error,
                          "Time period name must not be empty")

    def test_name_error(self):
        view = self.createView()
        view.request.args['name'] = ['not valid']
        view.render(view.request)
        self.assert_(view.name_widget.error.startswith(
                            "Time period name can only contain "))

    def test_name_duplicate(self):
        view = self.createView()
        view.request.args['name'] = ['2004-fall']
        view.render(view.request)
        self.assertEquals(view.name_widget.error,
                          "Time period with this name already exists.")

    def test_start_date_missing(self):
        view = self.createView()
        view.request.args['start'] = ['']
        view.request.args['NEXT'] = ['Next']
        view.render(view.request)
        self.assertEquals(view.start_widget.error, "This field is required.")

    def test_start_date_error(self):
        view = self.createView()
        view.request.args['start'] = ['xyzzy']
        view.render(view.request)
        self.assertEquals(view.start_widget.error,
                          "Invalid date.  Please specify YYYY-MM-DD.")

    def test_start_date_ok(self):
        view = self.createView()
        view.request.args['start'] = ['2004-01-02']
        view.render(view.request)
        self.assertEquals(view.start_widget.value, datetime.date(2004, 1, 2))
        self.assertEquals(view.start_widget.error, None)

    def test_end_date_missing(self):
        view = self.createView()
        view.request.args['end'] = ['']
        view.request.args['NEXT'] = ['Next']
        view.render(view.request)
        self.assertEquals(view.end_widget.error, "This field is required.")

    def test_end_date_error(self):
        view = self.createView()
        view.request.args['end'] = ['xyzzy']
        view.render(view.request)
        self.assertEquals(view.end_widget.error,
                          "Invalid date.  Please specify YYYY-MM-DD.")

    def test_end_date_early(self):
        view = self.createView()
        view.request.args['start'] = ['2004-01-02']
        view.request.args['end'] = ['2004-01-01']
        view.render(view.request)
        self.assertEquals(view.end_widget.error,
                          "End date cannot be earlier than start date.")

    def test_end_date_ok(self):
        view = self.createView()
        view.request.args['end'] = ['2004-01-02']
        view.render(view.request)
        self.assertEquals(view.end_widget.value, datetime.date(2004, 1, 2))
        self.assertEquals(view.end_widget.error, None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.browser.timetable'))
    suite.addTest(unittest.makeSuite(TestTimetableTraverseView))
    suite.addTest(unittest.makeSuite(TestTimetableView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaWizard))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaServiceView))
    suite.addTest(unittest.makeSuite(TestTimePeriodServiceView))
    suite.addTest(unittest.makeSuite(TestTimePeriodViewBase))
    suite.addTest(unittest.makeSuite(TestTimePeriodView))
    suite.addTest(unittest.makeSuite(TestNewTimePeriodView))
    return suite


if __name__ == '__main__':
    unittest.main()
