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
Timetabling Schema views.

$Id$
"""

#from zope.i18n import translate
import zope.schema
import zope.lifecycleevent
from zope.proxy import sameProxiedObjects
from zope.component import getMultiAdapter, queryMultiAdapter
from zope.component import adapts
#from zope.component import getUtility, queryUtility
from zope.container.interfaces import INameChooser
from zope.interface import Interface, implements
from zope.interface.exceptions import Invalid
#from zope.schema import TextLine, Int
#from zope.schema.interfaces import RequiredMissing
#from zope.intid.interfaces import IIntIds
#from zope.app.form.interfaces import IWidgetInputError
#from zope.app.form.interfaces import IInputWidget
#from zope.app.form.interfaces import WidgetInputError
#from zope.app.form.interfaces import WidgetsError
#from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
#from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IBrowserView
#from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL
from z3c.form import form, field, button, widget, validator
from z3c.form.util import getSpecification
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget

from schooltool.app.browser.content import ContentProvider
from schooltool.common import format_time_range
#from schooltool.common import parse_time_range
#from schooltool.skin.containers import ContainerView, ContainerDeleteView
#from schooltool.app.interfaces import ISchoolToolApplication
#from schooltool.app.interfaces import IApplicationPreferences
#from schooltool.timetable import SchooldayTemplate, SchooldaySlot
#from schooltool.timetable.interfaces import ITimetableModelFactory
#from schooltool.timetable.interfaces import ITimetableSchema
#from schooltool.timetable.interfaces import ITimetableSchemaContainer
#from schooltool.timetable.schema import TimetableSchema, TimetableSchemaDay
#from schooltool.timetable import findRelatedTimetables
#from schooltool.timetable.browser.schedule import TimetableView, TabindexMixin
#from schooltool.timetable.browser.schedule import format_timetable_for_presentation
from schooltool.table.table import simple_form_key
from schooltool.timetable.interfaces import ITimetable
from schooltool.timetable.interfaces import IDayTemplateSchedule
from schooltool.timetable.interfaces import ISelectedPeriodsSchedule
from schooltool.timetable.interfaces import IHaveSchedule
from schooltool.timetable.browser.app import getActivityVocabulary
from schooltool.timetable.timetable import SelectedPeriodsSchedule
from schooltool.term.interfaces import ITerm

from schooltool.common import SchoolToolMessage as _


#def fix_duplicates(names):
#    """Change a list of names so that there are no duplicates.
#
#    Trivial cases:
#
#      >>> fix_duplicates([])
#      []
#      >>> fix_duplicates(['a', 'b', 'c'])
#      ['a', 'b', 'c']
#
#    Simple case:
#
#      >>> fix_duplicates(['a', 'b', 'b', 'a', 'b'])
#      ['a', 'b', 'b (2)', 'a (2)', 'b (3)']
#
#    More interesting cases:
#
#      >>> fix_duplicates(['a', 'b', 'b', 'a', 'b (2)', 'b (2)'])
#      ['a', 'b', 'b (3)', 'a (2)', 'b (2)', 'b (2) (2)']
#
#    """
#    seen = set(names)
#    if len(seen) == len(names):
#        return names    # no duplicates
#    result = []
#    used = set()
#    for name in names:
#        if name in used:
#            n = 2
#            while True:
#                candidate = '%s (%d)' % (name, n)
#                if not candidate in seen:
#                    name = candidate
#                    break
#                n += 1
#            seen.add(name)
#        result.append(name)
#        used.add(name)
#    return result


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


# MOVED to schooltool.timetable.browser.app.TimetableContainerView
#class TimetableSchemaContainerView(ContainerView):
#    """TimetableSchema Container view."""
#
#    __used_for__ = ITimetableSchemaContainer
#
#    index_title = _("School Timetables")
#
#    def update(self):
#        if 'UPDATE_SUBMIT' in self.request:
#            self.context.default_id = self.request['ttschema'] or None
#        return ''


#class TimetableDependentDeleteView(ContainerDeleteView):
#    """The delete view for school timetables and schemas.
#
#    Finds all timetables that use the object to be deleted and deletes
#    them too.
#    """
#
#    adapts((ITimetableSchemaContainer, IBrowserRequest))
#    implements(IBrowserPublisher)
#
#    def timetables(self, obj):
#        return findRelatedTimetables(obj)
#
#    def update(self):
#        if 'CONFIRM' in self.request:
#            for key in self.listIdsForDeletion():
#                del self.context[key]
#            self.request.response.redirect(self.nextURL())
#        elif 'CANCEL' in self.request:
#            self.request.response.redirect(self.nextURL())


#class IAdvancedTimetableSchemaAddSchema(Interface):
#
#    title = TextLine(title=_(u"Title"), required=False)
#    duration = Int(title=_(u"Duration"), description=_(u"Duration in minutes"),
#                   required=False)


#class AdvancedTimetableSchemaAdd(BrowserView, TabindexMixin):
#    """View for defining a new timetable schema.
#
#    Can be accessed at /ttschemas/complexadd.html.
#    """
#
#    __used_for__ = ITimetableSchemaContainer
#
#    template = ViewPageTemplateFile("templates/advancedtts.pt")
#
#    # Used in the page template
#    days_of_week = (_("Monday"),
#                    _("Tuesday"),
#                    _("Wednesday"),
#                    _("Thursday"),
#                    _("Friday"),
#                    _("Saturday"),
#                    _("Sunday"),
#                   )
#
#    _schema = IAdvancedTimetableSchemaAddSchema
#
#    def __init__(self, context, request):
#        BrowserView.__init__(self, context, request)
#        TabindexMixin.__init__(self)
#        setUpWidgets(self, self._schema, IInputWidget,
#                     initial={'title': 'default'})
#
#    def __call__(self):
#
#        # We could build a custom widget for the model radio buttons, but I do
#        # not think it is worth the trouble.
#        self.model_error = None
#        self.model_name = self.request.get('model')
#
#        self.ttschema = self._buildSchema()
#        self.day_templates = self._buildDayTemplates()
#
#        if 'CREATE' in self.request:
#            data = getWidgetsData(self, self._schema)
#            factory = queryUtility(ITimetableModelFactory,
#                                   name=self.model_name)
#            if factory is None:
#                self.model_error = _("Please select a value")
#            if not self.title_widget.error() and not self.model_error:
#                model = factory(self.ttschema.day_ids, self.day_templates)
#                self.ttschema.model = model
#                self.ttschema.title = data['title']
#                nameChooser = INameChooser(self.context)
#                key = nameChooser.chooseName('', self.ttschema)
#                self.context[key] = self.ttschema
#                #Note: if you uncomment this, fix the i18n bug inside too.
#                #self.request.appLog(_("Timetable schema %s created") %
#                #               getPath(self.context[key]))
#                return self.request.response.redirect(
#                    absoluteURL(self.context, self.request))
#        return self.template()
#
#    def rows(self):
#        return format_timetable_for_presentation(self.ttschema)
#
#    def _buildSchema(self):
#        """Build a timetable schema from data in the request."""
#        n = 1
#        day_ids = []
#        day_idxs = []
#        while 'day%d' % n in self.request:
#            if 'DELETE_DAY_%d' % n not in self.request:
#                day_id = self.request['day%d' % n].strip()
#                if not day_id:
#                    day_id_msgid = _('Day ${number}',
#                                     mapping={'number': len(day_ids) + 1})
#                    day_id = translate(day_id_msgid, context=self.request)
#                day_ids.append(day_id)
#                day_idxs.append(n)
#            n += 1
#        if 'ADD_DAY' in self.request or not day_ids:
#            day_id_msgid = _('Day ${number}',
#                             mapping={'number': len(day_ids) + 1})
#            day_id = translate(day_id_msgid, context=self.request)
#            day_ids.append(day_id)
#            day_idxs.append(-1)
#        day_ids = fix_duplicates(day_ids)
#
#        periods_for_day = []
#        longest_day = None
#        previous_day = None
#        for idx, day in zip(day_idxs, day_ids):
#            n = 1
#            if ('COPY_DAY_%d' % (idx - 1) in self.request
#                and previous_day is not None):
#                periods = list(previous_day)
#            else:
#                periods = []
#                while 'day%d.period%d' % (idx, n) in self.request:
#                    per_id = self.request['day%d.period%d' % (idx, n)].strip()
#                    periods.append(per_id)
#                    n += 1
#                periods = filter(None, periods)
#                if not periods:
#                    period1 = translate(_("Period 1"), context=self.request)
#                    periods = [period1]
#                else:
#                    periods = fix_duplicates(periods)
#            periods_for_day.append(periods)
#            if longest_day is None or len(periods) > len(longest_day):
#                longest_day = periods
#            previous_day = periods
#
#        if 'ADD_PERIOD' in self.request:
#            period_name_msgid = _('Period ${number}',
#                                  mapping={'number': len(longest_day) + 1})
#            period_name = translate(period_name_msgid, context=self.request)
#            longest_day.append(period_name)
#
#        app = ISchoolToolApplication(None)
#        tzname = IApplicationPreferences(app).timezone
#        ttschema = TimetableSchema(day_ids, timezone=tzname)
#        for day, periods in zip(day_ids, periods_for_day):
#            ttschema[day] = TimetableSchemaDay(periods)
#
#        return ttschema
#
#    def _buildDayTemplates(self):
#        """Built a dict of day templates from data contained in the request.
#
#        The dict is suitable to be passed as the second argument to the
#        timetable model factory.
#        """
#        data = getWidgetsData(self, self._schema)
#        default_duration = data.get('duration')
#        result = {None: SchooldayTemplate()}
#        n = 1
#        self.discarded_some_periods = False
#        while 'time%d.day0' % n in self.request:
#            raw_value = [0]
#            for day in range(7):
#                value = self.request.form.get('time%d.day%d' % (n, day), '')
#                if not value:
#                    continue
#                try:
#                    start, duration = parse_time_range(value, default_duration)
#                except ValueError:
#                    # ignore invalid values for now, but tell the user
#                    self.discarded_some_periods = True
#                    continue
#                if day not in result:
#                    result[day] = SchooldayTemplate()
#                result[day].add(SchooldaySlot(start, duration))
#            n += 1
#        for day in range(1, 7):
#            if 'COPY_PERIODS_%d' % day in self.request:
#                if (day - 1) in result:
#                    result[day] = result[day - 1]
#                elif day in result:
#                    del result[day]
#        return result
#
#    def all_periods(self):
#        """Return a list of all period names in order of occurrence."""
#        periods = []
#        for day_id in self.ttschema.day_ids:
#            for period in self.ttschema[day_id].periods:
#                if period not in periods:
#                    periods.append(period)
#        return periods
#
#    def slot_times(self):
#        """Return a list of lists of time periods for each day for each slot.
#
#                      |  mo tu we thu fri sa su
#             ---------+-------------------------
#             1st slot |
#             2nd slot |
#             ...      |
#        """
#        nr_rows = max([len(day.keys())
#                       for day_id, day in self.ttschema.items()])
#        result =  [[None] * 7 for i in range(nr_rows)]
#        for day, template in self.day_templates.items():
#            for idx, slot in enumerate(template):
#                slotfmt = format_time_range(slot.tstart, slot.duration)
#                result[idx][day] = slotfmt
#        return result


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

    template = ViewPageTemplateFile('templates/selected-periods-add.pt')
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


class SelectedPeriodsScheduleEditView(form.EditForm):
    implements(IRenderDayTableCells)

    template = ViewPageTemplateFile('templates/selected-periods-edit.pt')
    fields = field.Fields(ISelectedPeriodsSchedule).select(
        'first', 'last',
        'consecutive_periods_as_one')
    fields['consecutive_periods_as_one'].widgetFactory = SingleCheckBoxFieldWidget

    def __init__(self, *args, **kw):
        form.EditForm.__init__(self, *args, **kw)
        self.owner = IHaveSchedule(self.context)
        self.activity_vocabulary = getActivityVocabulary(self.context)

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
