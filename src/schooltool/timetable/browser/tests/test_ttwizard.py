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
Tests for SchoolTool timetable schema wizard.

$Id$
"""

import unittest
import datetime
from pprint import pprint

from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.interface import Interface
from zope.schema import TextLine
from zope.i18n import translate
from zope.app.testing import ztapi
from zope.app.container.interfaces import INameChooser

from schooltool.testing import setup
from schooltool.app.browser import testing as schooltool_setup
from schooltool.app.app import SimpleNameChooser
from schooltool.testing.setup import setUpApplicationPreferences
from schooltool import timetable
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.browser import format_time_range


def setUpNameChoosers():
    """Set up name choosers.

    This particular test module is only interested in name chooser
    for ITimetableSchemaContainer.
    """
    ztapi.provideAdapter(ITimetableSchemaContainer, INameChooser,
                         SimpleNameChooser)


def setUp(test):
    """Test setup.

    Sets up enough of Zope 3 to be able to render page templates.

    Creates a SchoolTool application and makes it both the current site
    and the containment root.  The application object is available as
    a global named `app` in all doctests.
    """
    schooltool_setup.setUp(test)
    setup.setupSessions()
    setUpApplicationPreferences()
    setUpNameChoosers()
    test.globs['app'] = setup.setupSchoolToolSite()


def tearDown(test):
    """Test cleanup."""
    schooltool_setup.tearDown(test)


def print_day_templates(daytemplates):
    """Print day templates."""
    keys = daytemplates.keys()
    keys.sort()
    for key in keys:
        print "--- day template %r" % key
        slots = [(period.tstart, period.duration)
                 for period in daytemplates[key]]
        slots.sort()
        for tstart, duration in slots:
            print format_time_range(tstart, duration)


def print_ttschema(ttschema):
    """Print a timetable schema as a grid."""
    for row in map(None, *[[day_id] + list(day.periods)
                           for day_id, day in ttschema.items()]):
        print " ".join(['%-12s' % cell for cell in row])


def doctest_getSessionData():
    """Unit test for getSessionData.

    This function is used as a method for both Step and TimetableSchemaWizard
    classes (and subclasses of the former).

        >>> from schooltool.timetable.browser.ttwizard import Step
        >>> context = app['ttschemas']
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

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...                                     TimetableSchemaWizard
        >>> view = TimetableSchemaWizard(context, request)
        >>> data['something']
        42

    """


def doctest_ChoiceStep():
    """Unit test for ChoiceStep

        >>> from schooltool.timetable.browser.ttwizard import ChoiceStep
        >>> context = app['ttschemas']
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


def doctest_FormStep():
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

        >>> context = app['ttschemas']
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


def doctest_FirstStep():
    """Unit test for FirstStep

        >>> from schooltool.timetable.browser.ttwizard import FirstStep
        >>> context = app['ttschemas']
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

        >>> request = TestRequest(form={'field.title': u'Sample Schema'})
        >>> view = FirstStep(context, request)
        >>> view.update()
        True

        >>> view.getSessionData()['title']
        u'Sample Schema'

    If the form is incomplete, update says so by returning False

        >>> request = TestRequest(form={'field.title': u''})
        >>> view = FirstStep(context, request)
        >>> view.update()
        False

    The next step is always CycleStep

        >>> view.next()
        <...CycleStep...>

    """


def doctest_CycleStep():
    """Unit test for CycleStep

        >>> from schooltool.timetable.browser.ttwizard import CycleStep
        >>> context = app['ttschemas']
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
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    """


def doctest_DayEntryStep():
    r"""Unit test for DayEntryStep

        >>> from schooltool.timetable.browser.ttwizard import DayEntryStep
        >>> context = app['ttschemas']
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


def doctest_IndependentDaysStep():
    r"""Unit test for IndependentDaysStep

        >>> from schooltool.timetable.browser.ttwizard \
        ...                                         import IndependentDaysStep
        >>> context = app['ttschemas']
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

    If you chose the rotating cycle, you will get to the view to enter
    the slots for rotating schedule:

        >>> view.getSessionData()['cycle'] = 'rotating'
        >>> view.next()
        <...ttwizard.RotatingSlotEntryStep...>

    """


def doctest_SimpleSlotEntryStep():
    r"""Unit test for SimpleSlotEntryStep

        >>> from schooltool.timetable.browser.ttwizard import SimpleSlotEntryStep
        >>> context = app['ttschemas']
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

    The next page is the final page.

        >>> view.next()
        <...ttwizard.NamedPeriodsStep...>

    """


def doctest_RotatingSlotEntryStep():
    r"""Unit test for RotatingSlotEntryStep

        >>> from schooltool.timetable.browser.ttwizard import RotatingSlotEntryStep
        >>> from schooltool.timetable.browser.ttwizard import getSessionData
        >>> context = app['ttschemas']
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

    SlotEntryStep.update wants at least one slot on each day:

        >>> view.request.form['times.0'] = u'9:30 - 10:25'
        >>> view.request.form['times.1'] = u''
        >>> view.update()
        False

        >>> print translate(view.error)
        Please enter at least one time slot for Twoday.

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


def doctest_WeeklySlotEntryStep():
    r"""Unit test for WeeklySlotEntryStep

        >>> from schooltool.timetable.browser.ttwizard import WeeklySlotEntryStep
        >>> from schooltool.timetable.browser.ttwizard import getSessionData
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = WeeklySlotEntryStep(context, request)
        >>> view.getSessionData()['cycle'] = 'weekly'

        >>> view.dayNames()
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    At first we get a table with one empty row of input fields:

        >>> print view()
        <BLANKLINE>
        ...
        <tr>
          <th>Monday</th>
          ...
          <th>Friday</th>
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
        </tr>
        </table>
        ...

        >>> print view.error
        None

    SlotEntryStep.update wants at least one slot on each day:

        >>> view.request.form['times.0'] = u'9:30 - 10:25'
        >>> view.request.form['times.1'] = u''
        >>> view.update()
        False

        >>> print translate(view.error)
        Please enter at least one time slot for Tuesday.

        >>> print view()
        <BLANKLINE>
        ...
        <tr>
          <td>
            <textarea rows="12" cols="15" name="times.0">9:30 - 10:25</textarea>
          </td>
          <td>
            <textarea rows="12" cols="15" name="times.1"></textarea>
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
          (datetime.time(10, 35), datetime.timedelta(0, 2700))]]

    If we choose a rotating timetable cycle and slots vary based on day of
    week, each day must have the same number of slots.

        >>> form = {'times.4': '9:15 - 10:10\n10:35 - 11:20\n11:30 - 12:15\n'}
        >>> for i in range(0, 4):
        ...     field_name = 'times.%d' % i
        ...     form[field_name] = u'9:15 - 10:10\n10:35 - 11:20'
        >>> request = TestRequest(form=form)
        >>> view = WeeklySlotEntryStep(context, request)

        >>> session = view.getSessionData()
        >>> session['cycle'] = 'rotating'
        >>> view.update()
        True

    The next page is the period naming step.

        >>> view.next()
        <...ttwizard.NamedPeriodsStep...>

    """


def doctest_NamedPeriodsStep():
    r"""Unit test for NamedPeriodsStep

        >>> from schooltool.timetable.browser.ttwizard \
        ...     import NamedPeriodsStep
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = NamedPeriodsStep(context, request)

    The next step is PeriodNamesStep if perods should be named:

        >>> view.getSessionData()['named_periods'] = True
        >>> view.next()
        <schooltool.timetable.browser.ttwizard.PeriodNamesStep...>

    If periods are not named, go straight to the final step:

        >>> view.getSessionData()['named_periods'] = False
        >>> view.next()
        <...ttwizard.FinalStep...>

    """


def doctest_PeriodNamesStep():
    r"""
    Unit test for PeriodNamesStep

        >>> from schooltool.timetable.browser.ttwizard import PeriodNamesStep
        >>> context = app['ttschemas']
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

    The next page is FinalStep.

        >>> view.next()
        <schooltool.timetable.browser.ttwizard.PeriodSequenceSameStep ...>

    """

def doctest_PeriodSequenceSameStep():
    r"""Unit test for PeriodSequenceSameStep

        >>> from schooltool.timetable.browser.ttwizard \
        ...     import PeriodSequenceSameStep
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = PeriodSequenceSameStep(context, request)

    The next step is PeriodOrderSimple if periods are the same:

        >>> view.getSessionData()['periods_same'] = True
        >>> view.next()
        <schooltool.timetable.browser.ttwizard.PeriodOrderSimple...>

    The next step is PeriodOrderComplex if periods are not the same:

        >>> view.getSessionData()['periods_same'] = False
        >>> view.next()
        <schooltool.timetable.browser.ttwizard.PeriodOrderComplex...>

    """

def doctest_PeriodOrderSimple():
    """Unit test for PeriodOrderSimple view

        >>> from schooltool.timetable.browser.ttwizard import PeriodOrderSimple
        >>> context = app['ttschemas']
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

    The next step is always the final step:

        >>> view.next()
        <...ttwizard.FinalStep ...>

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


def doctest_PeriodOrderComplex():
    """Unit test for PeriodOrderComplex view

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...     PeriodOrderComplex
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = PeriodOrderComplex(context, request)

    Let's say we have some periods:

        >>> session = view.getSessionData()
        >>> session['period_names'] = ['A', 'B', 'C', 'D']
        >>> session['day_names'] = ['Day One', 'Day Two']
        >>> session['cycle'] = 'rotating'

    The number of period dropdowns is the maximum of slots in a day:

        >>> time_slots = [
        ...     [(datetime.time(9, 30), datetime.timedelta(0, 3300))],
        ...     [(datetime.time(9, 15), datetime.timedelta(0, 3300)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),
        ...      (datetime.time(10, 35), datetime.timedelta(0, 2700)),]]
        >>> session['time_slots'] = time_slots

    Our view lets the template easily access them:

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
        >>> view.update()
        True
        >>> print view.getSessionData()['periods_order']
        [['A'], ['B', 'A', 'C']]

    The next step is always the final step:

        >>> view.next()
        <...ttwizard.FinalStep ...>

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


def doctest_FinalStep():
    """Unit test for FinalStep

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = FinalStep(context, request)

    In its first primitive incarnation, the wizard can magically create a whole
    schema from almost no user data at all!  XXX: fix this

        >>> from datetime import time, timedelta
        >>> data = view.getSessionData()
        >>> data['title'] = u'Sample Schema'
        >>> data['cycle'] = 'weekly'
        >>> data['day_names'] = ['Monday', 'Tuesday', 'Wednesday',
        ...                      'Thursday', 'Friday']
        >>> data['similar_days'] = True
        >>> data['time_slots'] = [[(time(9, 30), timedelta(minutes=55)),
        ...                        (time(10, 30), timedelta(minutes=55))]]
        >>> data['named_periods'] = False

        >>> view()

        >>> ttschema = context['sample-schema']
        >>> ttschema
        <...TimetableSchema object at ...>
        >>> print ttschema.title
        Sample Schema

    We should get redirected to the ttschemas index:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/ttschemas'

    The cycle of steps loops here

        >>> view.update()
        True
        >>> view.next()
        <...FirstStep...>

    """


def doctest_FinalStep_dayTemplates():
    """Unit test for FinalStep.dayTemplates

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> from datetime import time, timedelta
        >>> names = ['A', 'B', 'C']
        >>> slots = [(time(9, 0), timedelta(minutes=50)),
        ...          (time(12, 35), timedelta(minutes=50)),
        ...          (time(14, 15), timedelta(minutes=55))]

    Simple case: all days are the same.

        >>> dt = FinalStep.dayTemplates([names] * 4, [slots] * 4)
        >>> print_day_templates(dt)
        --- day template None
        09:00-09:50
        12:35-13:25
        14:15-15:10

    Time slots are the same for all days, but period order differs.

        >>> dt = FinalStep.dayTemplates([['A', 'B', 'C'],
        ...                              ['B', 'C', 'A'],
        ...                              ['C', 'A', 'B'],
        ...                              ['B', 'A', 'C']],
        ...                             [slots] * 4)
        >>> print_day_templates(dt)
        --- day template None
        09:00-09:50
        12:35-13:25
        14:15-15:10

    Time slots are different.

        >>> duration = timedelta(minutes=30)
        >>> dt = FinalStep.dayTemplates([['A', 'B', 'C'],
        ...                              ['B', 'C', 'A'],
        ...                              ['C', 'A', 'B'],
        ...                              ['B', 'A', 'C']],
        ...                             [[(time(9+n, 5*d), duration)
        ...                               for n in range(3)]
        ...                              for d in range(4)])
        >>> print_day_templates(dt)
        --- day template None
        --- day template 0
        09:00-09:30
        10:00-10:30
        11:00-11:30
        --- day template 1
        09:05-09:35
        10:05-10:35
        11:05-11:35
        --- day template 2
        09:10-09:40
        10:10-10:40
        11:10-11:40
        --- day template 3
        09:15-09:45
        10:15-10:45
        11:15-11:45

    """


def doctest_FinalStep_createSchema():
    """Unit test for FinalStep.createSchema

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = app['ttschemas']
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

        >>> ttschema = view.createSchema()
        >>> ttschema
        <...TimetableSchema object at ...>
        >>> print ttschema.title
        Default
        >>> print_ttschema(ttschema)
        Monday       Tuesday      Wednesday    Thursday     Friday
        09:30-10:25  09:30-10:25  09:30-10:25  09:30-10:25  09:30-10:25
        10:30-11:25  10:30-11:25  10:30-11:25  10:30-11:25  10:30-11:25

        >>> ttschema.model
        <...WeeklyTimetableModel object at ...>
        >>> print " ".join(ttschema.model.timetableDayIds)
        Monday Tuesday Wednesday Thursday Friday

    There is a single day template

        >>> print_day_templates(ttschema.model.dayTemplates)
        --- day template None
        09:30-10:25
        10:30-11:25

    The model can also be rotating.

        >>> data['cycle'] = 'rotating'
        >>> data['day_names'] = ['D1', 'D2', 'D3']
        >>> ttschema = view.createSchema()
        >>> ttschema.model
        <...SequentialDayIdBasedTimetableModel object at ...>
        >>> print_ttschema(ttschema)
        D1           D2           D3
        09:30-10:25  09:30-10:25  09:30-10:25
        10:30-11:25  10:30-11:25  10:30-11:25

    The periods can be named rather than be designated by time:

        >>> data['cycle'] = 'rotating'
        >>> data['day_names'] = ['D1', 'D2', 'D3']
        >>> data['named_periods'] = True
        >>> data['period_names'] = ['Green', 'Blue']
        >>> data['periods_same'] = True
        >>> data['periods_order'] = [['Green', 'Blue']] * 3
        >>> ttschema = view.createSchema()
        >>> ttschema.model
        <...SequentialDayIdBasedTimetableModel object at ...>
        >>> print_ttschema(ttschema)
        D1           D2           D3
        Green        Green        Green
        Blue         Blue         Blue

    """


def doctest_FinalStep_createSchema_different_order_on_different_days_weekly():
    """Unit test for FinalStep.createSchema

    Weekly cycle, same time slots on each day, different period order in 
    each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(app['ttschemas'], TestRequest())
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
        >>> ttschema = view.createSchema()

        >>> print_ttschema(ttschema)
        Monday       Tuesday      Wednesday    Thursday     Friday
        A            B            C            D            E
        B            C            D            E            F
        C            D            E            F            G
        D            E            F            G            H

        >>> ttschema.model
        <...WeeklyTimetableModel object at ...>

        >>> print_day_templates(ttschema.model.dayTemplates)
        --- day template None
        08:00-08:45
        09:00-09:45
        10:00-10:45
        11:00-11:45

    """


def doctest_FinalStep_createSchema_different_order_on_different_days_cyclic():
    """Unit test for FinalStep.createSchema

    Rotating cycle, same time slots on each day, different period order in 
    each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(app['ttschemas'], TestRequest())
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
        >>> ttschema = view.createSchema()

        >>> print_ttschema(ttschema)
        Day 1        Day 2        Day 3
        A            B            C
        B            C            D
        C            D            E
        D            E            F

        >>> ttschema.model
        <...SequentialDayIdBasedTimetableModel object at ...>

        >>> print_day_templates(ttschema.model.dayTemplates)
        --- day template 'Day 1'
        08:00-08:45
        09:00-09:45
        10:00-10:45
        11:00-11:45
        --- day template 'Day 2'
        08:00-08:45
        09:00-09:45
        10:00-10:45
        11:00-11:45
        --- day template 'Day 3'
        08:00-08:45
        09:00-09:45
        10:00-10:45
        11:00-11:45

    """


def doctest_FinalStep_createSchema_different_times():
    """Unit test for FinalStep.createSchema

    Weekly cycle, different time slots on each day, different period order in 
    each day.

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> view = FinalStep(app['ttschemas'], TestRequest())
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
        >>> ttschema = view.createSchema()

        >>> print_ttschema(ttschema)
        Monday       Tuesday      Wednesday    Thursday     Friday
        A            B            C            D            E
        B            C            D            E            F
        C            D            E            F            G
        D            E            F            G            H

        >>> ttschema.model
        <...WeeklyTimetableModel object at ...>

        >>> print_day_templates(ttschema.model.dayTemplates)
        --- day template None
        --- day template 0
        08:00-08:45
        09:00-09:45
        10:00-10:45
        11:00-11:45
        --- day template 1
        08:05-08:50
        09:05-09:50
        10:05-10:50
        11:05-11:50
        --- day template 2
        08:10-08:55
        09:10-09:55
        10:10-10:55
        11:10-11:55
        --- day template 3
        08:15-09:00
        09:15-10:00
        10:15-11:00
        11:15-12:00
        --- day template 4
        08:20-09:05
        09:20-10:05
        10:20-11:05
        11:20-12:05

    """


def doctest_FinalStep_add():
    """Unit test for FinalStep.createSchema

        >>> from schooltool.timetable.browser.ttwizard import FinalStep
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = FinalStep(context, request)

        >>> from schooltool.timetable.schema import TimetableSchema
        >>> ttschema = TimetableSchema([], title="Timetable Schema")
        >>> view.add(ttschema)

        >>> context['timetable-schema'] is ttschema
        True

    """


def doctest_TimetableSchemaWizard():
    """Unit test for TimetableSchemaWizard

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...                                     TimetableSchemaWizard
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = TimetableSchemaWizard(context, request)

    We shall stub it heavily.

        >>> class StepStub:
        ...     update_succeeds = False
        ...     def __repr__(self):
        ...         return '<same step>'
        ...     def update(self):
        ...         print 'Updating...'
        ...         return self.update_succeeds
        ...     def __call__(self):
        ...         return 'Rendered step'
        ...     def next(self):
        ...         return NextStepStub()

        >>> class NextStepStub:
        ...     def __repr__(self):
        ...         return '<next step>'
        ...     def __call__(self):
        ...         return 'Rendered next step'

        >>> view.getLastStep = StepStub

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
        'http://127.0.0.1/ttschemas'

    """


def doctest_TimetableSchemaWizard_getLastStep():
    """Unit test for TimetableSchemaWizard.getLastStep

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...                                    TimetableSchemaWizard
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = TimetableSchemaWizard(context, request)

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


def doctest_TimetableSchemaWizard_rememberLastStep():
    """Unit test for TimetableSchemaWizard.rememberLastStep

        >>> from schooltool.timetable.browser.ttwizard import \\
        ...                                     TimetableSchemaWizard
        >>> context = app['ttschemas']
        >>> request = TestRequest()
        >>> view = TimetableSchemaWizard(context, request)

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
