#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Timetabling Term views.
"""
import datetime
import itertools

from zope.component import adapts
from zope.interface.exceptions import Invalid
from zope.interface import implements
from zope.interface import Interface
from zope.schema import TextLine, Date
from zope.schema import ValidationError
from zope.container.interfaces import INameChooser
from zope.publisher.browser import BrowserView
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.checker import canAccess
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form.util import getSpecification
from z3c.form.validator import NoInputData
from z3c.form.validator import WidgetsValidatorDiscriminators
from z3c.form import form, field, button
from z3c.form.validator import SimpleFieldValidator
from z3c.form.validator import WidgetValidatorDiscriminators
from z3c.form.validator import InvariantsValidator

from schooltool.app.browser.cal import month_names
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.calendar.utils import parse_date
from schooltool.calendar.utils import next_month, week_start
from schooltool.term.interfaces import ITerm
from schooltool.term.term import validateTermsForOverlap
from schooltool.term.term import Term
from schooltool.skin import flourish
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.interfaces import TermOverlapError
from schooltool.common import IDateRange
from schooltool.common import DateRange
from schooltool.common import SchoolToolMessage as _
from schooltool.common.inlinept import InheritTemplate


class ITermForm(Interface):
    """Form schema for ITerm add/edit views."""

    title = TextLine(title=_("Title"))

    first = Date(title=_("Start date"))

    last = Date(title=_("End date"))


class TermFormAdapter(object):
    implements(ITermForm)
    adapts(ITerm)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __setattr__(self, name, value):
        setattr(self.context, name, value)

    def __getattr__(self, name):
        return getattr(self.context, name)


class TermView(BrowserView):
    """Browser view for terms."""

    __used_for__ = ITerm

    def calendar(self):
        """Prepare the calendar for display.

        Returns a structure composed of lists and dicts, see `TermRenderer`
        for more details.
        """
        return TermRenderer(self.context).calendar()


class TermFormBase(object):

    @property
    def showNext(self):
        return self.preview_term is None

    @property
    def showRefresh(self):
        return not self.showNext

    def setHolidays(self, term):
        term.addWeekdays(0, 1, 2, 3, 4, 5, 6)
        holidays = self.request.form.get('holiday', [])
        if not isinstance(holidays, list):
            holidays = [holidays]
        for holiday in holidays:
            try:
                term.remove(parse_date(holiday))
            except ValueError:
                pass # ignore ill-formed or out-of-range dates
        toggle = [n for n in range(7) if ('TOGGLE_%d' % n) in self.request]
        if toggle:
            term.toggleWeekdays(*toggle)


class TermAddForm(form.AddForm, TermFormBase):
    """Add form for school terms."""

    label = _("Add new term")
    template = ViewPageTemplateFile('templates/term_add.pt')

    fields = field.Fields(ITermForm)

    @property
    def preview_term(self):
        data, errors = self.extractData()
        self.updateWidgets()
        if errors:
            return None
        term = Term(data['title'], data['first'], data['last'])
        self.setHolidays(term)
        return TermRenderer(term).calendar()

    def updateActions(self):
        super(TermAddForm, self).updateActions()
        for button_id, cls in zip(['next', 'refresh', 'add'],
                                  ['button-ok', 'button-neutral', 'button-ok']):
            button = self.actions.get(button_id)
            if button is not None:
                button.addClass(cls)
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Refresh'), name='refresh',
                             condition=lambda form: form.showRefresh)
    def handleRefresh(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._finishedAdd = False

    @button.buttonAndHandler(_('Next'), name='next',
                             condition=lambda form: form.showNext)
    def next(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._finishedAdd = False

    @button.buttonAndHandler(_('Add term'), name='add',
                             condition=lambda form: form.showRefresh)
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        obj = self.createAndAdd(data)
        if obj is not None:
            # mark only as finished if we get the new object
            self._finishedAdd = True

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def create(self, data):
        term = Term(data['title'], data['first'], data['last'])
        form.applyChanges(self, term, data)
        self.setHolidays(term)
        return term

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def add(self, term):
        """Add `term` to the container."""
        chooser = INameChooser(self.context)
        name = chooser.chooseName("", term)
        self.context[name] = term
        return term


class FlourishTermAddView(flourish.form.AddForm, TermAddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = 'Term Details'

    @property
    def title(self):
        return self.context.title

    @button.buttonAndHandler(_('Next'), name='next',
                             condition=lambda form: form.showNext)
    def next(self, action):
        super(FlourishTermAddView, self).next.func(self, action)

    @button.buttonAndHandler(_('Add term'), name='add',
                             condition=lambda form: form.showRefresh)
    def handleAdd(self, action):
        super(FlourishTermAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(ISchoolToolApplication(None), self.request) + '/terms'
        self.request.response.redirect(url)


class TermEditForm(form.EditForm, TermFormBase):
    """Edit form for basic person."""
    template = ViewPageTemplateFile('templates/term_add.pt')

    fields = field.Fields(ITermForm)

    @property
    def preview_term(self):
        data, errors = self.extractData()
        self.updateWidgets()
        if errors:
            term = self.context
        else:
            term = Term(data['title'], data['first'], data['last'])
            self.setHolidays(term)
        return TermRenderer(term).calendar()

    def updateActions(self):
        super(TermEditForm, self).updateActions()
        for button_id, cls in zip(['refresh', 'apply'],
                                  ['button-neutral', 'button-ok']):
            button = self.actions.get(button_id)
            if button is not None:
                button.addClass(cls)
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Refresh'), name='refresh',
                             condition=lambda form: form.showRefresh)
    def handleRefresh(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self._finishedAdd = False

    def applyChanges(self, data):
        changes = super(TermEditForm, self).applyChanges(data)
        self.setHolidays(self.context)
        return changes

    @button.buttonAndHandler(_('Save changes'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        changes = self.applyChanges(data)
        self.status = self.successMessage

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @property
    def label(self):
        return _(u'Change information for ${term_title}',
                 mapping={'term_title': self.context.title})


class AddTermFormValidator(InvariantsValidator):

    def validateObject(self, obj):
        errors = super(AddTermFormValidator, self).validateObject(obj)
        try:
            dr = DateRange(obj.first, obj.last)
            try:
                validateTermsForOverlap(self.view.context, dr, None)
            except TermOverlapError, e:
                errors += (e, )
        except ValueError, e:
            errors += (Invalid(_("Term must begin before it ends.")), )
        except NoInputData:
            return errors
        return errors

WidgetsValidatorDiscriminators(
    AddTermFormValidator,
    view=TermAddForm,
    schema=getSpecification(ITermForm, force=True))


class EditTermFormValidator(InvariantsValidator):

    def validateObject(self, obj):
        errors = super(EditTermFormValidator, self).validateObject(obj)
        try:
            dr = DateRange(obj.first, obj.last)
            try:
                validateTermsForOverlap(self.view.context.__parent__, dr,
                                        self.view.context)
            except TermOverlapError, e:
                errors += (e, )
        except ValueError, e:
            errors += (Invalid(_("Term must begin before it ends.")), )
        except NoInputData:
            return errors
        return errors

WidgetsValidatorDiscriminators(
    EditTermFormValidator,
    view=TermEditForm,
    schema=getSpecification(ITermForm, force=True))


class DateOutOfYearBounds(ValidationError):
    """Date is not in the school year."""


class TermBoundsValidator(SimpleFieldValidator):

    def validate(self, value):
        super(TermBoundsValidator, self).validate(value)
        from schooltool.schoolyear.interfaces import ISchoolYear
        if ISchoolYear.providedBy(self.view.context):
            sy = self.view.context
        else:
            sy = self.view.context.__parent__

        if value not in IDateRange(sy):
            raise DateOutOfYearBounds(self.view.context, value)


class FirstTermBoundsValidator(TermBoundsValidator):
    pass

WidgetValidatorDiscriminators(
    FirstTermBoundsValidator,
    field=ITermForm['first'])


class LastTermBoundsValidator(TermBoundsValidator):
    pass

WidgetValidatorDiscriminators(
    LastTermBoundsValidator,
    field=ITermForm['last'])


class TermRenderer(object):
    """Helper for rendering ITerms."""

    first_day_of_week = 0 # Monday  TODO: get from IApplicationPreferences

    def __init__(self, term):
        self.term = term

    def calendar(self):
        """Prepare the calendar for display.

        Returns a list of month dicts (see `month`).
        """
        calendar = []
        date = self.term.first
        counter = itertools.count(1)
        while date <= self.term.last:
            start_of_next_month = next_month(date)
            end_of_this_month = start_of_next_month - datetime.date.resolution
            maxdate = min(self.term.last, end_of_this_month)
            calendar.append(self.month(date, maxdate, counter))
            date = start_of_next_month
        return calendar

    def month(self, mindate, maxdate, counter):
        """Prepare one month for display.

        Returns a dict with these keys:

            month   -- title of the month
            year    -- the year number
            weeks   -- a list of week dicts in this month (see `week`)

        """
        assert (mindate.year, mindate.month) == (maxdate.year, maxdate.month)
        weeks = []
        date = week_start(mindate, self.first_day_of_week)
        while date <= maxdate:
            weeks.append(self.week(date, mindate, maxdate, counter))
            date += datetime.timedelta(days=7)
        return {'month': month_names[mindate.month],
                'year': mindate.year,
                'weeks': weeks}

    def week(self, start_of_week, mindate, maxdate, counter):
        """Prepare one week of a Term for display.

        `start_of_week` is the date when the week starts.

        `mindate` and `maxdate` are used to indicate which month (or part of
        the month) interests us -- days in this week that fall outside
        [mindate, maxdate] result in a dict containing None values for all
        keys.

        `counter` is an iterator that returns indexes for days
        (itertools.count(1) is handy for this purpose).

        `term` is an ITerm that indicates which days are schooldays,
        and which are holidays.

        Returns a dict with these keys:

            number  -- week number
            days    -- a list of exactly seven dicts

        Each day dict has the following keys

            date    -- date as a string (YYYY-MM-DD)
            number  -- day of month
                       (None when date is outside [mindate, maxdate])
            index   -- serial number of this day (used in Javascript)
            class   -- CSS class ('holiday' or 'schoolday')
            checked -- True for holidays, False for schooldays
            onclick -- onclick event handler that calls toggle(index)

        """
        # start_of_week will be a Sunday or a Monday.  If it is a Sunday,
        # we want to take the ISO week number of the following Monday.  If
        # it is a Monday, we won't break anything by taking the week number
        # of the following Tuesday.
        week_no = (start_of_week + datetime.date.resolution).isocalendar()[1]
        date = start_of_week
        days = []
        for day in range(7):
            if mindate <= date <= maxdate:
                index = counter.next()
                checked = not self.term.isSchoolday(date)
                css_class = checked and 'holiday' or 'schoolday'
                days.append({'number': date.day, 'class': css_class,
                             'date': date.strftime('%Y-%m-%d'),
                             'index': index, 'checked': checked,
                             'onclick': 'javascript:toggle(%d)' % index})
            else:
                days.append({'number': None, 'class': None, 'index': None,
                             'onclick': None, 'checked': None, 'date': None})
            date += datetime.date.resolution
        return {'number': week_no,
                'days': days}


class FlourishTermsView(flourish.page.Page):

    def years(self):
        syc = ISchoolYearContainer(self.context)
        for year in reversed(tuple(syc.values())):
            result = {
                'obj': year,
                'first': year.first,
                'last': year.last,
                'terms': [],
                'empty': not bool(tuple(year.values())),
                'canModify': canAccess(year, '__delitem__'),
                'add': 'add.' + year.__name__,
                'addurl': absoluteURL(year, self.request) + '/add.html',
                }
            for term in reversed(tuple(year.values())):
                result['terms'].append(term)
            yield result

    def update(self):
        for year in self.years():
            if year['add'] in self.request:
                self.request.response.redirect(year['addurl'])

