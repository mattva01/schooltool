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
Timetable setup wizard for SchoolTool.

This module implements a the workflow described by Tom Hoffman on Jun 9 2005
on the schooltool mailing list, in ttschema-wireframes.pdf[1].

    [1] http://lists.schooltool.org/pipermail/schooltool/2005-June/001347.html

The workflow is as follows:

    1. "New timetable schema"

       (The user enters a name.)

    2. "Does your school's timetable cycle use days of the week, or a rotating
        cycle?"

        Skip to step 3 if days of the week was chosen.

    3. "Enter names of days in cycle:"

        (The user enters a list of day names in a single textarea.)

    4. "Do classes begin and end at the same time each day in your school's
        timetable?"

        Continue with step 5 if "yes".
        Skip to step 6 if "no", and "cycle" was chosen in step 2.
        Skip to step 7 if "no", and "days of the week" was chosen in step 2.

    5. "Enter start and end times for each slot"

        (The user enters a list of start and end times in a single textarea.)

        Jump to step 9.

    6. "Do the start and end times vary based on the day of the week, or the
        day in the cycle?"

        Continue with step 7 if "days of week".
        Continue with step 8 if "cycle".

    7. "Enter the start and end times of each slot on each day:"

        (The user sees 5 columns of text lines, with five buttons that let him
        add an extra slot for each column.)

        Jump to step 9.

    8. "Enter the start and end times of each slot on each day:"

        (The user sees N columns of text lines, with five buttons that let him
        add an extra slot for each column.)

    9. "Do periods have names or are they simply designated by time?"

        Skip to step 14 if periods are simply designated by time.

    10. "Enter names of the periods:"

        (The user enters a list of periods in a single textarea.)

    11. "Is the sequence of periods each day the same or different?"

        Skip to step 13 if it is different

    12. "Put the periods in order for each day:"

        (The user sees a grid of drop-downs.)

        Jump to step 14.

    13. "Put the periods in order:"

        (The user sees a list of drop-downs.)

    14. The timetable schema is created.


The shortest path through this workflow contains 6 steps, the longest contains
11 steps.

Step 14 needs the following data:

    - title (determined in step 1)
    - timetable model factory (determined in step 2)
    - a list of day IDs (determined in step 3)
    - a list of periods for each day ID
    - a list of day templates (weekday -> period_id -> start time & duration)

$Id$
"""

from zope.interface import Interface
from zope.schema import TextLine, Text, getFieldNamesInOrder
from zope.app import zapi
from zope.app.form.utility import setUpWidgets
from zope.app.form.utility import getWidgetsData
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.container.interfaces import INameChooser
from zope.app.session.interfaces import ISession

from schooltool.timetable.browser import parse_time_range
from schooltool.timetable.browser import format_time_range
from schooltool import SchoolToolMessageID as _
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable import TimetableSchema
from schooltool.timetable import TimetableSchemaDay
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.timetable import WeeklyTimetableModel
from schooltool.timetable import SequentialDaysTimetableModel



def getSessionData(request):
    """Return the data container stored in the session."""
    return ISession(request)['schooltool.ttwizard']


#
# Abstract step classes
#

class Step(BrowserView):
    """A step, one of many.

    Each step has three important methods:

        `__call__` renders the page.

        `update` processes the form, and then either stores the data in the
        session, and returns True if the form was submitted correctly, or
        returns False if it wasn't.

        `next` returns the next step.

    """

    __used_for__ = ITimetableSchemaContainer

    def getSessionData(self):
        return getSessionData(self.request)


class ChoiceStep(Step):
    """A step that requires the user to make a choice.

    Subclasses should provide three attributes:

        `question` -- question text

        `choices` -- a list of tuples (choice_value, choice_text)

        `key` -- name of the session dict key that will store the value.

    They should also define the `next` method.
    """

    __call__ = ViewPageTemplateFile("templates/ttwizard_choice.pt")

    def update(self):
        session = self.getSessionData()
        for n, (value, text) in enumerate(self.choices):
            if 'NEXT.%d' % n in self.request:
                session[self.key] = value
                return True
        return False


class FormStep(Step):
    """A step that presents a form.

    Subclasses should provide a `schema` attribute.

    They should also define the `update` and `next` methods.
    """

    __call__ = ViewPageTemplateFile("templates/ttwizard_form.pt")

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        setUpWidgets(self, self.schema, IInputWidget)

    def widgets(self):
        return [getattr(self, name + '_widget')
                for name in getFieldNamesInOrder(self.schema)]


#
# Concrete wizard steps
#

class FirstStep(FormStep):
    """First step: enter the title for the new schema."""

    __call__ = ViewPageTemplateFile("templates/ttwizard.pt")

    class schema(Interface):
        title = TextLine(title=_("Title"), default=u"default")

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError:
            return False
        session = self.getSessionData()
        session['title'] = data['title']
        return True

    def next(self):
        return CycleStep(self.context, self.request)


class CycleStep(ChoiceStep):
    """A step for choosing the timetable cycle."""

    key = 'cycle'

    question = _("Does your school's timetable cycle use days of the week,"
                 " or a rotating cycle?")

    choices = (('weekly',   _("Days of the week")),
               ('rotating', _("Rotating cycle")))

    def next(self):
        session = self.getSessionData()
        if session['cycle'] == 'weekly':
            return IndependentDaysStep(self.context, self.request)
        else:
            return DayEntryStep(self.context, self.request)

    # TODO: fill session['day_names'] with weekday names in update()

class DayEntryStep(FormStep):
    """A step for entering names of days."""

    class schema(Interface):
        days = Text(title=_("Names of days"))

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError, e:
            return False
        day_names = self.parse(data['days'])
        if not day_names:
            return False
        session = self.getSessionData()
        session['day_names'] = day_names
        return True

    def parse(self, day_names):
        """Parse a multi-line string into a list of day names.

        One day name per line.  Empty lines are ignored.  Extra spaces
        are stripped.
        """
        return filter(None, map(unicode.strip, day_names.splitlines()))

    def next(self):
        return IndependentDaysStep(self.context, self.request)


class IndependentDaysStep(ChoiceStep):
    """A step for choosing if all period times are the same each day."""

    key = 'similar_days'

    question = _("Do classes begin and end at the same time each day in"
                 " your school's timetable?")

    choices = ((True,  _("Same time")),
               (False, _("Different times")))

    def next(self):
        session = self.getSessionData()
        if session['similar_days']:
            return SimpleSlotEntryStep(self.context, self.request)
        else:
            return SlotEntryStep(self.context, self.request)


class SimpleSlotEntryStep(FormStep):
    """A step for entering times for classes.

    This step is used when the times are the same in each day.
    """

    class schema(Interface):
        times = Text(title=_("Start and end times for each slot"),
                     default=u"9:30-10:25\n10:30-11:25")

    def update(self):
        try:
            data = getWidgetsData(self, self.schema)
        except WidgetsError, e:
            return False
        try:
            times = self.parse(data['times'])
        except ValueError:
            # TODO: tell the user what was wrong
            return False
        if not times:
            return False
        session = self.getSessionData()
        session['time_slots'] = times
        return True

    def parse(self, times):
        """Parse a multi-line string into a list of time slots.

        One slot per line (HH:MM - HH:MM).  Empty lines are ignored.  Extra
        spaces are stripped.
        """
        return map(parse_time_range,
                   filter(None, map(unicode.strip, times.splitlines())))

    def next(self):
        return FinalStep(self.context, self.request)


class SlotEntryStep(Step):
    """Step for entering start and end times of slots in each day.

    This step is taken when the start/end times are different for each day.
    """

    __call__ = ViewPageTemplateFile("templates/ttwizard_slottimes.pt")

    def __init__(self, context, request):
        Step.__init__(self, context, request)
        self.day_names = self.getSessionData()['day_names']
        self.time_rows = [('', ) * len(self.day_names)]

    def update(self):
        # TODO
        return False

    def next(self):
        # TODO: redirect to period names/time step when we have it.
        return FinalStep(self.context, self.request)


class FinalStep(Step):
    """Final step: create the schema."""

    def __call__(self):
        ttschema = self.createSchema()
        self.add(ttschema)
        self.request.response.redirect(
            zapi.absoluteURL(self.context, self.request))

    def update(self):
        return True

    def next(self):
        return FirstStep(self.context, self.request)

    def createSchema(self):
        """Create the timetable schema."""
        session = self.getSessionData()
        title = session['title']
        cycle = session['cycle']
        model_factory = {'weekly': WeeklyTimetableModel,
                         'rotating': SequentialDaysTimetableModel}[cycle]
        if cycle == 'rotating':
            day_ids = session['day_names']
        else:
            day_ids = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        periods = ['A', 'B']
        template = SchooldayTemplate()
        for tstart, duration in session['time_slots']:
            ptitle = format_time_range(tstart, duration)
            template.add(SchooldayPeriod(ptitle, tstart, duration))
        day_templates = {None: template}
        model = model_factory(day_ids, day_templates)
        ttschema = TimetableSchema(day_ids, title=title, model=model)
        for day_id in day_ids:
            ttschema[day_id] = TimetableSchemaDay(periods)
        return ttschema

    def add(self, ttschema):
        """Add the timetable schema to self.context."""
        nameChooser = INameChooser(self.context)
        key = nameChooser.chooseName('', ttschema)
        self.context[key] = ttschema


#
# The wizard itself
#

class TimetableSchemaWizard(BrowserView):
    """View for defining a new timetable schema."""

    __used_for__ = ITimetableSchemaContainer

    def getSessionData(self):
        return getSessionData(self.request)

    def getLastStep(self):
        session = self.getSessionData()
        step_class = session.get('last_step', FirstStep)
        step = step_class(self.context, self.request)
        return step

    def rememberLastStep(self, step):
        session = self.getSessionData()
        session['last_step'] = step.__class__

    def __call__(self):
        if 'CANCEL' in self.request:
            self.rememberLastStep(FirstStep(self.context, self.request))
            self.request.response.redirect(
                    zapi.absoluteURL(self.context, self.request))
            return
        current_step = self.getLastStep()
        if current_step.update():
            current_step = current_step.next()
        self.rememberLastStep(current_step)
        return current_step()

