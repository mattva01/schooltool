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
Tests for SchoolTool timetable wizard.
"""

import unittest
import doctest
import datetime
from pprint import pprint

from zope.component import provideAdapter
from zope.interface import Interface
from zope.i18n import translate
from zope.location.location import locate
from zope.publisher.browser import TestRequest
from zope.schema import TextLine

from schooltool.app.browser import testing as schooltool_setup
from schooltool.app.app import SimpleNameChooser
from schooltool.app.app import getApplicationPreferences
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.common import format_time_range
from schooltool.testing import setup
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.timetable import TimetableContainer
from schooltool.timetable.browser.ttwizard import TimetableWizard
from schooltool.testing.util import format_table


class SchoolYearStub(object):
    def __init__(self, first, last):
        self.first = first
        self.last = last


def setUp(test):
    """Test setup.

    Sets up enough of Zope 3 to be able to render page templates.

    Creates a SchoolTool application and makes it both the current site
    and the containment root.  The application object is available as
    a global named `app` in all doctests.
    """
    schooltool_setup.setUp(test)
    setup.setUpSessions()
    setup.setUpApplicationPreferences()
    provideAdapter(SimpleNameChooser, (ITimetableContainer,))
    provideAdapter(getApplicationPreferences,
                   (ISchoolToolApplication,), IApplicationPreferences)
    provideAdapter(getSchoolToolApplication, (None,), ISchoolToolApplication)


    app = test.globs['app'] = setup.setUpSchoolToolSite()

    schoolyear = app['schoolyear'] = SchoolYearStub(
        datetime.date(2010, 07, 01),
        datetime.date(2011, 06, 15))
    locate(schoolyear, app, 'schoolyear')
    timetables =test.globs['timetables'] = TimetableContainer()
    locate(timetables, app['schoolyear'], 'timetables')

    provideAdapter(lambda container: schoolyear,
                   (ITimetableContainer, ),
                   IHaveTimetables)


def tearDown(test):
    """Test cleanup."""
    schooltool_setup.tearDown(test)


def print_day_templates(templates, filter=None):
    cols = []
    for day in templates.values():
        col = [day.title]
        for item in day.values():
            if (filter is not None and
                not filter(item)):
                col.append('')
            elif isinstance(item, Period):
                cell = item.title or ''
                if item.activity_type is not None:
                    cell = '%s %s' % (item.activity_type, cell)
                col.append(cell or '?')
            elif isinstance(item, TimeSlot):
                cell = format_time_range(item.tstart, item.duration)
                if item.activity_type is not None:
                    cell = '%s %s' % (item.activity_type, cell)
                col.append(cell or '?')
            else:
                col.append(item.__class__.__name_)
        cols.append(col)
    max_len = max([len(c) for c in cols])
    cols = [c + ['']*(max_len-len(c)) for c in cols]
    rows = map(None, *cols)
    print format_table(rows, header_rows=1)


def print_timetable(timetable):
    print "Timetable '%s'" % timetable.title
    print 'Periods (%s)' % timetable.periods.__class__.__name__
    print_day_templates(timetable.periods.templates)
    print 'Time slots (%s)' % timetable.time_slots.__class__.__name__
    print_day_templates(timetable.time_slots.templates)


def doctest_wizard_getSessionData():
    """Unit test for getSessionData.

    This function is used as a method for both Step and TimetableWizard
    classes (and subclasses of the former).

        >>> from schooltool.timetable.browser.ttwizard import Step
        >>> context = timetables
        >>> request = TestRequest()
        >>> step = Step(context, request)
        >>> data = step.getSessionData()
        >>> data
        <...SessionPkgData...>
        >>> data['something'] = 42

        >>> request = TestRequest()
        >>> step = Step(context, request)
        >>> data['something']
        42

        >>> view = TimetableWizard(context, request)
        >>> data['something']
        42

    """


def doctest_wizard_ChoiceStep():
    """Unit test for ChoiceStep

        >>> from schooltool.timetable.browser.ttwizard import ChoiceStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = ChoiceStep(context, request)

    ChoiceStep wants some attributes

        >>> view.key = 'meaning'
        >>> view.question = 'What is the meaning of life?'
        >>> view.choices = [('42', "Fourty two"),
        ...                 ('huh', "I don't know")]

        >>> print view()
        <BLANKLINE>
        ...What is the meaning of life?...
        ...<input class="button-ok" type="submit" name="NEXT.0"
                  value="Fourty two" />
        ...<input class="button-ok" type="submit" name="NEXT.1"
                  value="I don't know" />
        ...

    Update does something if you choose a valid choice

        >>> view.update()
        False

        >>> view.request = TestRequest(form={'NEXT.0': "Whatever"})
        >>> view.update()
        True
        >>> view.getSessionData()[view.key]
        '42'

        >>> view.request = TestRequest(form={'NEXT.1': "Whatever"})
        >>> view.update()
        True
        >>> view.getSessionData()[view.key]
        'huh'
    """


def doctest_wizard_FormStep():
    """Unit test for FormStep

    FormStep needs to be subclassed, and a subclass has to provide a `schema`
    attribute

        >>> from schooltool.timetable.browser.ttwizard import FormStep
        >>> class SampleFormStep(FormStep):
        ...     description = "Informative text shown above the form."
        ...     class schema(Interface):
        ...         a_field = TextLine(title=u"A field")
        ...         b_field = TextLine(title=u"B field")

    The constructor sets up input widgets.

        >>> context = timetables
        >>> request = TestRequest()
        >>> view = SampleFormStep(context, request)
        >>> view.a_field_widget
        <...TextWidget...>
        >>> view.b_field_widget
        <...TextWidget...>

    The `widgets` method returns all widgets in oroder

        >>> view.widgets() == [view.a_field_widget, view.b_field_widget]
        True

    Calling the view renders the form

        >>> print view()
        <BLANKLINE>
        ...
        <form class="plain" method="POST" action="http://127.0.0.1">
          <p>Informative text shown above the form.</p>
              <div class="row">
                  <div class="label">
                    <label for="field.a_field" title="">A field</label>
                  </div>
                  <div class="field"><input class="textType" id="field.a_field" name="field.a_field" size="20" type="text" value=""  /></div>
              </div>
              <div class="row">
                  <div class="label">
                    <label for="field.b_field" title="">B field</label>
                  </div>
                  <div class="field"><input class="textType" id="field.b_field" name="field.b_field" size="20" type="text" value=""  /></div>
              </div>
          <div class="controls">
            <input type="submit" class="button-ok" name="NEXT"
                   value="Next" />
            <input type="submit" class="button-cancel" name="CANCEL"
                   value="Cancel" />
          </div>
        </form>
        ...

    An error message may come from the `error` attribute.

        >>> view.error = "A terrible error has occurred!"
        >>> print view()
        <BLANKLINE>
        ...
        <form class="plain" method="POST" action="http://127.0.0.1">
          <p>Informative text shown above the form.</p>
          <div class="error">A terrible error has occurred!</div>
        ...

    """


def doctest_wizard_FirstStep():
    """Unit test for FirstStep

        >>> from schooltool.timetable.browser.ttwizard import FirstStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = FirstStep(context, request)

        >>> print view()
        <BLANKLINE>
        ...<input class="textType" id="field.title" name="field.title"
                  size="20" type="text" value="default" />...
        ...<input type="submit" class="button-ok" name="NEXT"
                  value="Next" />
        ...

    FirstStep.update can take the title from the request and put it into
    the session.

        >>> request = TestRequest(form={'field.title': u'Sample Timetable'})
        >>> view = FirstStep(context, request)
        >>> view.update()
        True

        >>> view.getSessionData()['title']
        u'Sample Timetable'

    If the form is incomplete, update says so by returning False

        >>> request = TestRequest(form={'field.title': u''})
        >>> view = FirstStep(context, request)
        >>> view.update()
        False

    The next step is always CycleStep

        >>> view.next()
        <...CycleStep...>

    """


def doctest_wizard_CycleStep():
    """Unit test for CycleStep

        >>> from schooltool.timetable.browser.ttwizard import CycleStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = CycleStep(context, request)
        >>> session = view.getSessionData()

    The next step is DayEntryStep for rotating cycle

        >>> session['cycle'] = 'rotating'
        >>> view.next()
        <...DayEntryStep...>

    The next step is IndependentDaysStep for weekly cycle

        >>> session['cycle'] = 'weekly'
        >>> view.next()
        <...IndependentDaysStep...>

    The session variable day_names is filled with weekday
    names in view.update() if and only if the cycle is weekly

        >>> view.request.form['NEXT.1'] = 'Rotating' # rotating
        >>> view.update()
        True
        >>> 'day_names' in session
        False

        >>> view.request.form['NEXT.0'] = 'weekly' # weekly
        >>> view.update()
        True
        >>> session['day_names']
        [u'Monday', u'Tuesday', u'Wednesday', u'Thursday', u'Friday',
         u'Saturday', u'Sunday']

    """


def doctest_wizard_DayEntryStep():
    r"""Unit test for DayEntryStep

        >>> from schooltool.timetable.browser.ttwizard import DayEntryStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = DayEntryStep(context, request)

        >>> print view()
        <BLANKLINE>
        ...<textarea cols="60" id="field.days" name="field.days"
                     rows="15" ></textarea>...

    DayEntryStep.update wants at least one day name

        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least one day name.

        >>> request = TestRequest(form={'field.days': u''})
        >>> view = DayEntryStep(context, request)
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least one day name.

        >>> request = TestRequest(form={'field.days': u'\n\n\n'})
        >>> view = DayEntryStep(context, request)
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least one day name.

        >>> request = TestRequest(form={'field.days': u'A\nB\nA\n'})
        >>> view = DayEntryStep(context, request)
        >>> view.update()
        False
        >>> print translate(view.error)
        Please make sure the day names are unique.

        >>> request = TestRequest(form={'field.days': u'A\nB\n\n'})
        >>> view = DayEntryStep(context, request)
        >>> view.update()
        True
        >>> view.error

        >>> view.getSessionData()['day_names']
        [u'A', u'B']

    The next page is IndependentDaysStep.

        >>> view.next()
        <...IndependentDaysStep...>

    """


def doctest_wizard_IndependentDaysStep():
    r"""Unit test for IndependentDaysStep

        >>> from schooltool.timetable.browser.ttwizard \
        ...                                         import IndependentDaysStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = IndependentDaysStep(context, request)

    The next step is SimpleSlotEntryStep if days are similar:

        >>> view.getSessionData()['similar_days'] = True
        >>> view.next()
        <...ttwizard.SimpleSlotEntryStep...>

    The next step cares about day names in the session.

        >>> view.getSessionData()['day_names'] = ['Day A', 'Day B']

    The next step is WeeklySlotEntryStep if each day is different and you chose
    the weekly cycle:

        >>> view.getSessionData()['similar_days'] = False
        >>> view.getSessionData()['cycle'] = 'weekly'
        >>> view.next()
        <...ttwizard.WeeklySlotEntryStep...>

    If you chose the rotating cycle, you will be asked another question
    about the time model:

        >>> view.getSessionData()['cycle'] = 'rotating'
        >>> view.next()
        <...ttwizard.SequentialModelStep...>

    """


def doctest_wizard_SequentialModelStep():
    r"""Unit test for SequentialModelStep

        >>> from schooltool.timetable.browser.ttwizard import SequentialModelStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = SequentialModelStep(context, request)

    If you choose the weekly cycle, you will be redirected to
    WeeklySlotEntryStep:

        >>> session = view.getSessionData()
        >>> session['time_model'] = 'weekly'
        >>> view.next()
        <...ttwizard.WeeklySlotEntryStep...>

    Otherwise, the rotating cycle will be used:

        >>> session['time_model'] = 'rotating'
        >>> view.next()
        <...ttwizard.RotatingSlotEntryStep...>

    """


def doctest_wizard_SimpleSlotEntryStep():
    r"""Unit test for SimpleSlotEntryStep

        >>> from schooltool.timetable.browser.ttwizard import SimpleSlotEntryStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = SimpleSlotEntryStep(context, request)

        >>> print view()
        <BLANKLINE>
        ...<textarea cols="60" id="field.times" name="field.times"
                     rows="15" >...</textarea>...

    SimpleSlotEntryStep.update wants at least one slot

        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least one time slot.

        >>> request = TestRequest(form={'field.times': u''})
        >>> view = SimpleSlotEntryStep(context, request)
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least one time slot.

        >>> request = TestRequest(form={'field.times': u'\n\n\n'})
        >>> view = SimpleSlotEntryStep(context, request)
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least one time slot.

        >>> request = TestRequest(form={'field.times': u'not a time\n\n\n'})
        >>> view = SimpleSlotEntryStep(context, request)
        >>> view.update()
        False
        >>> print translate(view.error)
        Not a valid time slot: not a time.

        >>> request = TestRequest(form={'field.times': u'unicode is tr\u00efcky'})
        >>> view = SimpleSlotEntryStep(context, request)
        >>> view.update()
        False
        >>> translate(view.error)
        u'Not a valid time slot: unicode is tr\xefcky.'

    Let's cover the successful case.  We will need day names in the session.

        >>> request = TestRequest(form={'field.times': u'9:30-10:25\n\n'})
        >>> view = SimpleSlotEntryStep(context, request)
        >>> view.getSessionData()['day_names'] = ['DA', 'DB', 'DC']
        >>> view.update()
        True
        >>> view.error

    The time_slots structure will be filled with as many duplicates of the
    slot times as there are day names.

        >>> pprint(view.getSessionData()['time_slots'])
        [[(datetime.time(9, 30), datetime.timedelta(0, 3300))],
         [(datetime.time(9, 30), datetime.timedelta(0, 3300))],
         [(datetime.time(9, 30), datetime.timedelta(0, 3300))]]

    The text area contains one slot per line; extra spaces are stripped;
    empty lines are ignored.

    The next page is the named periods page.

        >>> view.next()
        <...ttwizard.NamedPeriodsStep...>

    """


def doctest_wizard_RotatingSlotEntryStep():
    r"""Unit test for RotatingSlotEntryStep

        >>> from schooltool.timetable.browser.ttwizard import RotatingSlotEntryStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = RotatingSlotEntryStep(context, request)

        >>> view.getSessionData()['day_names'] = ['Oneday', 'Twoday']

        >>> view.dayNames()
        ['Oneday', 'Twoday']

    At first we get a table with one empty row of input fields:

        >>> print view()
        <BLANKLINE>
        ...
            <tr>
              <th>Oneday</th>
              <th>Twoday</th>
            </tr>
            <tr>
              <td>
                <textarea rows="12" cols="15" name="times.0">8:00 - 8:45
        9:05 - 9:50
        </textarea>
              </td>
              <td>
                <textarea rows="12" cols="15" name="times.1">8:00 - 8:45
        9:05 - 9:50
        </textarea>
              </td>
            </tr>
        </table>
        ...

        >>> print view.error
        None

    SlotEntryStep.update accepts days without any slots (so you could
    have a day without lessons in the middle of the cycle, or have
    lessons on Saturday, but not Sunday):

        >>> view.request.form['times.0'] = u'9:30 - 10:25'
        >>> view.request.form['times.1'] = u''
        >>> view.update()
        True

        >>> print view()
        <BLANKLINE>
        ...
        <tr>
          <th>Oneday</th>
          <th>Twoday</th>
        </tr>
        <tr>
          <td>
            <textarea rows="12" cols="15" name="times.0">9:30 - 10:25</textarea>
          </td>
          <td>
            <textarea rows="12" cols="15" name="times.1"></textarea>
          </td>
        </tr>
        </table>
        ...

    If we provide an invalid interval, an error message will be shown:

        >>> view.request.form['times.1'] = u'9:15 - 10:73'
        >>> view.update()
        False
        >>> print translate(view.error)
        Not a valid time slot: 9:15 - 10:73.

    If we provide both fields, the form will be parsed successfully:

        >>> view.request.form['times.1'] = u'9:15 - 10:10\n10:35 - 11:20'
        >>> view.update()
        True

        >>> pprint(view.getSessionData()['time_slots'])
        [[(datetime.time(9, 30), datetime.timedelta(0, 3300))],
         [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
          (datetime.time(10, 35), datetime.timedelta(0, 2700))]]

    The next page is the period naming step.

        >>> view.next()
        <...ttwizard.NamedPeriodsStep...>

    """


def doctest_wizard_WeeklySlotEntryStep():
    r"""Unit test for WeeklySlotEntryStep

        >>> from schooltool.timetable.browser.ttwizard import WeeklySlotEntryStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = WeeklySlotEntryStep(context, request)
        >>> view.getSessionData()['cycle'] = 'weekly'

        >>> view.dayNames()
        [u'Monday', u'Tuesday', u'Wednesday', u'Thursday', u'Friday',
         u'Saturday', u'Sunday']

    At first we get a table with one empty row of input fields:

        >>> print view()
        <BLANKLINE>
        ...
        <tr>
          <th>Monday</th>
          ...
          <th>Sunday</th>
        </tr>
        <tr>
          <td>
            <textarea rows="12" cols="15" name="times.0">8:00 - 8:45
        9:05 - 9:50
        </textarea>
          </td>
          ...
          <td>
            <textarea rows="12" cols="15" name="times.4">8:00 - 8:45
        9:05 - 9:50
        </textarea>
          </td>
          <td>
            <textarea rows="12" cols="15" name="times.5"></textarea>
          </td>
          <td>
            <textarea rows="12" cols="15" name="times.6"></textarea>
          </td>
        </tr>
        </table>
        ...

        >>> print view.error
        None

    SlotEntryStep.update accepts days without any slots:

        >>> view.request.form['times.0'] = u'9:30 - 10:25'
        >>> view.request.form['times.5'] = u''
        >>> view.update()
        True

        >>> print view()
        <BLANKLINE>
        ...
        <tr>
          <td>
            <textarea rows="12" cols="15" name="times.0">9:30 - 10:25</textarea>
          </td>
          ...
          <td>
            <textarea rows="12" cols="15" name="times.5"></textarea>
          </td>
          ...
        </tr>
        </table>
        ...

    If we provide an invalid interval, an error message will be shown:

        >>> view.request.form['times.1'] = u'9:15 - 10:73'
        >>> view.update()
        False
        >>> print translate(view.error)
        Not a valid time slot: 9:15 - 10:73.

    If we provide both fields, the form will be parsed successfully:

        >>> for i in range(1, 5):
        ...     field_name = 'times.%d' % i
        ...     view.request.form[field_name] = u'9:15 - 10:10\n10:35 - 11:20'
        >>> view.update()
        True

        >>> pprint(view.getSessionData()['time_slots'])
        [[(datetime.time(9, 30), datetime.timedelta(0, 3300))],
         [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
          (datetime.time(10, 35), datetime.timedelta(0, 2700))],
         [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
          (datetime.time(10, 35), datetime.timedelta(0, 2700))],
         [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
          (datetime.time(10, 35), datetime.timedelta(0, 2700))],
         [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
          (datetime.time(10, 35), datetime.timedelta(0, 2700))],
         [],
         []]

    The next page is the period naming step.

        >>> view.next()
        <...ttwizard.NamedPeriodsStep...>

    """


def doctest_wizard_NamedPeriodsStep():
    r"""Unit test for NamedPeriodsStep

        >>> from schooltool.timetable.browser.ttwizard \
        ...     import NamedPeriodsStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = NamedPeriodsStep(context, request)

    The next step is PeriodNamesStep if perods should be named:

        >>> view.getSessionData()['named_periods'] = True
        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.PeriodNamesStep'>

    If periods are not named, go straight to the homeroom step, and compute
    the default period names:

        >>> from datetime import time, timedelta
        >>> periods = [(time(9, 0), timedelta(minutes=50)),
        ...            (time(12, 35), timedelta(minutes=50)),
        ...            (time(14, 15), timedelta(minutes=55))]
        >>> periods2 = [(time(9, 10), timedelta(minutes=50)),
        ...             (time(12, 35), timedelta(minutes=50))]
        >>> view.getSessionData()['time_slots'] = [periods] * 2 + [periods2]
        >>> view.getSessionData()['named_periods'] = False

        >>> view.next()
        <...ttwizard.HomeroomStep...>

        >>> pprint(view.getSessionData()['periods_order'])
        [['09:00-09:50', '12:35-13:25', '14:15-15:10'],
         ['09:00-09:50', '12:35-13:25', '14:15-15:10'],
         ['09:10-10:00', '12:35-13:25']]

    """


def doctest_wizard_PeriodNamesStep():
    r"""Unit test for PeriodNamesStep

        >>> from schooltool.timetable.browser.ttwizard import PeriodNamesStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = PeriodNamesStep(context, request)

    The number of the required periods depends on the maximum number
    of slots:

        >>> session = view.getSessionData()
        >>> interval = (datetime.time(9, 15), datetime.timedelta(0, 3300))
        >>> view.getSessionData()['time_slots'] = \
        ...     [[interval] * 3, [interval] * 5, [interval] * 2]
        >>> view.requiredPeriods()
        5
        >>> del session['time_slots']

    The view asks the user to enter at least 3 period names:

        >>> default_slots = [[interval] * 3]
        >>> view.getSessionData()['time_slots'] = default_slots
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least 3 periods.

        >>> request = TestRequest(form={'field.periods': u''})
        >>> view = PeriodNamesStep(context, request)
        >>> view.getSessionData()['time_slots'] = default_slots
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least 3 periods.

        >>> request = TestRequest(form={'field.periods': u'\n\n\n'})
        >>> view = PeriodNamesStep(context, request)
        >>> view.getSessionData()['time_slots'] = default_slots
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least 3 periods.

        >>> request = TestRequest(form={'field.periods': u'A\nB\nB\n'})
        >>> view = PeriodNamesStep(context, request)
        >>> view.getSessionData()['time_slots'] = default_slots
        >>> view.update()
        False
        >>> print translate(view.error)
        Please make sure the period names are unique.

        >>> request = TestRequest(form={'field.periods': u'A\n'})
        >>> view = PeriodNamesStep(context, request)
        >>> view.getSessionData()['time_slots'] = default_slots
        >>> view.update()
        False
        >>> print translate(view.error)
        Please enter at least 3 periods.

        >>> request = TestRequest(form={'field.periods': u'A\nB\nC\nD'})
        >>> view = PeriodNamesStep(context, request)
        >>> view.getSessionData()['time_slots'] = default_slots
        >>> view.update()
        True
        >>> view.error

        >>> view.getSessionData()['period_names']
        [u'A', u'B', u'C', u'D']

    The next page is HomeroomStep.

        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.PeriodSequenceSameStep'>

    """


def doctest_wizard_PeriodSequenceSameStep():
    r"""Unit test for PeriodSequenceSameStep

        >>> from schooltool.timetable.browser.ttwizard \
        ...     import PeriodSequenceSameStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = PeriodSequenceSameStep(context, request)

    The next step is PeriodOrderSimple if periods are the same:

        >>> view.getSessionData()['periods_same'] = True
        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.PeriodOrderSimple'>

    The next step is PeriodOrderComplex if periods are not the same:

        >>> view.getSessionData()['periods_same'] = False
        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.PeriodOrderComplex'>

    """


def doctest_wizard_PeriodOrderSimple():
    """Unit test for PeriodOrderSimple view

        >>> from schooltool.timetable.browser.ttwizard import PeriodOrderSimple
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = PeriodOrderSimple(context, request)

    Let's say we have some periods:

        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D']

    Our view lets the template easily access them:

        >>> view.periods()
        ['A', 'B', 'C', 'D']

    The number of period dropdowns is the maximum of slots in a day:

        >>> time_slots = [
        ...     [(datetime.time(9, 30), datetime.timedelta(0, 3300))],
        ...     [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),]]
        >>> view.getSessionData()['time_slots'] = time_slots
        >>> view.numPeriods()
        3

    If we render the view, we get a list of dropdowns with consecutive
    periods selected:

        >>> print view()
        <BLANKLINE>
        ...
          <div class="row">
            <select name="period_0">
              <option selected="selected">A</option>
              <option>B</option>
              <option>C</option>
              <option>D</option>
            </select>
          </div>
          <div class="row">
            <select name="period_1">
              <option>A</option>
              <option selected="selected">B</option>
              <option>C</option>
              <option>D</option>
            </select>
          </div>
          <div class="row">
            <select name="period_2">
              <option>A</option>
              <option>B</option>
              <option selected="selected">C</option>
              <option>D</option>
            </select>
          </div>
        ...

    When the user shuffles the dropdowns and submits them, the order
    of periods is changed:

        >>> request = TestRequest(form={'period_0': 'D', 'period_1': 'C',
        ...                             'period_2': 'B', 'period_3': 'A'})
        >>> view = PeriodOrderSimple(context, request)
        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D',
        ...                                          'E', 'F']
        >>> view.getSessionData()['day_names'] = ['1', '2']
        >>> view.getSessionData()['time_slots'] = time_slots

        >>> view.update()
        True
        >>> print view.getSessionData()['periods_order']
        [['D', 'C', 'B'], ['D', 'C', 'B']]

    The next step is always the homeroom step:

        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.HomeroomStep'>

    If not all periods are in the request, update fails and the user
    gets an error.  This is unlikely in real life as the dropdowns
    have values preselected:

        >>> request = TestRequest(form={'period_0': 'D', 'period_1': 'C'})
        >>> view = PeriodOrderSimple(context, request)
        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D']
        >>> view.getSessionData()['time_slots'] = time_slots
        >>> view.update()
        False
        >>> print translate(view.error)
        Please provide all periods.
        >>> 'periods_order' in view.getSessionData()
        False

    A much more likely scenario is that some period was selected
    twice, and some was missed out:

        >>> request = TestRequest(form={'period_0': 'D', 'period_1': 'C',
        ...                             'period_2': 'C'})
        >>> view = PeriodOrderSimple(context, request)
        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D']
        >>> view.getSessionData()['time_slots'] = time_slots
        >>> view.getSessionData()['day_names'] = ['1', '2']
        >>> view.update()
        False
        >>> print translate(view.error)
        The following periods were selected more than once: C
        >>> 'periods_order' in view.getSessionData()
        False

    The view will display the order the user has selected though:

        >>> print view()
        <BLANKLINE>
        ...
          <div class="row">
            <select name="period_0">
              <option>A</option>
              <option>B</option>
              <option>C</option>
              <option selected="selected">D</option>
            </select>
          </div>
          <div class="row">
            <select name="period_1">
              <option>A</option>
              <option>B</option>
              <option selected="selected">C</option>
              <option>D</option>
            </select>
          </div>
          <div class="row">
            <select name="period_2">
              <option>A</option>
              <option>B</option>
              <option selected="selected">C</option>
              <option>D</option>
            </select>
          </div>
          ...

    """


def doctest_wizard_PeriodOrderComplex():
    """Unit test for PeriodOrderComplex view

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...     PeriodOrderComplex
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = PeriodOrderComplex(context, request)

    Let's say we have some periods and days in a rotating cycle:

        >>> session = view.getSessionData()
        >>> session['period_names'] = ['A', 'B', 'C', 'D']
        >>> session['day_names'] = ['Day One', 'Day Two']
        >>> session['cycle'] = 'rotating'
        >>> session['time_model'] = 'rotating'

    The number of period dropdowns is the maximum of slots in a day:

        >>> time_slots = [
        ...     [(datetime.time(9, 30), datetime.timedelta(0, 3300))],
        ...     [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),]]
        >>> session['time_slots'] = time_slots

    Our view lets the template easily access period and days names:

        >>> view.periods()
        ['A', 'B', 'C', 'D']

        >>> view.days()
        ['Day One', 'Day Two']

    The number of dropdowns for a day is equal to the number of slots:

        >>> view.numSlots()
        [1, 3]

    If we render the view, we get a list of dropdowns with consecutive
    periods selected:

        >>> print view()
        <BLANKLINE>
        ...
          <table>
            <tr>
              <th>Day One</th>
              <th>Day Two</th>
            </tr>
            <tr>
              <td>
                <select name="period_0_0">
                  <option selected="selected">A</option>
                  <option>B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
              <td>
                <select name="period_1_0">
                  <option selected="selected">A</option>
                  <option>B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
            </tr>
            <tr>
              <td>
              </td>
              <td>
                <select name="period_1_1">
                  <option>A</option>
                  <option selected="selected">B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
            </tr>
            <tr>
              <td>
              </td>
              <td>
                <select name="period_1_2">
                  <option>A</option>
                  <option>B</option>
                  <option selected="selected">C</option>
                  <option>D</option>
                </select>
              </td>
            </tr>
          </table>
        ...

    When the user shuffles the dropdowns and submits them, the order
    of periods is changed:

        >>> request = TestRequest(form={'period_0_0': 'A',
        ...                             'period_1_0': 'B', 'period_1_1': 'A',
        ...                             'period_1_2': 'C'})
        >>> view = PeriodOrderComplex(context, request)
        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D']
        >>> view.getSessionData()['day_names'] = ['Day 1', 'Day 2']
        >>> view.getSessionData()['time_slots'] = time_slots
        >>> view.getSessionData()['cycle'] = 'rotating'
        >>> view.getSessionData()['time_model'] = 'rotating'
        >>> view.update()
        True
        >>> print view.getSessionData()['periods_order']
        [['A'], ['B', 'A', 'C']]

    The next step is always the homeroom step:

        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.HomeroomStep'>

    If not all periods are in the request, update fails and the user
    gets an error.  This is unlikely in real life as the dropdowns
    have values preselected:

        >>> request = TestRequest(form={'period_0_0': 'A', 'period_0_1': 'B',
        ...                             'period_1_1': 'A'})
        >>> view = PeriodOrderComplex(context, request)
        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D']
        >>> view.getSessionData()['day_names'] = ['Z', 'X']
        >>> view.getSessionData()['time_slots'] = time_slots
        >>> view.getSessionData()['cycle'] = 'rotating'
        >>> view.getSessionData()['time_model'] = 'rotating'
        >>> view.update()
        False
        >>> print translate(view.error)
        Please provide all periods.
        >>> 'periods_order' not in view.getSessionData()
        True

    A much more likely scenario is that some period was selected
    twice, and some was missed out:

        >>> request = TestRequest(form={'period_0_0': 'B', 'period_0_1': 'B',
        ...                             'period_1_2': 'C',
        ...                             'period_1_0': 'A', 'period_1_1': 'A'})
        >>> view = PeriodOrderComplex(context, request)
        >>> view.getSessionData()['period_names'] = ['A', 'B', 'C', 'D']
        >>> view.getSessionData()['day_names'] = ['X', 'Y']
        >>> view.getSessionData()['time_slots'] = [
        ...     [(datetime.time(9, 30), datetime.timedelta(0, 3300)),
        ...      (datetime.time(10, 30), datetime.timedelta(0, 3300))],
        ...     [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),]]
        >>> view.getSessionData()['cycle'] = 'rotating'
        >>> view.getSessionData()['time_model'] = 'rotating'
        >>> view.update()
        False
        >>> print translate(view.error)
        The following periods were selected more than once: B on day X, A on day Y
        >>> 'periods_order' not in view.getSessionData()
        True

    The view will display the order the user has selected though:

        >>> print view()
        <BLANKLINE>
        ...
          <div class="error">The following periods were selected more
            than once: B on day X, A on day Y</div>
          <table>
            <tr>
              <th>X</th>
              <th>Y</th>
            </tr>
            <tr>
              <td>
                <select name="period_0_0">
                  <option>A</option>
                  <option selected="selected">B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
              <td>
                <select name="period_1_0">
                  <option selected="selected">A</option>
                  <option>B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
            </tr>
            <tr>
              <td>
                <select name="period_0_1">
                  <option>A</option>
                  <option selected="selected">B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
              <td>
                <select name="period_1_1">
                  <option selected="selected">A</option>
                  <option>B</option>
                  <option>C</option>
                  <option>D</option>
                </select>
              </td>
            </tr>
            <tr>
              <td>
              </td>
              <td>
                <select name="period_1_2">
                  <option>A</option>
                  <option>B</option>
                  <option selected="selected">C</option>
                  <option>D</option>
                </select>
              </td>
            </tr>
          </table>
        ...

    """


def doctest_wizard_PeriodOrderComplex_weekly_rotating():
    """Unit test for PeriodOrderComplex view

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...     PeriodOrderComplex
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = PeriodOrderComplex(context, request)

    There is one special case: a rotating cycle that uses weekdays to determine
    time slots.

        >>> session = view.getSessionData()
        >>> session['cycle'] = 'rotating'
        >>> session['time_model'] = 'weekly'

    Let's say we have some periods:

        >>> session['period_names'] = ['A', 'B', 'C', 'D']
        >>> session['day_names'] = ['Day One', 'Day Two']

    Our view lets the template easily access them:

        >>> view.periods()
        ['A', 'B', 'C', 'D']

        >>> view.days()
        ['Day One', 'Day Two']

    The number of dropdowns for each day is equal to the number of periods:

        >>> view.numSlots()
        [4, 4]

    """


def doctest_wizard_HomeroomStep():
    r"""Unit test for HomeroomStep

        >>> from schooltool.timetable.browser.ttwizard import HomeroomStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = HomeroomStep(context, request)

    If you say that your school does not take attendance in a homeroom period,
    you will be redirected to FinalStep.

        >>> session = view.getSessionData()
        >>> session['homeroom'] = False
        >>> view.next()
        <...ttwizard.FinalStep...>

    Otherwise, you will have to specify the homeroom period for each day

        >>> session['homeroom'] = True
        >>> view.next()
        <...ttwizard.HomeroomPeriodsStep...>

    """


def doctest_wizard_HomeroomPeriodsStep():
    r"""Unit test for HomeroomPeriodsStep view

        >>> from schooltool.timetable.browser.ttwizard \
        ...         import HomeroomPeriodsStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = HomeroomPeriodsStep(context, request)

    Let's say we have some days with periods:

        >>> view.getSessionData()['day_names'] = ['Day1', 'Day2', 'Day3']
        >>> view.getSessionData()['periods_order'] = [['A', 'B', 'C', 'D'],
        ...                                           ['B', 'C', 'D', 'E'],
        ...                                           ['C', 'D', 'E', 'F']]

    Our view lets the template easily access them:

        >>> view.days()
        ['Day1', 'Day2', 'Day3']

        >>> view.periodsInOrder()
        [['A', 'B', 'C', 'D'],
         ['B', 'C', 'D', 'E'],
         ['C', 'D', 'E', 'F']]

    If we render the view, we get lists of checkboxes with period names,
    one list for each day.

        >>> print view()
        <BLANKLINE>
        ...
              <td>
        <BLANKLINE>
        <BLANKLINE>
                    <input type="checkbox" name="homeroom_0_A"
                           id="homeroom_0_A" />
                    <label for="homeroom_0_A">A</label>
        <BLANKLINE>
                  <br />
        <BLANKLINE>
        <BLANKLINE>
        <BLANKLINE>
                    <input type="checkbox" name="homeroom_0_B"
                           id="homeroom_0_B" />
                    <label for="homeroom_0_B">B</label>
        <BLANKLINE>
                  <br />
        ...

    When the user selects some of the items and submits the form, the choice
    is remembered.

        >>> request = TestRequest(form={'homeroom_0_A': 'checked',
        ...                             'homeroom_0_C': 'checked',
        ...                             'homeroom_2_C': 'checked',
        ...                             'homeroom_2_F': 'checked'})
        >>> view = HomeroomPeriodsStep(context, request)
        >>> view.getSessionData()['day_names'] = ['Day 1', 'Day 2', 'Day 3']
        >>> view.getSessionData()['periods_order'] = [['A', 'B', 'C', 'D'],
        ...                                           ['B', 'C', 'D', 'E'],
        ...                                           ['C', 'D', 'E', 'F']]

        >>> view.update()
        True
        >>> print view.getSessionData()['homeroom_periods']
        [['A', 'C'], [], ['C', 'F']]

    The next step is always the final step:

        >>> view.next()
        <class 'schooltool.timetable.browser.ttwizard.FinalStep'>

    """


def doctest_wizard_FinalStep():
    r"""Unit test for FinalStep

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = FinalStep(context, request)

        >>> from datetime import time, timedelta
        >>> data = view.getSessionData()
        >>> data['title'] = u'Sample Timetable'
        >>> data['cycle'] = 'weekly'
        >>> data['day_names'] = ['Monday', 'Tuesday', 'Wednesday',
        ...                      'Thursday', 'Friday']
        >>> data['similar_days'] = True
        >>> data['time_slots'] = [[(time(9, 30), timedelta(minutes=55)),
        ...                        (time(10, 30), timedelta(minutes=55))]]
        >>> data['named_periods'] = False
        >>> from schooltool.timetable.browser.ttwizard \
        ...     import default_period_names
        >>> data['periods_order'] = default_period_names(data['time_slots'])
        >>> data['homeroom'] = False

        >>> view()

        >>> timetable = context['sample-timetable']
        >>> timetable
        <...Timetable object at ...>

        >>> print timetable.title
        Sample Timetable

    We should get redirected to the timetables index:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/schoolyear/timetables'

    The cycle of steps loops here

        >>> view.update()
        True
        >>> view.next()
        <...FirstStep...>

    """

def doctest_wizard_FinalStep_createTimeSlots():
    """Unit test for FinalStep.createTimeSlots

        >>> from datetime import time, timedelta
        >>> from schooltool.timetable.timetable import Timetable
        >>> from schooltool.timetable.browser.ttwizard import FinalStep

        >>> class FinalStepForTest(FinalStep):
        ...     def addTimeSlotTemplates(self, schedule, days):
        ...         for key, title, time_slots in days:
        ...             slots = [format_time_range(*slot) for slot in time_slots]
        ...             print '%s, %s: %s' % (key, title, slots)

        >>> day_names = ['Day one', 'Day two', 'Day three']
        >>> slots = [[(time(9, 0), timedelta(minutes=50)),
        ...           (time(12, 35), timedelta(minutes=50))],
        ...          [(time(10, 0), timedelta(minutes=50))],
        ...          [(time(11, 0), timedelta(minutes=50)),
        ...           (time(14, 35), timedelta(minutes=50))],
        ...         ]

        >>> context = timetables
        >>> request = TestRequest()

    Weekly model replaces day names with weekday names.

        >>> view = FinalStepForTest(context, request)
        >>> timetable = Timetable(None, None, title=u'Default')

        >>> print timetable.time_slots
        None

        >>> view.createTimeSlots(timetable, 'weekly', day_names, slots)
        0, Monday: ['09:00-09:50', '12:35-13:25']
        1, Tuesday: ['10:00-10:50']
        2, Wednesday: ['11:00-11:50', '14:35-15:25']

        >>> print timetable.time_slots
        <schooltool.timetable.daytemplates.WeekDayTemplates object ...>

    It can create up to 7 days timeslots.

        >>> view = FinalStepForTest(context, request)
        >>> timetable = Timetable(None, None, title=u'Default')

        >>> many_slots = slots * 4
        >>> len(many_slots)
        12

        >>> view.createTimeSlots(timetable, 'weekly', day_names, many_slots)
        0, Monday: ['09:00-09:50', '12:35-13:25']
        1, Tuesday: ['10:00-10:50']
        2, Wednesday: ['11:00-11:50', '14:35-15:25']
        3, Thursday: ['09:00-09:50', '12:35-13:25']
        4, Friday: ['10:00-10:50']
        5, Saturday: ['11:00-11:50', '14:35-15:25']
        6, Sunday: ['09:00-09:50', '12:35-13:25']

    Rotating model uses the given day titles.

        >>> view = FinalStepForTest(context, request)
        >>> timetable = Timetable(None, None, title='Default')

        >>> view.createTimeSlots(timetable, 'rotating', day_names, slots)
        0, Day one: ['09:00-09:50', '12:35-13:25']
        1, Day two: ['10:00-10:50']
        2, Day three: ['11:00-11:50', '14:35-15:25']

        >>> print timetable.time_slots
        <schooltool.timetable.daytemplates.SchoolDayTemplates object ...>

    We do not support unknown models.

        >>> view.createTimeSlots(timetable, 'this is bogus', day_names, slots)
        Traceback (most recent call last):
        ...
        NotImplementedError

    """


def doctest_wizard_FinalStep_createPeriods():
    """Unit test for FinalStep.createPeriods

        >>> from datetime import time, timedelta
        >>> from schooltool.timetable.timetable import Timetable
        >>> from schooltool.timetable.browser.ttwizard import FinalStep

        >>> class FinalStepForTest(FinalStep):
        ...     def addPeriodTemplates(self, schedule, days):
        ...         for key, title, periods in days:
        ...             print '%s, %s: %s' % (
        ...                 key, title,
        ...                 ['%s %s' % (act_type, period)
        ...                  for period, act_type in periods])

        >>> day_names = ['Day one', 'Day two', 'Day three']
        >>> period_names = [
        ...     ['first', 'second'],
        ...     ['first'],
        ...     ['first', 'second', 'third'],
        ...     ]
        >>> homeroom_names = [
        ...     ['second'],
        ...     [],
        ...     ['first', 'third'],
        ...     ]

        >>> context = timetables
        >>> request = TestRequest()

    Weekly model creates a weekly period template schedule.

        >>> view = FinalStepForTest(context, request)
        >>> timetable = Timetable(None, None, title=u'Default')

        >>> print timetable.periods
        None

        >>> view.createPeriods(timetable, 'weekly', day_names,
        ...                    period_names, homeroom_names)
        0, Day one: ['lesson first', 'homeroom second']
        1, Day two: ['lesson first']
        2, Day three: ['homeroom first', 'lesson second', 'homeroom third']

        >>> print timetable.periods
        <schooltool.timetable.daytemplates.WeekDayTemplates object ...>

    Weekly model supports up to 7 days.

        >>> view = FinalStepForTest(context, request)
        >>> timetable = Timetable(None, None, title=u'Default')

        >>> many_days = ['Day %s' % chr(n+ord('A')) for n in range(10)]
        >>> many_periods = [['X']] * len(many_days)

        >>> view.createPeriods(timetable, 'weekly', many_days,
        ...                    many_periods, [()]*len(many_periods))
        0, Day A: ['lesson X']
        1, Day B: ['lesson X']
        2, Day C: ['lesson X']
        3, Day D: ['lesson X']
        4, Day E: ['lesson X']
        5, Day F: ['lesson X']
        6, Day G: ['lesson X']

    Rotating model is also quite simple.

        >>> view = FinalStepForTest(context, request)
        >>> timetable = Timetable(None, None, title=u'Default')

        >>> print timetable.periods
        None

        >>> view.createPeriods(timetable, 'rotating', day_names,
        ...                    period_names, homeroom_names)
        0, Day one: ['lesson first', 'homeroom second']
        1, Day two: ['lesson first']
        2, Day three: ['homeroom first', 'lesson second', 'homeroom third']

        >>> print timetable.periods
        <schooltool.timetable.daytemplates.SchoolDayTemplates object ...>

    We do not support unknown models.

        >>> view.createPeriods(timetable, 'bogus', day_names,
        ...                    period_names, homeroom_names)
        Traceback (most recent call last):
        ...
        NotImplementedError

    """


def doctest_wizard_FinalStep_createTimetable():
    """Unit tests for FinalStep.createTimetable

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = FinalStep(context, request)


    This method creates a new timetable object.

        >>> data = view.getSessionData()
        >>> data['title'] = u'Some timetable'

        >>> timetable = view.createTimetable()

        >>> print timetable.title
        Some timetable

    The timetable's timezone is 'UTC', the app default:

        >>> timetable.timezone
        'UTC'

    However if we set a school preferred timezone and try again:

        >>> IApplicationPreferences(app).timezone = 'Australia/Canberra'

        >>> timetable = view.createTimetable()

        >>> timetable.timezone
        'Australia/Canberra'

    """


def doctest_wizard_FinalStep_setUpTimetable():
    r"""Unit test for FinalStep.setUpTimetable

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = FinalStep(context, request)
        >>> data = view.getSessionData()
        >>> data['title'] = u'Default'

    First, let's try the simple weekly model.

        >>> data['cycle'] = 'weekly'
        >>> data['day_names'] = ['Monday', 'Tuesday', 'Wednesday',
        ...                      'Thursday', 'Friday']
        >>> from datetime import time, timedelta
        >>> data['similar_days'] = True
        >>> data['time_slots'] = [[(time(9, 30), timedelta(minutes=55)),
        ...                        (time(10, 30), timedelta(minutes=55))]] * 5
        >>> data['named_periods'] = False
        >>> from schooltool.timetable.browser.ttwizard \
        ...     import default_period_names
        >>> data['periods_order'] = default_period_names(data['time_slots'])
        >>> data['homeroom'] = False

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (WeekDayTemplates)
        +--------------------+--------------------+--------------------+--------------------+--------------------+
        | Monday             | Tuesday            | Wednesday          | Thursday           | Friday             |
        +--------------------+--------------------+--------------------+--------------------+--------------------+
        | lesson 09:30-10:25 | lesson 09:30-10:25 | lesson 09:30-10:25 | lesson 09:30-10:25 | lesson 09:30-10:25 |
        | lesson 10:30-11:25 | lesson 10:30-11:25 | lesson 10:30-11:25 | lesson 10:30-11:25 | lesson 10:30-11:25 |
        +--------------------+--------------------+--------------------+--------------------+--------------------+
        Time slots (WeekDayTemplates)
        +-------------+-------------+-------------+-------------+-------------+
        | Monday      | Tuesday     | Wednesday   | Thursday    | Friday      |
        +-------------+-------------+-------------+-------------+-------------+
        | 09:30-10:25 | 09:30-10:25 | 09:30-10:25 | 09:30-10:25 | 09:30-10:25 |
        | 10:30-11:25 | 10:30-11:25 | 10:30-11:25 | 10:30-11:25 | 10:30-11:25 |
        +-------------+-------------+-------------+-------------+-------------+

    The model can also be rotating.

        >>> data['cycle'] = 'rotating'
        >>> data['day_names'] = ['D1', 'D2', 'D3']

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (SchoolDayTemplates)
        +--------------------+--------------------+--------------------+
        | D1                 | D2                 | D3                 |
        +--------------------+--------------------+--------------------+
        | lesson 09:30-10:25 | lesson 09:30-10:25 | lesson 09:30-10:25 |
        | lesson 10:30-11:25 | lesson 10:30-11:25 | lesson 10:30-11:25 |
        +--------------------+--------------------+--------------------+
        Time slots (SchoolDayTemplates)
        +-------------+-------------+-------------+
        | D1          | D2          | D3          |
        +-------------+-------------+-------------+
        | 09:30-10:25 | 09:30-10:25 | 09:30-10:25 |
        | 10:30-11:25 | 10:30-11:25 | 10:30-11:25 |
        +-------------+-------------+-------------+

        >>> print_day_templates(timetable.periods.templates)
        +--------------------+--------------------+--------------------+
        | D1                 | D2                 | D3                 |
        +--------------------+--------------------+--------------------+
        | lesson 09:30-10:25 | lesson 09:30-10:25 | lesson 09:30-10:25 |
        | lesson 10:30-11:25 | lesson 10:30-11:25 | lesson 10:30-11:25 |
        +--------------------+--------------------+--------------------+

        >>> print_day_templates(timetable.time_slots.templates)
        +-------------+-------------+-------------+
        | D1          | D2          | D3          |
        +-------------+-------------+-------------+
        | 09:30-10:25 | 09:30-10:25 | 09:30-10:25 |
        | 10:30-11:25 | 10:30-11:25 | 10:30-11:25 |
        +-------------+-------------+-------------+

    The periods can be named rather than be designated by time:

        >>> data['cycle'] = 'rotating'
        >>> data['day_names'] = ['D1', 'D2', 'D3']
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['Green', 'Blue']
        >>> data['periods_same'] = True
        >>> data['periods_order'] = [['Green', 'Blue']] * 3

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (SchoolDayTemplates)
        +--------------+--------------+--------------+
        | D1           | D2           | D3           |
        +--------------+--------------+--------------+
        | lesson Green | lesson Green | lesson Green |
        | lesson Blue  | lesson Blue  | lesson Blue  |
        +--------------+--------------+--------------+
        Time slots (SchoolDayTemplates)
        +-------------+-------------+-------------+
        | D1          | D2          | D3          |
        +-------------+-------------+-------------+
        | 09:30-10:25 | 09:30-10:25 | 09:30-10:25 |
        | 10:30-11:25 | 10:30-11:25 | 10:30-11:25 |
        +-------------+-------------+-------------+

    """


def doctest_wizard_FinalStep_setUpTimetable_different_order_on_different_days_weekly():
    """Unit test for FinalStep.setUpTimetable

    Weekly cycle, same time slots on each day, different period order in
    each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(timetables, TestRequest())
        >>> data = view.getSessionData()

        >>> from datetime import time, timedelta
        >>> slots = [(time(8+n, 0), timedelta(minutes=45))
        ...          for n in range(4)]

        >>> data['title'] = u'Default'
        >>> data['cycle'] = 'weekly'
        >>> data['day_names'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
        ...                      'Friday']
        >>> data['similar_days'] = True
        >>> data['time_slots'] = [slots] * 5
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        >>> data['periods_same'] = False
        >>> data['periods_order'] = [['A', 'B', 'C', 'D'],
        ...                          ['B', 'C', 'D', 'E'],
        ...                          ['C', 'D', 'E', 'F'],
        ...                          ['D', 'E', 'F', 'G'],
        ...                          ['E', 'F', 'G', 'H']]
        >>> data['homeroom'] = False

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (WeekDayTemplates)
        +----------+----------+-----------+----------+----------+
        | Monday   | Tuesday  | Wednesday | Thursday | Friday   |
        +----------+----------+-----------+----------+----------+
        | lesson A | lesson B | lesson C  | lesson D | lesson E |
        | lesson B | lesson C | lesson D  | lesson E | lesson F |
        | lesson C | lesson D | lesson E  | lesson F | lesson G |
        | lesson D | lesson E | lesson F  | lesson G | lesson H |
        +----------+----------+-----------+----------+----------+
        Time slots (WeekDayTemplates)
        +-------------+-------------+-------------+-------------+-------------+
        | Monday      | Tuesday     | Wednesday   | Thursday    | Friday      |
        +-------------+-------------+-------------+-------------+-------------+
        | 08:00-08:45 | 08:00-08:45 | 08:00-08:45 | 08:00-08:45 | 08:00-08:45 |
        | 09:00-09:45 | 09:00-09:45 | 09:00-09:45 | 09:00-09:45 | 09:00-09:45 |
        | 10:00-10:45 | 10:00-10:45 | 10:00-10:45 | 10:00-10:45 | 10:00-10:45 |
        | 11:00-11:45 | 11:00-11:45 | 11:00-11:45 | 11:00-11:45 | 11:00-11:45 |
        +-------------+-------------+-------------+-------------+-------------+

    """


def doctest_wizard_FinalStep_setUpTimetable_different_order_on_different_days_cyclic():
    """Unit test for FinalStep.setUpTimetable

    Rotating cycle, same time slots on each day, different period order in
    each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(timetables, TestRequest())
        >>> data = view.getSessionData()

        >>> from datetime import time, timedelta
        >>> slots = [(time(8+n, 0), timedelta(minutes=45))
        ...          for n in range(4)]

        >>> data['title'] = u'Default'
        >>> data['cycle'] = 'rotating'
        >>> data['day_names'] = ['Day 1', 'Day 2', 'Day 3']
        >>> data['similar_days'] = True
        >>> data['time_slots'] = [slots] * 3
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['A', 'B', 'C', 'D', 'E', 'F']
        >>> data['periods_same'] = False
        >>> data['periods_order'] = [['A', 'B', 'C', 'D'],
        ...                          ['B', 'C', 'D', 'E'],
        ...                          ['C', 'D', 'E', 'F']]
        >>> data['homeroom'] = False

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (SchoolDayTemplates)
        +----------+----------+----------+
        | Day 1    | Day 2    | Day 3    |
        +----------+----------+----------+
        | lesson A | lesson B | lesson C |
        | lesson B | lesson C | lesson D |
        | lesson C | lesson D | lesson E |
        | lesson D | lesson E | lesson F |
        +----------+----------+----------+
        Time slots (SchoolDayTemplates)
        +-------------+-------------+-------------+
        | Day 1       | Day 2       | Day 3       |
        +-------------+-------------+-------------+
        | 08:00-08:45 | 08:00-08:45 | 08:00-08:45 |
        | 09:00-09:45 | 09:00-09:45 | 09:00-09:45 |
        | 10:00-10:45 | 10:00-10:45 | 10:00-10:45 |
        | 11:00-11:45 | 11:00-11:45 | 11:00-11:45 |
        +-------------+-------------+-------------+

    """


def doctest_wizard_FinalStep_setUpTimetable_different_order_cyclic_weekly():
    """Unit test for FinalStep.setUpTimetable

    Rotating cycle, different time slots on a weekly basis, different period
    order in each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(timetables, TestRequest())
        >>> data = view.getSessionData()

        >>> from datetime import time, timedelta
        >>> slots = [[(time(8+n, d*5), timedelta(minutes=45))
        ...           for n in range(4)]
        ...          for d in range(5)]

        >>> data['title'] = u'Default'
        >>> data['cycle'] = 'rotating'
        >>> data['day_names'] = ['Day 1', 'Day 2', 'Day 3']
        >>> data['similar_days'] = False
        >>> data['time_model'] = 'weekly'
        >>> data['time_slots'] = slots
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['A', 'B', 'C', 'D', 'E', 'F']
        >>> data['periods_same'] = False
        >>> data['periods_order'] = [['A', 'B', 'C', 'D', 'E', 'F'],
        ...                          ['B', 'C', 'D', 'E', 'F', 'A'],
        ...                          ['C', 'D', 'E', 'F', 'A', 'B']]
        >>> data['homeroom'] = False

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (SchoolDayTemplates)
        +----------+----------+----------+
        | Day 1    | Day 2    | Day 3    |
        +----------+----------+----------+
        | lesson A | lesson B | lesson C |
        | lesson B | lesson C | lesson D |
        | lesson C | lesson D | lesson E |
        | lesson D | lesson E | lesson F |
        | lesson E | lesson F | lesson A |
        | lesson F | lesson A | lesson B |
        +----------+----------+----------+
        Time slots (WeekDayTemplates)
        +-------------+-------------+-------------+-------------+-------------+
        | Monday      | Tuesday     | Wednesday   | Thursday    | Friday      |
        +-------------+-------------+-------------+-------------+-------------+
        | 08:00-08:45 | 08:05-08:50 | 08:10-08:55 | 08:15-09:00 | 08:20-09:05 |
        | 09:00-09:45 | 09:05-09:50 | 09:10-09:55 | 09:15-10:00 | 09:20-10:05 |
        | 10:00-10:45 | 10:05-10:50 | 10:10-10:55 | 10:15-11:00 | 10:20-11:05 |
        | 11:00-11:45 | 11:05-11:50 | 11:10-11:55 | 11:15-12:00 | 11:20-12:05 |
        +-------------+-------------+-------------+-------------+-------------+

    """


def doctest_wizard_FinalStep_setUpTimetable_different_times():
    """Unit test for FinalStep.setUpTimetable

    Weekly cycle, different time slots on each day, different period order in
    each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(timetables, TestRequest())
        >>> data = view.getSessionData()

        >>> from datetime import time, timedelta
        >>> slots = [[(time(8+n, d*5), timedelta(minutes=45))
        ...           for n in range(4)]
        ...          for d in range(5)]

        >>> data['title'] = u'Default'
        >>> data['cycle'] = 'weekly'
        >>> data['day_names'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
        ...                      'Friday']
        >>> data['similar_days'] = False
        >>> data['time_slots'] = slots
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        >>> data['periods_same'] = False
        >>> data['periods_order'] = [['A', 'B', 'C', 'D'],
        ...                          ['B', 'C', 'D', 'E'],
        ...                          ['C', 'D', 'E', 'F'],
        ...                          ['D', 'E', 'F', 'G'],
        ...                          ['E', 'F', 'G', 'H']]
        >>> data['homeroom'] = False

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (WeekDayTemplates)
        +----------+----------+-----------+----------+----------+
        | Monday   | Tuesday  | Wednesday | Thursday | Friday   |
        +----------+----------+-----------+----------+----------+
        | lesson A | lesson B | lesson C  | lesson D | lesson E |
        | lesson B | lesson C | lesson D  | lesson E | lesson F |
        | lesson C | lesson D | lesson E  | lesson F | lesson G |
        | lesson D | lesson E | lesson F  | lesson G | lesson H |
        +----------+----------+-----------+----------+----------+
        Time slots (WeekDayTemplates)
        +-------------+-------------+-------------+-------------+-------------+
        | Monday      | Tuesday     | Wednesday   | Thursday    | Friday      |
        +-------------+-------------+-------------+-------------+-------------+
        | 08:00-08:45 | 08:05-08:50 | 08:10-08:55 | 08:15-09:00 | 08:20-09:05 |
        | 09:00-09:45 | 09:05-09:50 | 09:10-09:55 | 09:15-10:00 | 09:20-10:05 |
        | 10:00-10:45 | 10:05-10:50 | 10:10-10:55 | 10:15-11:00 | 10:20-11:05 |
        | 11:00-11:45 | 11:05-11:50 | 11:10-11:55 | 11:15-12:00 | 11:20-12:05 |
        +-------------+-------------+-------------+-------------+-------------+

    """


def doctest_wizard_FinalStep_setUpTimetable_with_homeroom():
    """Unit test for FinalStep.setUpTimetable

    Weekly cycle, different time slots on each day, different period order in
    each day, homeroom periods.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(timetables, TestRequest())
        >>> data = view.getSessionData()

        >>> from datetime import time, timedelta
        >>> slots = [[(time(8+n, d*5), timedelta(minutes=45))
        ...           for n in range(4)]
        ...          for d in range(5)]

        >>> data['title'] = u'Default'
        >>> data['cycle'] = 'weekly'
        >>> data['day_names'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
        ...                      'Friday']
        >>> data['similar_days'] = False
        >>> data['time_slots'] = slots
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        >>> data['periods_same'] = False
        >>> data['periods_order'] = [['A', 'B', 'C', 'D'],
        ...                          ['B', 'C', 'D', 'E'],
        ...                          ['C', 'D', 'E', 'F'],
        ...                          ['D', 'E', 'F', 'G'],
        ...                          ['E', 'F', 'G', 'H']]
        >>> data['homeroom'] = True
        >>> data['homeroom_periods'] = [['A'], ['C'], [], ['F'], ['H']]

        >>> timetable = Timetable(None, None, title=u'Default')
        >>> view.setUpTimetable(timetable)

        >>> print_timetable(timetable)
        Timetable 'Default'
        Periods (WeekDayTemplates)
        +------------+------------+-----------+------------+------------+
        | Monday     | Tuesday    | Wednesday | Thursday   | Friday     |
        +------------+------------+-----------+------------+------------+
        | homeroom A | lesson B   | lesson C  | lesson D   | lesson E   |
        | lesson B   | homeroom C | lesson D  | lesson E   | lesson F   |
        | lesson C   | lesson D   | lesson E  | homeroom F | lesson G   |
        | lesson D   | lesson E   | lesson F  | lesson G   | homeroom H |
        +------------+------------+-----------+------------+------------+
        Time slots (WeekDayTemplates)
        +-------------+-------------+-------------+-------------+-------------+
        | Monday      | Tuesday     | Wednesday   | Thursday    | Friday      |
        +-------------+-------------+-------------+-------------+-------------+
        | 08:00-08:45 | 08:05-08:50 | 08:10-08:55 | 08:15-09:00 | 08:20-09:05 |
        | 09:00-09:45 | 09:05-09:50 | 09:10-09:55 | 09:15-10:00 | 09:20-10:05 |
        | 10:00-10:45 | 10:05-10:50 | 10:10-10:55 | 10:15-11:00 | 10:20-11:05 |
        | 11:00-11:45 | 11:05-11:50 | 11:10-11:55 | 11:15-12:00 | 11:20-12:05 |
        +-------------+-------------+-------------+-------------+-------------+

    """


def doctest_wizard_FinalStep_add():
    """Unit test for FinalStep.setUpTimetable

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = timetables
        >>> request = TestRequest()
        >>> view = FinalStep(context, request)

        >>> from schooltool.timetable.timetable import Timetable
        >>> timetable = Timetable(None, None, title='timetable')
        >>> view.add(timetable)

        >>> context['timetable'] is timetable
        True

    """


def doctest_wizard_TimetableWizard():
    """Unit test for TimetableWizard

        >>> context = timetables
        >>> request = TestRequest()
        >>> view = TimetableWizard(context, request)

    We shall stub it heavily.

        >>> class StepStub:
        ...     update_succeeds = False
        ...     def __init__(self, context, request):
        ...         pass
        ...     def __repr__(self):
        ...         return '<same step>'
        ...     def update(self):
        ...         print 'Updating...'
        ...         return self.update_succeeds
        ...     def __call__(self):
        ...         return 'Rendered step'
        ...     def next(self):
        ...         return NextStepStub

        >>> class NextStepStub(object):
        ...     def __init__(self, context, request):
        ...         pass
        ...     def __repr__(self):
        ...         return '<next step>'
        ...     def __call__(self):
        ...         return 'Rendered next step'

        >>> view.getLastStep = lambda: StepStub(None, None)

        >>> def rememberLastStep(step):
        ...     print 'Remembering step: %s' % step
        >>> view.rememberLastStep = rememberLastStep

    There are three main cases.

    Case 1: the user completes the current step successfully.

        >>> StepStub.update_succeeds = True
        >>> print view()
        Updating...
        Remembering step: <next step>
        Rendered next step

    Case 2: the user does not complete the current step successfully.

        >>> StepStub.update_succeeds = False
        >>> print view()
        Updating...
        Remembering step: <same step>
        Rendered step

    Case 3: the user presses the 'Cancel' button

        >>> view.request.form['CANCEL'] = 'Cancel'
        >>> view()
        Remembering step: <...FirstStep...>

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/schoolyear/timetables'

    """


def doctest_wizard_TimetableWizard_getLastStep():
    """Unit test for TimetableWizard.getLastStep

        >>> context = timetables
        >>> request = TestRequest()
        >>> view = TimetableWizard(context, request)

    When there is no step saved in the session, getLastStep returns the first
    step.

        >>> view.getLastStep()
        <...FirstStep...>

    When there is one, that's what getLastStep returns.

        >>> from schooltool.timetable.browser.ttwizard import CycleStep
        >>> view.getSessionData()['last_step'] = CycleStep
        >>> view.getLastStep()
        <...CycleStep...>

    """


def doctest_wizard_TimetableWizard_rememberLastStep():
    """Unit test for TimetableWizard.rememberLastStep

        >>> context = timetables
        >>> request = TestRequest()
        >>> view = TimetableWizard(context, request)

        >>> from schooltool.timetable.browser.ttwizard import CycleStep
        >>> view.rememberLastStep(CycleStep(context, request))
        >>> view.getSessionData()['last_step']
        <class 'schooltool.timetable.browser.ttwizard.CycleStep'>

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return unittest.TestSuite([
                doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                     optionflags=optionflags),
                doctest.DocTestSuite('schooltool.timetable.browser.ttwizard',
                                     optionflags=optionflags),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
