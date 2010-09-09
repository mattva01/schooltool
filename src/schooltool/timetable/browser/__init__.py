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
SchoolTool timetabling views.
"""
import datetime
import re

import zope.event
import zope.schema
from zope.container.interfaces import INameChooser
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.interface.exceptions import Invalid
from zope.interface import implements
from zope.interface import Interface
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form import form, field, button, widget, validator
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget
from z3c.form.util import getSpecification

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.utils import TitledContainerItemVocabulary
from schooltool.calendar.utils import parse_date, parse_time
from schooltool.course.interfaces import ISection
from schooltool.common import DateRange
from schooltool.term.interfaces import ITerm
from schooltool.term.term import getTermForDate
from schooltool.timetable import SchooldaySlot
from schooltool.timetable import Timetable, TimetableDay
from schooltool.timetable import TimetableActivity
from schooltool.timetable import TimetableReplacedEvent
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.interfaces import ITimetable, IOwnTimetables
from schooltool.timetable.interfaces import ITimetables, ITimetableDict
from schooltool.timetable import TimetableOverlapError, TimetableOverflowError
from schooltool.timetable import validateAgainstTerm
from schooltool.timetable import validateAgainstOthers
from schooltool.traverser.interfaces import ITraverserPlugin
from schooltool.schoolyear.interfaces import ISchoolYear

from schooltool.common import SchoolToolMessage as _


class TabindexMixin(object):
    """Tab index calculator mixin for views."""

    def __init__(self):
        self.__tabindex = 0
        self.__tabindex_matrix = []

    def next_tabindex(self):
        """Return the next tabindex.

          >>> view = TabindexMixin()
          >>> [view.next_tabindex() for n in range(5)]
          [1, 2, 3, 4, 5]

        See the docstring for tabindex_matrix for an example where
        next_tabindex() returns values out of order
        """
        if self.__tabindex_matrix:
            return self.__tabindex_matrix.pop(0)
        else:
            self.__tabindex += 1
            return self.__tabindex

    def tabindex_matrix(self, nrows, ncols):
        """Ask next_tabindex to return transposed tab indices for a matrix.

        For example, suppose that you have a 3 x 5 matrix like this:

               col1 col2 col3 col4 col5
          row1   1    4    7   10   13
          row2   2    5    8   11   14
          row3   3    6    9   12   15

        Then you do

          >>> view = TabindexMixin()
          >>> view.tabindex_matrix(3, 5)
          >>> [view.next_tabindex() for n in range(5)]
          [1, 4, 7, 10, 13]
          >>> [view.next_tabindex() for n in range(5)]
          [2, 5, 8, 11, 14]
          >>> [view.next_tabindex() for n in range(5)]
          [3, 6, 9, 12, 15]

        After the matrix is finished, next_tabindex reverts back to linear
        allocation:

          >>> [view.next_tabindex() for n in range(5)]
          [16, 17, 18, 19, 20]

        """
        first = self.__tabindex + 1
        self.__tabindex_matrix += [first + col * nrows + row
                                     for row in range(nrows)
                                       for col in range(ncols)]
        self.__tabindex += nrows * ncols


class TimetablesTraverser(object):
    """A traverser that allows to traverse to a timetable of its context."""

    adapts(IOwnTimetables)
    implements(ITraverserPlugin)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == 'timetables':
            return ITimetables(self.context).timetables

        raise NotFound(self.context, name, request)


def fix_duplicates(names):
    """Change a list of names so that there are no duplicates.

    Trivial cases:

      >>> fix_duplicates([])
      []
      >>> fix_duplicates(['a', 'b', 'c'])
      ['a', 'b', 'c']

    Simple case:

      >>> fix_duplicates(['a', 'b', 'b', 'a', 'b'])
      ['a', 'b', 'b (2)', 'a (2)', 'b (3)']

    More interesting cases:

      >>> fix_duplicates(['a', 'b', 'b', 'a', 'b (2)', 'b (2)'])
      ['a', 'b', 'b (3)', 'a (2)', 'b (2)', 'b (2) (2)']

    """
    seen = set(names)
    if len(seen) == len(names):
        return names    # no duplicates
    result = []
    used = set()
    for name in names:
        if name in used:
            n = 2
            while True:
                candidate = '%s (%d)' % (name, n)
                if not candidate in seen:
                    name = candidate
                    break
                n += 1
            seen.add(name)
        result.append(name)
        used.add(name)
    return result


def parse_time_range(value, default_duration=None):
    """Parse a range of times (e.g. 9:45-14:20).

    Example:

        >>> parse_time_range('9:45-14:20')
        (datetime.time(9, 45), datetime.timedelta(0, 16500))

        >>> parse_time_range('00:00-24:00')
        (datetime.time(0, 0), datetime.timedelta(1))

        >>> parse_time_range('10:00-10:00')
        (datetime.time(10, 0), datetime.timedelta(0))

    Time ranges may span midnight

        >>> parse_time_range('23:00-02:00')
        (datetime.time(23, 0), datetime.timedelta(0, 10800))

    When the default duration is specified, you may omit the second time

        >>> parse_time_range('23:00', 45)
        (datetime.time(23, 0), datetime.timedelta(0, 2700))

    Invalid values cause a ValueError

        >>> parse_time_range('something else')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: something else

        >>> parse_time_range('9:00')
        Traceback (most recent call last):
          ...
        ValueError: duration is not specified

        >>> parse_time_range('9:00-9:75')
        Traceback (most recent call last):
          ...
        ValueError: minute must be in 0..59

        >>> parse_time_range('5:99-6:00')
        Traceback (most recent call last):
          ...
        ValueError: minute must be in 0..59

        >>> parse_time_range('14:00-24:01')
        Traceback (most recent call last):
          ...
        ValueError: hour must be in 0..23

    White space can be inserted between times

        >>> parse_time_range(' 9:45 - 14:20 ')
        (datetime.time(9, 45), datetime.timedelta(0, 16500))

    but not inside times

        >>> parse_time_range('9: 45-14:20')
        Traceback (most recent call last):
          ...
        ValueError: bad time range: 9: 45-14:20

    """
    m = re.match(r'\s*(\d+):(\d+)\s*(?:-\s*(\d+):(\d+)\s*)?$', value)
    if not m:
        raise ValueError('bad time range: %s' % value)
    h1, m1 = int(m.group(1)), int(m.group(2))
    if not m.group(3):
        if default_duration is None:
            raise ValueError('duration is not specified')
        duration = default_duration
    else:
        h2, m2 = int(m.group(3)), int(m.group(4))
        if (h2, m2) != (24, 0):   # 24:00 is expressly allowed here
            datetime.time(h2, m2) # validate the second time
        duration = (h2*60+m2) - (h1*60+m1)
        if duration < 0:
            duration += 1440
    return datetime.time(h1, m1), datetime.timedelta(minutes=duration)


def format_time_range(start, duration):
    """Format a range of times (e.g. 9:45-14:20).

    Example:

        >>> format_time_range(datetime.time(9, 45),
        ...                   datetime.timedelta(0, 16500))
        '09:45-14:20'

        >>> format_time_range(datetime.time(0, 0), datetime.timedelta(1))
        '00:00-24:00'

        >>> format_time_range(datetime.time(10, 0), datetime.timedelta(0))
        '10:00-10:00'

        >>> format_time_range(datetime.time(23, 0),
        ...                   datetime.timedelta(0, 10800))
        '23:00-02:00'

    """
    end = (datetime.datetime.combine(datetime.date.today(), start) + duration)
    ends = end.strftime('%H:%M')
    if ends == '00:00' and duration == datetime.timedelta(1):
        return '00:00-24:00' # special case
    else:
        return '%s-%s' % (start.strftime('%H:%M'), ends)


def format_timetable_for_presentation(timetable):
    """Prepare a timetable for presentation with Page Templates.

    Returns a matrix where columns correspond to days, rows correspond to
    periods, and cells contain a dict with two keys

      'period' -- the name of this period (different days may have different
                  periods)

      'activity' -- activity or activities that occur during that period of a
                    day.

    First, let us create a timetable:

      >>> timetable = Timetable(['day 0', 'day 1', 'day 2', 'day 3'])
      >>> timetable['day 0'] = TimetableDay()
      >>> timetable['day 1'] = TimetableDay(['A', 'B'])
      >>> timetable['day 2'] = TimetableDay(['C', 'D', 'E'])
      >>> timetable['day 3'] = TimetableDay(['F'])
      >>> timetable['day 1'].add('A', TimetableActivity('Something'))
      >>> timetable['day 1'].add('B', TimetableActivity('A2'))
      >>> timetable['day 1'].add('B', TimetableActivity('A1'))
      >>> timetable['day 2'].add('C', TimetableActivity('Else'))
      >>> timetable['day 3'].add('F', TimetableActivity('A3'))

    Here's how it looks like

      >>> matrix = format_timetable_for_presentation(timetable)
      >>> for row in matrix:
      ...    for cell in row:
      ...        print '%(period)1s: %(activity)-11s |' % cell,
      ...    print
       :             | A: Something   | C: Else        | F: A3          |
       :             | B: A1 / A2     | D:             |  :             |
       :             |  :             | E:             |  :             |


    """
    rows = []
    for ncol, (id, day) in enumerate(timetable.items()):
        nrow = 0
        for nrow, (period, actiter) in enumerate(day.items()):
            activities = []
            for a in actiter:
                activities.append(a.title)
            activities.sort()
            if nrow >= len(rows):
                rows.append([{'period': '', 'activity': ''}] * ncol)
            rows[nrow].append({'period': period,
                               'activity': " / ".join(activities)})
        for nrow in range(nrow + 1, len(rows)):
            rows[nrow].append({'period': '', 'activity': ''})
    return rows


class TimetableView(BrowserView):

    __used_for__ = ITimetable

    def rows(self):
        return format_timetable_for_presentation(self.context)


class TimetableConflictMixin(object):
    """A mixin for views that check for booking conflicts."""

    def sectionMap(self, term, ttschema):
        """Compute a mapping of timetable slots to sections.

        Returns a dict {(day_id, period_id): Set([section])}.  The set for
        each period contains all sections that have activities in the
        (non-composite) timetable during that timetable period.
        """
        from schooltool.timetable import findRelatedTimetables

        section_map = {}
        for day_id, day in ttschema.items():
            for period_id in day.periods:
                section_map[day_id, period_id] = set()

        term_tables = [removeSecurityProxy(tt)
                       for tt in findRelatedTimetables(term)]

        for timetable in findRelatedTimetables(ttschema):
            if removeSecurityProxy(timetable) not in term_tables:
                continue
            for day_id, period_id, activity in timetable.activities():
                section_map[day_id, period_id].add(timetable.__parent__.__parent__)

        return section_map

    def getSchema(self):
        """Return the chosen timetable schema.

        If there are no timetable schemas, None is returned.
        """
        app = ISchoolToolApplication(None)
        ttschemas = ITimetableSchemaContainer(app, None)
        if ttschemas is None:
            return None
        ttschema_id = self.request.get('ttschema', ttschemas.default_id)
        ttschema = ttschemas.get(ttschema_id, None)
        if not ttschema and ttschemas:
            ttschema = ttschemas.values()[0]
        return ttschema

    @property
    def owner(self):
        # XXX: make this property obsolete as soon as possible
        return self.context

    def getTerm(self):
        """Return the chosen term."""
        # XXX: make this method obsolete as soon as possible
        return ITerm(self.owner)

    def getSections(self, item):
        raise NotImplementedError(
            "This method should be implemented in subclasses")

    def getGroupSections(self):
        raise NotImplementedError(
            "This method should be implemented in subclasses")

    def getTimetable(self):
        # XXX: somewhat broken as of now.
        timetables = ITimetables(self.owner)
        term = self.getTerm()
        ttschema = self.getSchema()
        return timetables.lookup(term, ttschema)


class TimetableSetupViewBase(BrowserView, TimetableConflictMixin):
    """Common methods for setting up timetables."""

    @property
    def ttschemas(self):
        return ITimetableSchemaContainer(ISchoolToolApplication(None))


class TimetableAddForm(TimetableSetupViewBase):

    template = ViewPageTemplateFile('templates/timetable-add.pt')

    def getTerm(self):
        """Return the chosen term."""
        return ITerm(self.context)

    def addTimetable(self, timetable):
        chooser = INameChooser(self.context)
        name = chooser.chooseName('', timetable)
        self.context[name] = timetable

    def __call__(self):
        context = removeSecurityProxy(self.context)
        self.has_timetables = bool(self.ttschemas)
        if not self.has_timetables:
            return self.template()
        self.term = self.getTerm()
        self.ttschema = self.getSchema()
        self.ttkeys = ['.'.join((self.term.__name__, self.ttschema.__name__))]
        if 'SUBMIT' in self.request:
            timetable = self.ttschema.createTimetable(self.term)
            self.addTimetable(timetable)
            # TODO: find a better place to redirect to
            self.request.response.redirect(
                absoluteURL(self.context, self.request))
        return self.template()


# XXX: remove this class soon!
class SectionTimetableSetupView(TimetableSetupViewBase):

    __used_for__ = ISection

    template = ViewPageTemplateFile('templates/section-timetable-setup.pt')

    def singleSchema(self):
        return len(self.ttschemas.values()) == 1

    def addTimetable(self, timetable):
        tt_dict = ITimetables(self.context).timetables
        chooser = INameChooser(tt_dict)
        name = chooser.chooseName('', timetable)
        tt_dict[name] = timetable

    def getDays(self, ttschema):
        """Return the current selection.

        Returns a list of dicts with the following keys

            title   -- title of the timetable day
            periods -- list of timetable periods in that day

        Each period is represented by a dict with the following keys

            title    -- title of the period
            selected -- a boolean whether that period is in self.context's tt
                            for this shcema

        """
        timetable = self.getTimetable()

        def days(schema):
            for day_id, day in schema.items():
                yield {'title': day_id,
                       'periods': list(periods(day_id, day))}

        def periods(day_id, day):
            for period_id in day.periods:
                if timetable:
                    selected = timetable[day_id][period_id]
                else:
                    selected = False
                yield {'title': period_id,
                       'selected': selected}

        return list(days(ttschema))

    @property
    def consecutive_label(self):
        return _('Show consecutive periods as one period in journal')

    def __call__(self):
        self.has_timetables = bool(self.ttschemas)
        if not self.has_timetables:
            return self.template()
        self.ttschema = self.getSchema()
        self.term = ITerm(self.context)
        self.ttkeys = ['.'.join((self.term.__name__, self.ttschema.__name__))]
        self.days = self.getDays(self.ttschema)
        #XXX dumb, this doesn't space course names
        course_title = ''.join([course.title
                                for course in self.context.courses])
        section = removeSecurityProxy(self.context)
        timetable = ITimetables(section).lookup(self.term, self.ttschema)
        if timetable is None:
            self.consecutive_value = False
        else:
            self.consecutive_value = timetable.consecutive_periods_as_one

        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        if 'SAVE' in self.request:
            if timetable is None:
                timetable = self.ttschema.createTimetable(self.term)
                self.addTimetable(timetable)
            if self.request.get('consecutive') == 'on':
                timetable.consecutive_periods_as_one = True
            else:
                timetable.consecutive_periods_as_one = False

            for day_id, day in timetable.items():
                for period_id, period in list(day.items()):
                    if '.'.join((day_id, period_id)) in self.request:
                        if not period:
                            # XXX Resource list is being copied
                            # from section as this view can't do
                            # proper resource booking
                            act = TimetableActivity(title=course_title,
                                                    owner=section,
                                                    resources=section.resources)
                            day.add(period_id, act)
                    else:
                        if period:
                            for act in list(period):
                                day.remove(period_id, act)

            self.request.response.redirect(self.nextURL())

        return self.template()

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class TimetableEditView(form.EditForm, TimetableConflictMixin):
    template = ViewPageTemplateFile('templates/timetable-edit.pt')
    fields = field.Fields(ITimetable).select(
        'first', 'last',
        'consecutive_periods_as_one')
    fields['consecutive_periods_as_one'].widgetFactory = SingleCheckBoxFieldWidget

    def getDays(self):
        """Return the current selection.

        Returns a list of dicts with the following keys

            title   -- title of the timetable day
            periods -- list of timetable periods in that day

        Each period is represented by a dict with the following keys

            title    -- title of the period
            selected -- a boolean whether that period is in self.context's tt
                            for this shcema

        """
        ttschema = self.context.schooltt
        def days(schema):
            for day_id, day in schema.items():
                yield {'title': day_id,
                       'periods': list(periods(day_id, day))}

        def periods(day_id, day):
            for period_id in day.periods:
                selected = self.context[day_id][period_id]
                yield {'title': period_id,
                       'selected': selected}

        return list(days(ttschema))

    @property
    def timetable_dict(self):
        return self.context.__parent__

    def updateActions(self):
        super(TimetableEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        changes = self.applyChanges(data)
        section = removeSecurityProxy(self.context.__parent__.__parent__)
        course_title = ''.join([course.title
                                for course in section.courses])
        timetable_changed = bool(changes)
        for day_id, day in removeSecurityProxy(self.context).items():
            for period_id, period in list(day.items()):
                if '.'.join((day_id, period_id)) in self.request:
                    if not period:
                        # XXX Resource list is being copied
                        # from section as this view can't do
                        # proper resource booking
                        act = TimetableActivity(title=course_title,
                                                owner=section,
                                                resources=section.resources)
                        day.add(period_id, act)
                        timetable_changed = True
                else:
                    if period:
                        for act in list(period):
                            day.remove(period_id, act)
                            timetable_changed = True
        self.status = self.successMessage

        if timetable_changed:
            timetable = removeSecurityProxy(self.context)
            event = TimetableReplacedEvent(
                timetable.__parent__.__parent__, timetable.__name__,
                timetable, timetable)
            zope.event.notify(event)
        self.redirectToParent()

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        self.redirectToParent()

    def redirectToParent(self):
        self.request.response.redirect(
            absoluteURL(self.context.__parent__,
                        self.request))

    @property
    def ttschemas(self):
        return ITimetableSchemaContainer(ISchoolToolApplication(None))

    @property
    def has_timetables(self):
        return bool(self.ttschemas)


class TimetableSchemaVocabulary(TitledContainerItemVocabulary):

    @property
    def container(self):
        term = ITerm(self.context)
        return ITimetableSchemaContainer(term, {})


def timetableSchemaVocabularyFactory():
    return TimetableSchemaVocabulary


class ITimetableAddForm(Interface):
    """Form schema for ITerm add/edit views."""

    schooltt = zope.schema.Choice(
        title=_("School timetable"),
        source="schooltool.timetable.browser.timetable_schema_vocabulary",
        required=True,
    )

    first = zope.schema.Date(title=_("Apply from"))

    last = zope.schema.Date(title=_("Apply until"))


class TimetableAddView(form.AddForm, TimetableConflictMixin):

    template = ViewPageTemplateFile('templates/section-timetable-add.pt')
    fields = field.Fields(ITimetableAddForm)

    _object_added = None

    buttons = button.Buttons(
        button.Button('add', title=_('Add')),
        button.Button('cancel', title=_('Cancel')))

    @button.handler(buttons["add"])
    def handleAdd(self, action):
        return form.AddForm.handleAdd.func(self, action)

    @button.handler(buttons["cancel"])
    def handleCancel(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(TimetableAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def timetable_dict(self):
        return self.context

    @property
    def term(self):
        """Return the chosen term."""
        return ITerm(self.context)

    def create(self, data):
        schema = data['schooltt']
        timetable = schema.createTimetable(self.term)
        timetable.first = data['first']
        timetable.last = data['last']
        return timetable

    def add(self, timetable):
        chooser = INameChooser(self.context)
        name = chooser.chooseName('', timetable)
        self.context[name] = timetable
        self._object_added = timetable

    def nextURL(self):
        if self._object_added is not None:
            return absoluteURL(self._object_added, self.request)
        return absoluteURL(self.context, self.request)


TimetableAdd_default_first = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.term.first,
    view=TimetableAddView,
    field=ITimetableAddForm['first']
    )


TimetableAdd_default_last = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.term.last,
    view=TimetableAddView,
    field=ITimetableAddForm['last']
    )


class TimetableFormValidator(validator.InvariantsValidator):

    def _formatTitle(self, object):
        if object is None:
            return None
        def dateTitle(date):
            if date is None:
                return '...'
            formatter = getMultiAdapter((date, self.request), name='mediumDate')
            return formatter()
        return u"%s (%s - %s)" % (
            object.title, dateTitle(object.first), dateTitle(object.last))

    def validateObject(self, timetable):
        errors = super(TimetableFormValidator, self).validateObject(timetable)
        try:
            dr = DateRange(timetable.first, timetable.last)
            timetable_dict = self.view.timetable_dict
            term = ITerm(timetable_dict)
            try:
                other_timetables = timetable_dict.values()
                if getattr(timetable, '__name__', None) is not None:
                    other_timetables = [tt for tt in other_timetables
                                        if tt.__name__ != timetable.__name__]
                validateAgainstOthers(
                    timetable.schooltt, timetable.first, timetable.last,
                    other_timetables)
            except TimetableOverlapError, e:
                for tt in e.overlapping:
                    errors += (Invalid(
                        u"%s %s" % (
                            _("Timetable conflicts with another:"),
                            self._formatTitle(tt))), )
            try:
                validateAgainstTerm(
                    timetable.schooltt, timetable.first, timetable.last,
                    term)
            except TimetableOverflowError, e:
                errors += (Invalid(u"%s %s" % (
                    _("Timetable does not fit in term"),
                    self._formatTitle(term))), )
        except ValueError, e:
            errors += (Invalid(_("Timetable must begin before it ends.")), )
        except validator.NoInputData:
            return errors
        return errors


validator.WidgetsValidatorDiscriminators(
    TimetableFormValidator,
    view=TimetableEditView,
    schema=getSpecification(ITimetable, force=True))


validator.WidgetsValidatorDiscriminators(
    TimetableFormValidator,
    view=TimetableAddView,
    schema=getSpecification(ITimetableAddForm, force=True))


class SpecialDayView(BrowserView):
    """The view for changing the periods for a particular day.

    The typical use case: some periods get shortened or and some get
    cancelled altogether if some special event is held at noon.
    """

    select_template = ViewPageTemplateFile('templates/specialday_select.pt')
    form_template = ViewPageTemplateFile('templates/specialday_change.pt')

    error = None
    field_errors = None
    date = None
    term = None

    def delta(self, start, end):
        """
        Returns a timedelta between two times

            >>> from datetime import time, timedelta
            >>> view = SpecialDayView(None, None)
            >>> view.delta(time(11, 10), time(12, 20))
            datetime.timedelta(0, 4200)

        If a result is negative, it is 'wrapped around':

            >>> view.delta(time(11, 10), time(10, 10)) == timedelta(hours=23)
            True
        """
        today = datetime.date.today()
        dtstart = datetime.datetime.combine(today, start)
        dtend = datetime.datetime.combine(today, end)
        delta = dtend - dtstart
        if delta < datetime.timedelta(0):
            delta += datetime.timedelta(1)
        return delta

    def extractPeriods(self):
        """Return a list of three-tuples with period titles, tstarts,
        durations.

        If errors are encountered in some fields, the names of the
        fields get added to field_errors.
        """
        model = self.context.model
        result = []
        for info in model.originalPeriodsInDay(self.term, self.context,
                                               self.date):
            period_id, tstart, duration = info
            start_name = period_id + '_start'
            end_name = period_id + '_end'
            if (start_name in self.request and end_name in self.request
                and (self.request[start_name] or self.request[end_name])):
                start = end = None
                try:
                    start = parse_time(self.request[start_name])
                except ValueError:
                    pass
                try:
                    end = parse_time(self.request[end_name])
                except ValueError:
                    pass
                if start is None:
                    self.field_errors.append(start_name)
                if end is None:
                    self.field_errors.append(end_name)
                elif start is not None:
                    duration = self.delta(start, end)
                    result.append((period_id, start, duration))

        return result

    def update(self):
        """Read and validate form data, and update model if necessary.

        Also choose the correct template to render.
        """
        self.field_errors = []
        self.template = self.select_template
        if 'CANCEL' in self.request:
            self.request.response.redirect(
                absoluteURL(self.context, self.request))
            return
        if 'date' in self.request:
            try:
                self.date = parse_date(self.request['date'])
            except ValueError:
                self.error = _("Invalid date. Please use YYYY-MM-DD format.")
            else:
                self.term = getTermForDate(self.date)
                if self.term is None:
                    self.error = _("The date does not belong to any term.")
                    self.date = None
        if self.date:
            self.template = self.form_template
        if self.date and 'SUBMIT' in self.request:
            daytemplate = []
            for title, start, duration in self.extractPeriods():
                daytemplate.append((title, SchooldaySlot(start, duration)))
            if self.field_errors:
                self.error = _('Some values were invalid.'
                               '  They are highlighted in red.')
            else:
                exceptionDays = removeSecurityProxy(
                    self.context.model.exceptionDays)
                exceptionDays[self.date] = daytemplate
                self.request.response.redirect(
                    absoluteURL(self.context, self.request))

    def timeplustd(self, t, td):
        """Add a timedelta to time.

        datetime authors are cowards.

            >>> view = SpecialDayView(None, None)
            >>> from datetime import time, timedelta
            >>> view.timeplustd(time(10,0), timedelta(0, 5))
            datetime.time(10, 0, 5)
            >>> view.timeplustd(time(23,0), timedelta(0, 3660))
            datetime.time(0, 1)
        """
        dt = datetime.datetime.combine(datetime.date.today(), t)
        dt += td
        return dt.time()

    def getPeriods(self):
        """A helper method that returns a list of tuples of:

        (period_title, orig_start, orig_end, actual_start, actual_end)
        """
        model = self.context.model
        result = []
        actual_times = {}
        for info in model.periodsInDay(self.term, self.context, self.date):
            period_id, tstart, duration = info
            endtime = self.timeplustd(tstart, duration)
            actual_times[period_id] = (tstart.strftime("%H:%M"),
                                       endtime.strftime("%H:%M"))
        for info in model.originalPeriodsInDay(self.term, self.context,
                                                 self.date):
            period_id, tstart, duration = info
            # datetime authors are cowards
            endtime = self.timeplustd(tstart, duration)
            result.append((period_id,
                           tstart.strftime("%H:%M"),
                           endtime.strftime("%H:%M")) +
                          actual_times.get(period_id, ('', '')))
        return result

    def __call__(self):
        self.update()
        return self.template()


class SectionTimetablesViewBase(TimetableSetupViewBase):

    def formatTimetableForTemplate(self, timetable):
        timetable = removeSecurityProxy(timetable)
        has_activities = False
        days = []
        for day_id, day in timetable.items():
            periods = []
            for period, activities in day.items():
                periods.append({
                    'title': period,
                    'activities': " / ".join(
                        sorted([a.title for a in activities])),
                    })
                has_activities |= bool(len(activities))
            days.append({
                'title': day_id,
                'periods': periods,
                })
        return {
            'timetable': timetable,
            'has_activities': has_activities,
            'days': days,
            }


class SectionTimetablesView(SectionTimetablesViewBase):

    __used_for__ = ITimetableDict
    template = ViewPageTemplateFile('templates/section-timetable-view.pt')

    @property
    def owner(self):
        # XXX: make this property obsolete as soon as possible
        return self.context.__parent__

    @property
    def term(self):
        return ITerm(self.owner)

    @property
    def school_year(self):
        return ISchoolYear(self.term)

    @property
    def timetables(self):
        timetables = sorted(self.context.values(),
                            key=lambda tt: (tt.first, tt.title))
        result = []
        for timetable in timetables:
            result.append(self.formatTimetableForTemplate(timetable))
        return result

    def hasTimetables(self):
        return bool(self.context)

    def __call__(self):
        return self.template()


class SectionTimetableDeleteView(SectionTimetablesViewBase):

    __used_for__ = ITimetableDict
    template = ViewPageTemplateFile('templates/confirm-timetable-delete.pt')

    def owner(self):
        # XXX: make this property obsolete as soon as possible
        return self.context.__parent__

    @property
    def term(self):
        return ITerm(self.owner)

    @property
    def school_year(self):
        return ISchoolYear(self.term)

    @property
    def timetable(self):
        name = self.request['timetable']
        if name not in self.context:
            return None
        timetable = self.context[name]
        return self.formatTimetableForTemplate(timetable)

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def __call__(self):
        timetable = self.timetable
        if 'CONFIRM' in self.request and timetable is not None:
            del self.context[timetable['timetable'].__name__]
            self.request.response.redirect(self.nextURL())
        elif 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return self.template()

