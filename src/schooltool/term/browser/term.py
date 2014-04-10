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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Timetabling Term views.
"""
import datetime
import itertools

from zope.component import adapts, getMultiAdapter
from zope.interface.exceptions import Invalid
from zope.interface import implements, directlyProvides
from zope.interface import Interface
from zope.schema import TextLine, Date
from zope.schema import ValidationError
from zope.container.interfaces import INameChooser
from zope.i18n import translate
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
from z3c.form.interfaces import DISPLAY_MODE
from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn

import schooltool.skin.flourish.breadcrumbs
from schooltool import table
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.browser.cal import month_names
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.calendar.utils import parse_date
from schooltool.calendar.utils import next_month, week_start
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.term.interfaces import ITerm, ITermContainer
from schooltool.term.term import validateTermsForOverlap
from schooltool.term.term import Term
from schooltool.skin import flourish
from schooltool.skin.dateformatter import DateFormatterMediumView
from schooltool.schoolyear.interfaces import TermOverlapError
from schooltool.schoolyear.interfaces import ISchoolYear
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


class FlourishTermView(flourish.page.Page, TermView, ActiveSchoolYearContentMixin):
    """flourish view of a term."""

    @property
    def title(self):
        return self.context.__parent__.title

    @property
    def subtitle(self):
        return self.context.title

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    @property
    def details(self):
        view = FlourishTermDetails(self.context, self.request, None)
        view.update()
        return view

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    def done_link(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='terms')

class FlourishTermDetails(flourish.form.FormViewlet):

    fields = field.Fields(ITerm).select(
        '__name__', 'title', 'first', 'last')
    mode = DISPLAY_MODE

    def updateWidgets(self, *args, **kw):
        super(FlourishTermDetails, self).updateWidgets(*args, **kw)
        self.widgets['first'].label = _('First day')
        self.widgets['last'].label = _('Last day')


class FlourishTermActionLinks(flourish.page.RefineLinksViewlet):
    """Term action links viewlet."""


class FlourishTermsAddLinks(flourish.page.RefineLinksViewlet):
    """Term action links viewlet."""


class FlourishTermDeleteLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Delete ${term}',
                  mapping={'term': self.context.title})
        return translate(title, context=self.request)


class FlourishTermDeleteView(flourish.form.DialogForm, form.EditForm):
    """View used for confirming deletion of a schoolyear."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        url = '%s/delete.html?delete.%s&CONFIRM' % (
            absoluteURL(self.context.__parent__, self.request),
            self.context.__name__.encode('utf-8'))
        self.request.response.redirect(url)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishTermDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishTermContainerDeleteView(flourish.containers.ContainerDeleteView, ActiveSchoolYearContentMixin):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    def nextURL(self):
        if 'CONFIRM' in self.request:
            app = ISchoolToolApplication(None)
            return self.url_with_schoolyear_id(app, view_name='terms')
        return super(flourish.containers.ContainerDeleteView, self).nextURL(self)


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


class FlourishTermAddView(flourish.form.AddForm, TermAddForm, ActiveSchoolYearContentMixin):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Term Details')

    @property
    def title(self):
        return self.context.title

    @button.buttonAndHandler(_('Refresh'), name='refresh',
                             condition=lambda form: form.showRefresh)
    def handleRefresh(self, action):
        super(FlourishTermAddView, self).handleRefresh.func(self, action)

    @button.buttonAndHandler(_('Next'), name='next',
                             condition=lambda form: form.showNext)
    def next(self, action):
        super(FlourishTermAddView, self).next.func(self, action)

    @button.buttonAndHandler(_('Submit'), name='add',
                             condition=lambda form: form.showRefresh)
    def handleAdd(self, action):
        super(FlourishTermAddView, self).handleAdd.func(self, action)

    def create(self, data):
        term = Term(data['title'], data['first'], data['last'])
        form.applyChanges(self, term, data)
        self.setHolidays(term)
        self._term = term
        return term

    def nextURL(self):
        return absoluteURL(self._term, self.request)

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        app = ISchoolToolApplication(None)
        url = self.url_with_schoolyear_id(app, view_name='terms')
        self.request.response.redirect(url)

    def dateString(self, date):
        return DateFormatterMediumView(date, self.request)()

    def updateWidgets(self):
        super(FlourishTermAddView, self).updateWidgets()
        description = _(u'The year starts ${year_start}',
            mapping={'year_start': self.dateString(self.context.first)})
        self.widgets['first'].field.description = description
        description = _(u'The year ends ${year_end}',
            mapping={'year_end': self.dateString(self.context.last)})
        self.widgets['last'].field.description = description


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


class FlourishTermEditView(flourish.form.Form, TermEditForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None

    @property
    def title(self):
        return self.context.title

    @property
    def legend(self):
        return _(u'Change information for ${term_title}',
                 mapping={'term_title': self.context.title})

    @button.buttonAndHandler(_('Refresh'), name='refresh',
                             condition=lambda form: form.showRefresh)
    def handleRefresh(self, action):
        super(FlourishTermEditView, self).handleRefresh.func(self, action)

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishTermEditView, self).handleApply.func(self, action)
        if self.status != self.formErrorsMessage:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        super(FlourishTermEditView, self).handle_cancel_action.func(self,
            action)


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


class FlourishInvalidDateRangeError(ValidationError):
    __doc__ = _('Term must begin before it ends.')


class FlourishOverlapError(ValidationError):
    __doc__ = _('Date range overlaps another term.')


class FlourishOverlapValidator(TermBoundsValidator):

    def validate(self, value):
        # XXX: hack to display the overlap error next to the widget!
        super(FlourishOverlapValidator, self).validate(value)
        last_widget = self.view.widgets['last']
        last_value = self.request.get(last_widget.name)
        try:
            last_value = last_widget._toFieldValue(last_value)
        except:
            return
        try:
            dr = DateRange(value, last_value)
        except:
            raise FlourishInvalidDateRangeError()
        try:
            validateTermsForOverlap(self.container, dr, self.term)
        except TermOverlapError, e:
            raise FlourishOverlapError()


class FlourishOverlapAddValidator(FlourishOverlapValidator):
    term = None

    @property
    def container(self):
        return self.context


class FlourishOverlapEditValidator(FlourishOverlapValidator):

    @property
    def term(self):
        return self.context

    @property
    def container(self):
        return self.context.__parent__


WidgetValidatorDiscriminators(FlourishOverlapAddValidator,
                              view=FlourishTermAddView,
                              field=ITermForm['first'])


WidgetValidatorDiscriminators(FlourishOverlapEditValidator,
                              view=FlourishTermEditView,
                              field=ITermForm['first'])


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


class FlourishTermsView(flourish.page.Page, ActiveSchoolYearContentMixin):

    @property
    def title(self):
        year = self.schoolyear
        if year is not None:
            return _('Terms for ${schoolyear}',
                     mapping={'schoolyear': year.title})

    def year(self):
        year = self.schoolyear
        if year is not None:
            return {
                'title': _(u'School Year: ${year_title}',
                         mapping={'year_title': year.title}),
                'first': year.first,
                'last': year.last,
                'empty': not bool(tuple(year.values())),
                'canModify': canAccess(year, '__delitem__'),
                'addurl': absoluteURL(year, self.request) + '/add.html',
                'alt': _(u'Add a new term to ${year_title}',
                         mapping={'year_title': year.title}),
                }

    def terms(self):
        year = self.schoolyear
        if year is not None:
            for term in reversed(tuple(year.values())):
                yield {
                    'obj': term,
                    'first': term.first,
                    'last': term.last,
                    }


class TermsTertiaryNavigationManager(
    flourish.page.TertiaryNavigationManager,
    ActiveSchoolYearContentMixin):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        active = self.schoolyear
        schoolyears = active.__parent__ if active is not None else {}
        for schoolyear in schoolyears.values():
            url = '%s/terms?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class FlourishManageYearsOverview(flourish.page.Content,
                                  ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_years_overview.pt')

    @property
    def terms(self):
        terms = ITermContainer(self.schoolyear, None)
        if terms is not None:
            return sorted(terms.values(), key=lambda t:t.first)

    def terms_url(self):
        return self.url_with_schoolyear_id(self.context, view_name='terms')


class TermContainerBreadcrumb(flourish.breadcrumbs.Breadcrumbs, ActiveSchoolYearContentMixin):

    title = _('Terms')

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    @property
    def url(self):
        if not self.checkPermission():
            return None
        url = self.url_with_schoolyear_id(self.crumb_parent, view_name='terms')
        return url

    @property
    def crumb_parent(self):
        return ISchoolToolApplication(None)


class TermAddLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        year = self.view.schoolyear
        if year is None or not flourish.canEdit(year):
            return False
        return super(TermAddLinkViewlet, self).enabled

    @property
    def url(self):
        year = self.view.schoolyear
        if year is None:
            return None
        return '%s/%s' % (absoluteURL(year, self.request), 'add.html')


def date_cell_formatter(value, item, formatter):
    view = getMultiAdapter((value, formatter.request), name='mediumDate')
    return view()


class SchoolYearTermsTable(table.ajax.Table):

    def columns(self):
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        starts = GetterColumn(
            name='starts',
            title=_(u"First Day"),
            getter=lambda i, f: i.first,
            cell_formatter=date_cell_formatter,
            subsort=True)
        ends = GetterColumn(
            name='ends',
            title=_(u"Last Day"),
            getter=lambda i, f: i.last,
            cell_formatter=date_cell_formatter,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        directlyProvides(starts, ISortableColumn)
        directlyProvides(ends, ISortableColumn)
        return [title, starts, ends]

    def sortOn(self):
        return (("starts", False),)
