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
Timetabling Schema views.
"""
import urllib

import zope.schema
import zope.lifecycleevent
from zope.proxy import sameProxiedObjects
from zope.component import getMultiAdapter
from zope.component import adapts
from zope.component import getUtility
from zope.container.interfaces import INameChooser
from zope.interface import Interface, implements
from zope.intid.interfaces import IIntIds
from zope.i18n import translate
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IBrowserView
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from z3c.form import form, field, button, widget, validator
from z3c.form.util import getSpecification
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget

import schooltool.skin.flourish.page
from schooltool.skin import flourish
from schooltool.skin.flourish.content import ContentProvider
from schooltool.common import format_time_range
from schooltool.table.table import simple_form_key
from schooltool.timetable.interfaces import ITimetable, ITimetableContainer
from schooltool.timetable.interfaces import ISelectedPeriodsSchedule
from schooltool.timetable.interfaces import IHaveSchedule, IScheduleContainer
from schooltool.timetable.browser.app import getActivityVocabulary
from schooltool.timetable.browser.schedule import FlourishConfirmDeleteView
from schooltool.timetable.timetable import SelectedPeriodsSchedule
from schooltool.term.interfaces import ITerm

from schooltool.common import SchoolToolMessage as _


class IRenderDayTableCells(IBrowserView):
    def renderCells(schedule, day, item):
        """Return contents for two <td> cells: (title_html, value_html)
           Or return None if don't want to render the cell.
        """


class DayTemplatesTable(ContentProvider):

    @property
    def days(self):
        return self.context.templates.values()

    def makeTable(self):
        days = self.days
        table = {'header': [day.title for day in days]}

        def to_dict(item):
            return item and {'title': item[0], 'value': item[1]} or {}

        cols = []
        for day in days:
            cells = [self.view.renderCells(self.context, day, item)
                     for item in day.values()]
            cols.append(map(to_dict, filter(None, cells)))

        max_rows = max([len(cells) for cells in cols])
        cols = [cells + [{}]*(max_rows-len(cells)) for cells in cols]

        if len(cols) == 1:
            table['rows'] = [(col,) for col in cols[0]]
        else:
            table['rows'] = map(None, *cols)
        ncols = len(cols) or 1
        table['col_width'] ='%d%%' % (100 / ncols);
        table['th_width'] = '%d%%' % (10 / ncols);
        table['td_width'] = '%d%%' % (90 / ncols);
        return table


class TimetableView(BrowserView):
    implements(IRenderDayTableCells)
    adapts(ITimetable, IBrowserRequest)

    template = ViewPageTemplateFile("templates/timetable.pt")

    activity_vocabulary = None

    def __init__(self, *args, **kw):
        BrowserView.__init__(self, *args, **kw)
        self.activity_vocabulary = getActivityVocabulary(self.context)

    def activityTitle(self, activity_type):
        if activity_type in self.activity_vocabulary:
            term = self.activity_vocabulary.getTerm(activity_type)
            return term.title
        return None

    def renderCells(self, schedule, day, item):
        if sameProxiedObjects(schedule, self.context.periods):
            period = item
            return (period.title,
                    self.activityTitle(period.activity_type) or '')
        if sameProxiedObjects(schedule, self.context.time_slots):
            slot = item
            return (format_time_range(slot.tstart, slot.duration),
                    self.activityTitle(slot.activity_type) or '')
        return None

    def __call__(self):
        return self.template()


class FlourishTimetableView(flourish.page.WideContainerPage, TimetableView):
    pass


#class SimpleTimetableSchemaAdd(BrowserView):
#    """A simple timetable schema definition view"""
#
#    _nrperiods = 9
#
#    day_ids = (_("Monday"),
#               _("Tuesday"),
#               _("Wednesday"),
#               _("Thursday"),
#               _("Friday"),
#               )
#
#    error = None
#
#    template = ViewPageTemplateFile('templates/simpletts.pt')
#
#    def __init__(self, content, request):
#        BrowserView.__init__(self, content, request)
#        self._schema = {}
#        self._schema['title'] = TextLine(__name__='title', title=_(u"Title"))
#        for nr in range(1, self._nrperiods + 1):
#            pname = 'period_name_%s' % nr
#            pstart = 'period_start_%s' % nr
#            pfinish = 'period_finish_%s' % nr
#            self._schema[pname] = TextLine(__name__=pname,
#                                           title=u"Period title",
#                                           required=False)
#            self._schema[pstart] = TextLine(__name__=pstart,
#                                            title=u"Period start time",
#                                            required=False)
#            self._schema[pfinish] = TextLine(__name__=pfinish,
#                                             title=u"Period finish time",
#                                             required=False)
#        setUpWidgets(self, self._schema, IInputWidget,
#                     initial={'title': 'default'})
#
#    def _setError(self, name, error=RequiredMissing()):
#        """Set an error on a widget."""
#        # XXX Touching widget._error is bad, see
#        #     http://dev.zope.org/Zope3/AccessToWidgetErrors
#        # The call to setRenderedValue is necessary because
#        # otherwise _getFormValue will call getInputValue and
#        # overwrite _error while rendering.
#        widget = getattr(self, name + '_widget')
#        widget.setRenderedValue(widget._getFormValue())
#        if not IWidgetInputError.providedBy(error):
#            error = WidgetInputError(name, widget.label, error)
#        widget._error = error
#
#    def getPeriods(self):
#        try:
#            data = getWidgetsData(self, self._schema)
#        except WidgetsError:
#            return []
#
#        result = []
#        for nr in range(1, self._nrperiods + 1):
#            pname = 'period_name_%s' % nr
#            pstart = 'period_start_%s' % nr
#            pfinish = 'period_finish_%s' % nr
#            if data.get(pstart) or data.get(pfinish):
#                try:
#                    start, duration = parse_time_range(
#                        "%s-%s" % (data[pstart], data[pfinish]))
#                except ValueError:
#                    self.error = _('Please use HH:MM format for period '
#                                   'start and end times')
#                    continue
#                name = data[pname]
#                if not name:
#                    name = data[pstart]
#                result.append((name, start, duration))
#        return result
#
#    def createSchema(self, periods):
#        daytemplate = SchooldayTemplate()
#        for title, start, duration in periods:
#            daytemplate.add(SchooldaySlot(start, duration))
#
#        factory = getUtility(ITimetableModelFactory, 'WeeklyTimetableModel')
#        model = factory(self.day_ids, {None: daytemplate})
#        app = ISchoolToolApplication(None)
#        tzname = IApplicationPreferences(app).timezone
#        schema = TimetableSchema(self.day_ids, timezone=tzname)
#        for day_id in self.day_ids:
#            schema[day_id] = TimetableSchemaDay(
#                [title for title, start, duration in periods])
#        schema.model = model
#        return schema
#
#    def __call__(self):
#        try:
#            data = getWidgetsData(self, self._schema)
#        except WidgetsError:
#            return self.template()
#
#        if 'CANCEL' in self.request:
#            self.request.response.redirect(
#                absoluteURL(self.context, self.request))
#        elif 'CREATE' in self.request:
#            periods = self.getPeriods()
#            if self.error:
#                return self.template()
#
#            if not periods:
#                self.error = _('You must specify at least one period.')
#                return self.template()
#
#            schema = self.createSchema(periods)
#            schema.title = data['title']
#
#            nameChooser = INameChooser(self.context)
#            name = nameChooser.chooseName('', schema)
#
#            self.context[name] = schema
#            self.request.response.redirect(
#                absoluteURL(self.context, self.request))
#
#        return self.template()



#class TimetableSchemaXMLView(BrowserView):
#    """View for ITimetableSchema"""
#
#    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
#            'Friday', 'Saturday', 'Sunday']
#
#    template = ViewPageTemplateFile("templates/schema_export.pt",
#                                    content_type="text/xml; charset=UTF-8")
#
#    __call__ = template
#
#    def exceptiondayids(self):
#        result = []
#
#        for date, id in self.context.model.exceptionDayIds.items():
#            result.append({'when': str(date), 'id': id})
#
#        result.sort(lambda a, b: cmp((a['when'], a['id']),
#                                     (b['when'], b['id'])))
#        return result
#
#    def daytemplates(self):
#        items = self.context.items()
#        id = items[0][0]
#        result = []
#        for id, day in self.context.model.dayTemplates.items():
#            if id is None:
#                used = "default"
#            elif id in self.context.keys():
#                used = id
#            else:
#                used = self.dows[id]
#            periods = []
#            for period in day:
#                periods.append(
#                    {'id': None,
#                     'tstart': period.tstart.strftime("%H:%M"),
#                     'duration': period.duration.seconds / 60})
#            periods.sort()
#            for template in result:
#                if template['periods'] == periods:
#                    days = template['used'].split()
#                    days.append(used)
#                    days.sort()
#                    template['used'] = " ".join(days)
#                    break
#            else:
#                result.append({'used': used, 'periods': periods})
#
#        for date, day in self.context.model.exceptionDays.items():
#            periods = []
#            for period, slot in day:
#                periods.append(
#                    {'id': period,
#                     'tstart': slot.tstart.strftime("%H:%M"),
#                     'duration': slot.duration.seconds / 60})
#            periods.sort()
#            result.append({'used': str(date), 'periods': periods})
#
#        result.sort(lambda a, b: cmp((a['used'], a['periods']),
#                                     (b['used'], b['periods'])))
#
#        return result



class ISelectedPeriodsAddForm(Interface):
    """Form schema for ITerm add/edit views."""

    timetable = zope.schema.Choice(
        title=_("School timetable"),
        source="schooltool.timetable.browser.timetable_vocabulary",
        required=True,
    )

    first = zope.schema.Date(title=_("Apply from"))

    last = zope.schema.Date(title=_("Apply until"))


class SelectedPeriodsAddView(form.AddForm):

    template = ViewPageTemplateFile('templates/selected_periods_add.pt')
    fields = field.Fields(ISelectedPeriodsAddForm)

    _object_added = None

    buttons = button.Buttons(
        button.Button('add', title=_('Add')),
        button.Button('cancel', title=_('Cancel')))

    @property
    def owner(self):
        return IHaveSchedule(self.context)

    @property
    def term(self):
        return ITerm(self.owner, None)

    @button.handler(buttons["add"])
    def handleAdd(self, action):
        return form.AddForm.handleAdd.func(self, action)

    @button.handler(buttons["cancel"])
    def handleCancel(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SelectedPeriodsAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def create(self, data):
        timetable = data['timetable']
        schedule = SelectedPeriodsSchedule(
            timetable, data['first'], data['last'],
            title=timetable.title,
            timezone=timetable.timezone)
        return schedule

    def add(self, schedule):
        chooser = INameChooser(self.context)
        name = chooser.chooseName('', schedule)
        self.context[name] = schedule
        self._object_added = schedule

    def nextURL(self):
        if self._object_added is not None:
            return '%s/edit.html' % (
                absoluteURL(self._object_added, self.request))
        return absoluteURL(self.context, self.request)


TimetableAdd_default_first = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.term.first,
    view=SelectedPeriodsAddView,
    field=ISelectedPeriodsAddForm['first']
    )


TimetableAdd_default_last = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.term.last,
    view=SelectedPeriodsAddView,
    field=ISelectedPeriodsAddForm['last']
    )


class FlourishSelectedPeriodsAddView(flourish.form.AddForm,
                                     SelectedPeriodsAddView):
    template = flourish.templates.Inherit(flourish.page.Page.template)
    legend = _("Schedule a school timetable")


SelectedPeriodsSubmitLabel = button.StaticButtonActionAttribute(
    _(u'Submit'),
    button=FlourishSelectedPeriodsAddView.buttons['add'])


class SelectedPeriodsFormValidator(validator.InvariantsValidator):

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

    def getOthers(self, schedule):
        container = schedule.__parent__
        others = [other for key, other in container.items()
                  if key != schedule.__name__]
        return others

#    def validateAgainstOthers(self, schedule, others):
#        pass

#    def validateAgainstTerm(self, schedule, term):
#    term_daterange = IDateRange(term)
#    if ((first is not None and first not in term_daterange) or
#        (last is not None and last not in term_daterange)):
#        raise TimetableOverflowError(
#            schema, first, last, term)

    def validateObject(self, schedule):
        #errors = super(SelectedPeriodsFormValidator, self).validateObject(schedule)
        #try:
        #    dr = DateRange(schedule.first, schedule.last)
        #
        #    others = self.getOthers()
        #
        #    term = ITerm(timetable_dict)
        #
        #    try:
        #        validateAgainstOthers(
        #            timetable.schooltt, timetable.first, timetable.last,
        #            others)
        #    except TimetableOverlapError, e:
        #        for tt in e.overlapping:
        #            errors += (Invalid(
        #                u"%s %s" % (
        #                    _("Timetable conflicts with another:"),
        #                    self._formatTitle(tt))), )
        #    try:
        #        validateAgainstTerm(
        #            timetable.schooltt, timetable.first, timetable.last,
        #            term)
        #    except TimetableOverflowError, e:
        #        errors += (Invalid(u"%s %s" % (
        #            _("Timetable does not fit in term"),
        #            self._formatTitle(term))), )
        #except ValueError, e:
        #    errors += (Invalid(_("Schedule must begin before it ends.")), )
        #except validator.NoInputData:
        #    return errors
        #return errors
        return []


class SelectedPeriodsAddFormValidator(validator.InvariantsValidator):
    def getOthers(self, schedule):
        container = self.context
        return container.values()


validator.WidgetsValidatorDiscriminators(
    SelectedPeriodsAddFormValidator,
    view=SelectedPeriodsAddView,
    schema=getSpecification(ISelectedPeriodsAddForm, force=True))


class SelectedPeriodsContent(ContentProvider):
    implements(IRenderDayTableCells)

    def __init__(self, *args, **kw):
        ContentProvider.__init__(self, *args, **kw)
        self.owner = IHaveSchedule(self.context)

    def renderCells(self, schedule, day, item):
        timetable = self.context.timetable
        if sameProxiedObjects(schedule, timetable.periods):
            if self.context.hasPeriod(item):
                return (item.title,
                        self.owner.title)
            else:
                return (item.title, '')
        return None

    def __call__(self):
        return self.template()


class ISelectedPeriodsAddTermsForm(Interface):

    timetable = zope.schema.Choice(
        title=_("School timetable"),
        source="schooltool.timetable.browser.timetable_vocabulary",
        required=True,
    )

    first = zope.schema.Choice(
        title=_("First term"),
        required=True,
        vocabulary='schooltool.course.section.linked_section_terms')

    last = zope.schema.Choice(
        title=_("Last term"),
        required=True,
        vocabulary='schooltool.course.section.linked_section_terms')


class FlourishSelectedPeriodsAddTermsView(FlourishSelectedPeriodsAddView):
    fields = field.Fields(ISelectedPeriodsAddTermsForm)

    _objects_added = None
    _objects_created = None

    buttons = button.Buttons(
        button.Button('add', title=_('Add')),
        button.Button('cancel', title=_('Cancel')))

    @property
    def owner(self):
        return IHaveSchedule(self.context)

    @button.handler(buttons["add"])
    def handleAdd(self, action):
        return form.AddForm.handleAdd.func(self, action)

    @button.handler(buttons["cancel"])
    def handleCancel(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SelectedPeriodsAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def create(self, data):
        section = self.owner
        linked = section.linked_sections
        terms = [(ITerm(s), s) for s in linked]
        terms = [(term, section) for term, section in terms
                 if (term.first >= data['first'].first and
                     term.last <= data['last'].last)]
        self._objects_created = []
        timetable = data['timetable']
        for term, section in terms:
            schedule = SelectedPeriodsSchedule(
                timetable, term.first, term.last,
                title=timetable.title,
                timezone=timetable.timezone)
            self._objects_created.append((section, schedule))
        return self._objects_created

    def add(self, schedules):
        self._objects_added = []
        for section, schedule in self._objects_created:
            schedules = IScheduleContainer(section)
            chooser = INameChooser(schedules)
            name = chooser.chooseName('', schedule)
            schedules[name] = schedule
            self._objects_added.append(schedule)

    def nextURL(self):
        if self._objects_added:
            int_ids = getUtility(IIntIds)
            also_apply = ''
            this_section = self.owner
            n = 0
            for schedule in self._objects_added:
                section = IHaveSchedule(schedule)
                if sameProxiedObjects(this_section, section):
                    continue
                also_apply = '&'.join(
                    [also_apply,
                    'section-%d=%s&schedule-%d=%s' % (
                        n, int_ids.getId(removeSecurityProxy(section)),
                        n, urllib.quote(schedule.__name__)),
                     ])
                n += 1
            if also_apply:
                also_apply = '?' + also_apply
            return '%s/edit_multi.html%s' % (
                absoluteURL(self._objects_added[0], self.request),
                also_apply)
        return absoluteURL(self.context, self.request)


SelectedPeriodsAddTermsSubmitLabel = button.StaticButtonActionAttribute(
    _(u'Submit'),
    button=FlourishSelectedPeriodsAddTermsView.buttons['add'])


TimetableAdd_default_first = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.term.first,
    view=SelectedPeriodsAddView,
    field=ISelectedPeriodsAddForm['first']
    )


TimetableAdd_default_last = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.term.last,
    view=SelectedPeriodsAddView,
    field=ISelectedPeriodsAddForm['last']
    )


class SelectedPeriodsAddTertiaryNav(flourish.page.TertiaryNavigationManager):
    pass


class SelectedPeriodsScheduleEditView(form.EditForm):
    implements(IRenderDayTableCells)

    template = ViewPageTemplateFile('templates/selected_periods_edit.pt')
    fields = field.Fields(ISelectedPeriodsSchedule).select(
        'first', 'last',
        'consecutive_periods_as_one')
    fields['consecutive_periods_as_one'].widgetFactory = SingleCheckBoxFieldWidget

    def getPeriodKey(self, day, period):
        return 'period.%s.%s' % (simple_form_key(day),
                                 simple_form_key(period))

    def activityTitle(self, activity_type):
        if activity_type in self.activity_vocabulary:
            term = self.activity_vocabulary.getTerm(activity_type)
            return term.title
        return None

    def renderCells(self, schedule, day, item):
        timetable = self.context.timetable
        if sameProxiedObjects(schedule, timetable.periods):
            checked = self.context.hasPeriod(item)
            key = self.getPeriodKey(day, item)
            checkbox = """
              <input class="activity" type="checkbox"
                     id="%(key)s" name="%(key)s"
                     value="%(key)s"%(checked)s></input>""" % {
                'key': key,
                'checked': checked and ' checked="checked"' or ''}
            label = """
              <label class="period" for="%(key)s">%(title)s</label>""" % {
                'key': key, 'title': item.title or ''}
            return (checkbox, label)
        if sameProxiedObjects(schedule, timetable.time_slots):
            slot = item
            return (format_time_range(slot.tstart, slot.duration),
                    self.activityTitle(slot.activity_type) or '')
        return None

    def update(self):
        self.owner = IHaveSchedule(self.context)
        self.activity_vocabulary = getActivityVocabulary(self.context)
        super(SelectedPeriodsScheduleEditView, self).update()

    def updateActions(self):
        super(SelectedPeriodsScheduleEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        changes = self.applyChanges(data)

        schedule_changed = bool(changes)

        timetable = self.context.timetable
        for day in timetable.periods.templates.values():
            for period in day.values():
                key = self.getPeriodKey(day, period)
                selected = bool(self.request.get(key))
                scheduled = self.context.hasPeriod(period)
                if selected and not scheduled:
                    self.context.addPeriod(period)
                    schedule_changed = True
                elif not selected and scheduled:
                    self.context.removePeriod(period)
                    schedule_changed = True

        self.status = self.successMessage

        if schedule_changed:
            zope.lifecycleevent.modified(self.context)
        self.redirectToParent()

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        self.redirectToParent()

    def redirectToParent(self):
        self.request.response.redirect(
            absoluteURL(self.context.__parent__,
                        self.request))

    @property
    def term(self):
        return ITerm(self.owner, None)


validator.WidgetsValidatorDiscriminators(
    SelectedPeriodsFormValidator,
    view=SelectedPeriodsScheduleEditView,
    schema=getSpecification(ITimetable, force=True))


class FlourishSelectedPeriodsScheduleEditView(flourish.page.WideContainerPage,
                                              SelectedPeriodsScheduleEditView):
    __init__ = SelectedPeriodsScheduleEditView.__init__
    update = SelectedPeriodsScheduleEditView.update


class FlourishSelectedPeriodsMultiScheduleEditView(flourish.page.WideContainerPage,
                                                   SelectedPeriodsScheduleEditView):
    __init__ = SelectedPeriodsScheduleEditView.__init__
    update = SelectedPeriodsScheduleEditView.update

    fields = field.Fields(ISelectedPeriodsSchedule).select(
        'consecutive_periods_as_one')
    fields['consecutive_periods_as_one'].widgetFactory = SingleCheckBoxFieldWidget

    def applyChangesToSchedule(self, schedule, data):
        changes = form.applyChanges(self, schedule, data)
        # ``changes`` is a dictionary; if empty, there were no changes
        if changes:
            # Construct change-descriptions for the object-modified event
            descriptions = []
            for interface, names in changes.items():
                descriptions.append(
                    zope.lifecycleevent.Attributes(interface, *names))
            # Send out a detailed object-modified event
            zope.event.notify(
                zope.lifecycleevent.ObjectModifiedEvent(schedule, *descriptions))

        schedule_changed = bool(changes)
        timetable = schedule.timetable
        for day in timetable.periods.templates.values():
            for period in day.values():
                key = self.getPeriodKey(day, period)
                selected = bool(self.request.get(key))
                scheduled = schedule.hasPeriod(period)
                if selected and not scheduled:
                    schedule.addPeriod(period)
                    schedule_changed = True
                elif not selected and scheduled:
                    schedule.removePeriod(period)
                    schedule_changed = True
        return schedule_changed

    @property
    def other_params(self):
        params = []
        n = 0
        while ('section-%d' % n in self.request and
               'schedule-%d' % n in self.request):
            params.extend([
                {'key': 'section-%d' % n, 'value': self.request.get('section-%d' % n)},
                {'key': 'schedule-%d' % n, 'value': self.request.get('schedule-%d' % n)},
                ])
            n += 1
        return params

    @property
    def other_schedules(self):
        result = []
        n = 0
        int_ids = getUtility(IIntIds)
        while ('section-%d' % n in self.request and
               'schedule-%d' % n in self.request):
            section_id = self.request.get('section-%d' % n)
            schedule_name = self.request.get('schedule-%d' % n)
            n += 1
            try:
                section_id = int(section_id)
            except ValueError:
                continue
            section = int_ids.queryObject(section_id, None)
            if section is None:
                continue
            schedules = IScheduleContainer(section)
            schedule = schedules.get(schedule_name, None)
            if schedule is None:
                continue
            result.append(schedule)
        return result

    @property
    def other_info(self):
        result = []
        for schedule in self.other_schedules:
            section = IHaveSchedule(schedule)
            term = ITerm(section)
            result.append({'owner': section, 'term': term})
        return result

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        changed = self.applyChangesToSchedule(self.getContent(), data)
        if changed:
            zope.lifecycleevent.modified(self.getContent())

        for schedule in self.other_schedules:
            changed = self.applyChangesToSchedule(schedule, data)
            if changed:
                zope.lifecycleevent.modified(schedule)

        self.status = self.successMessage

        self.redirectToParent()

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        self.redirectToParent()


class FlourishSelectedScheduleDeleteView(FlourishConfirmDeleteView):

    def initDialog(self):
        super(FlourishSelectedScheduleDeleteView, self).initDialog()
        title = _(u'Unschedule timetable ${timetable}',
                  mapping={'timetable': self.context.timetable.title})
        self.ajax_settings['dialog']['title'] = translate(
            title, context=self.request)

    def delete(self):
        container = self.context.__parent__
        del container[self.context.__name__]

    @property
    def owner(self):
        return IHaveSchedule(self.context)


class TimetableActionsLinks(flourish.page.RefineLinksViewlet):
    """Manager for Action links in timetable views."""


class FlourishTimetableDeleteView(FlourishConfirmDeleteView):

    def initDialog(self):
        super(FlourishTimetableDeleteView, self).initDialog()
        title = _(u'Delete ${timetable}',
                  mapping={'timetable': self.context.title})
        self.ajax_settings['dialog']['title'] = translate(
            title, context=self.request)

    def delete(self):
        container = ITimetableContainer(self.context)
        del container[self.context.__name__]


class FlourishTimetableMakeDefaultView(flourish.form.DialogForm, form.EditForm):
    template = flourish.templates.Inherit(flourish.page.Page.template)
    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    def initDialog(self):
        super(FlourishTimetableMakeDefaultView, self).initDialog()
        title = _(u'Make ${timetable} default',
                  mapping={'timetable': self.context.title})
        self.ajax_settings['dialog']['title'] = translate(
            title, context=self.request)

    @button.buttonAndHandler(_("Apply"), name='apply')
    def handleApply(self, action):
        container = ITimetableContainer(self.context)
        container.default = removeSecurityProxy(self.context)
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handleCancel(self, action):
        pass

    def updateActions(self):
        super(FlourishTimetableMakeDefaultView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')
