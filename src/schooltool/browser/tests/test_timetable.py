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

from zope.testing.doctestunit import DocTestSuite
from schooltool.browser.tests import RequestStub
from schooltool.browser.tests import TraversalTestMixin
from schooltool.browser.tests.test_model import AppSetupMixin

__metaclass__ = type


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
        tts = Timetable([])
        tts.__name__ = 'weekly'
        return TimetableSchemaView(tts)

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200, result)

    def test_title(self):
        view = self.createView()
        self.assertEquals(view.title(), "Timetable schema weekly")


class TestTimetableSchemaWizard(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.browser.timetable import TimetableSchemaWizard
        view = TimetableSchemaWizard(None)
        view.request = RequestStub(authenticated_user=self.manager)
        return view

    def test(self):
        view = self.createView()
        request = view.request
        result = view.render(request)
        self.assertEquals(request.code, 200)

    def test_with_data(self):
        view = self.createView()
        request = view.request
        view.request.args['day1'] = ['Monday']
        view.request.args['model'] = ['SequentialDaysTimetableModel']
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(view.ttschema,
                          createSchema(['Monday'], ['Period 1']))
        self.assertEquals(view.model_name, 'SequentialDaysTimetableModel')
        self.assertEquals(view.model_error, False)
        self.assertEquals(view.day_templates,
                          {0: createDayTemplate([('Period 1', 9, 0, 45)])})

    def test_model_error(self):
        view = self.createView()
        view.request.args['model'] = ['xxx']
        view.request.args['CREATE'] = ['Create']
        view.render(view.request)
        self.assertEquals(view.model_error, True)

    def test_model_error_ignored_unless_this_is_the_final_submit(self):
        view = self.createView()
        view.request.args['model'] = ['xxx']
        view.render(view.request)
        self.assertEquals(view.model_error, False)

    def test_buildDayTemplates_empty(self):
        view = self.createView()
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {})

    def test_buildDayTemplates_simple(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['9:00-9:45']
        view.request.args['time2.period'] = ['Period 2']
        view.request.args['time2.day0'] = ['10:00-10:45']
        view.request.args['time2.day6'] = ['10:30-11:10']
        dt = view._buildDayTemplates()
        self.assertEquals(dt,
                          {0: createDayTemplate([('Period 1', 9, 0, 45),
                                                 ('Period 2', 10, 0, 45)]),
                           6: createDayTemplate([('Period 2', 10, 30, 40)])})

    def test_buildDayTemplates_errors(self):
        view = self.createView()
        view.request.args['time1.period'] = ['Period 1']
        view.request.args['time1.day0'] = ['foo']
        dt = view._buildDayTemplates()
        self.assertEquals(dt, {})

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
        view.request.args['COPY_DAY_2'] = ["Copy"]
        schema = view._buildSchema()
        self.assertEquals(schema, createSchema(['Day 1', 'Day 2'],
                                               ['A', 'B'], ['A', 'B']))

    def test_buildSchema_copy_day_1(self):
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


class TestTimetableSchemaServiceView(AppSetupMixin, unittest.TestCase,
                                     TraversalTestMixin):

    def setUp(self):
        self.setUpSampleApp()

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        assert 'weekly' in result
        assert 'bimonthly' in result

    def createView(self):
        from schooltool.timetable import TimetableSchemaService, Timetable
        from schooltool.browser.timetable import TimetableSchemaServiceView
        context = self.app.timetableSchemaService
        context['weekly'] = Timetable([])
        context['bimonthly'] = Timetable([])
        return TimetableSchemaServiceView(context)

    def test__traverse(self):
        from schooltool.browser.timetable import TimetableSchemaView
        view = self.createView()
        self.assertTraverses(view, 'weekly', TimetableSchemaView)

    def test_list(self):
        from schooltool.timetable import Timetable
        view = self.createView()
        self.assertEquals(list(view.list()), [Timetable([]), Timetable([])])

    def test_update_delete(self):
        view = self.createView()
        view.request = RequestStub(args={'DELETE': 'Why not',
                                         'CHECK': 'weekly'})
        view.update()
        self.assertEquals(view.context.keys(), ['bimonthly'])

    def test_update_add(self):
        view = self.createView()
        view.request = RequestStub(args={'ADD': 'Why not'})
        view.update()
        self.assertEquals(view.request.code, 302)
        self.assertEquals(view.request.headers['location'],
                          'http://localhost:7001/newttschema')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.browser.timetable'))
    suite.addTest(unittest.makeSuite(TestTimetableTraverseView))
    suite.addTest(unittest.makeSuite(TestTimetableView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaWizard))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaServiceView))
    return suite


if __name__ == '__main__':
    unittest.main()
