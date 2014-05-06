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
Views for school years and school year container implementation
"""
from zope.viewlet.viewlet import ViewletBase
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.cachedescriptors.property import Lazy
from zope.component import adapts, getMultiAdapter
from zope.event import notify
from zope.security import checkPermission
from zope.schema import Date, TextLine
from zope.schema.interfaces import ValidationError
from zope.interface.exceptions import Invalid
from zope.interface import implements
from zope.interface import Interface
from zope.traversing.browser.absoluteurl import AbsoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.container.interfaces import INameChooser
from zope.container.contained import containedEvent
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.proxy import sameProxiedObjects
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canAccess

from z3c.form import form, field, button
from z3c.form.util import getSpecification
from z3c.form.validator import NoInputData
from z3c.form.validator import WidgetsValidatorDiscriminators
from z3c.form.validator import InvariantsValidator
from z3c.form.validator import WidgetValidatorDiscriminators
from z3c.form.validator import SimpleFieldValidator
from z3c.form.error import ErrorViewSnippet
from z3c.form.interfaces import DISPLAY_MODE

import zc.table.column

import schooltool.skin.flourish.containers
import schooltool.skin.flourish.breadcrumbs
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.common import DateRange
from schooltool.common import SchoolToolMessage as _
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.course import Course
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.group import Group, defaultGroups
from schooltool.schoolyear.browser.interfaces import ISchoolYearViewMenuViewletManager
from schooltool.schoolyear.schoolyear import validateScholYearForOverflow
from schooltool.schoolyear.schoolyear import validateScholYearsForOverlap
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.interfaces import TermOverflowError
from schooltool.schoolyear.interfaces import SchoolYearOverlapError
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin.skin import OrderedViewletManager
from schooltool.skin.containers import ContainerDeleteView
from schooltool.skin.containers import TableContainerView
from schooltool.skin import flourish
from schooltool.table import table
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.interfaces import IWeekDayTemplates
from schooltool.timetable.interfaces import ISchoolDayTemplates
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period

class SchoolYearContainerAbsoluteURLAdapter(AbsoluteURL):

    adapts(ISchoolYearContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/schoolyears'

    __call__ = __str__


class SchoolYearAbsoluteURLAdapter(AbsoluteURL):

    adapts(ISchoolYear, IBrowserRequest)
    implements(IAbsoluteURL)


class SchoolYearContainerBaseView(object):

    def canDeleteSchoolYears(self):
        return len(self.listIdsForDeletion()) >= len(self.context)

    def deletingActiveSchoolYear(self):
        return self.context.getActiveSchoolYear().__name__ in self.listIdsForDeletion()


class SchoolYearContainerDeleteView(ContainerDeleteView, SchoolYearContainerBaseView):
    """A view for deleting items from container."""

    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                if key != self.context.active_id:
                    del self.context[key]
            if self.deletingActiveSchoolYear():
                del self.context[self.context.active_id]
            self.request.response.redirect(self.nextURL())
        elif 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())


class SchoolYearContainerView(TableContainerView, SchoolYearContainerBaseView):
    """SchoolYear container view."""

    __used_for__ = ISchoolYearContainer
    template = ViewPageTemplateFile("templates/schoolyear_container.pt")

    index_title = _("School Years")
    error = None

    @property
    def first(self):
        year = self.context.getActiveSchoolYear()
        if year is not None:
            return year.first

    @property
    def last(self):
        year = self.context.getActiveSchoolYear()
        if year is not None:
            return year.last

    def setUpTableFormatter(self, formatter):
        columns_before = []
        if self.canModify():
            columns_before = [
                table.DependableCheckboxColumn(prefix="delete",
                                               name='delete_checkbox',
                                               title=u'')]
        columns_after = [table.DateColumn(title=_("Starts"),
                                          getter=lambda x, y: x.first),
                         table.DateColumn(title=_("Ends"),
                                          getter=lambda x, y: x.last)]
        formatter.setUp(formatters=[table.url_cell_formatter],
                        columns_before=columns_before,
                        columns_after=columns_after)

    def __call__(self):
        if 'DELETE' in self.request:
            if not self.deletingActiveSchoolYear():
                return self.delete_template()
            elif not self.canDeleteSchoolYears():
                self.error = _("You can not delete the active school year."
                               " Unless you are deleting all the school years.")
            else:
                return self.delete_template()

        self.setUpTableFormatter(self.table)
        return self.template()

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def update(self):
        if 'ACTIVATE_NEXT_SCHOOLYEAR' in self.request:
            for key in self.listIdsForDeletion():
                if key in self.context:
                    self.context.activateNextSchoolYear(key)
                    self.request.response.redirect(self.nextURL())


class FlourishActiveSchoolYearColumn(zc.table.column.Column):
    """Table column that displays whether a schoolyear is the active one.
    """

    def renderCell(self, item, formatter):
        if item.__parent__.active_id == item.__name__:
            return '<span class="ui-icon ui-icon-check"></span>'
        else:
            return ''


class SchoolYearTableFormatter(table.SchoolToolTableFormatter):

    def sortOn(self):
        return (('first', True),)


class FlourishSchoolYearContainerView(table.TableContainerView):
    """flourish SchoolYear container view."""

    def getColumnsAfter(self):
        result = [
            table.DateColumn(title=_("First Day"),
                             name='first',
                             getter=lambda x, y: x.first),
            table.DateColumn(title=_("Last Day"),
                             getter=lambda x, y: x.last),
            FlourishActiveSchoolYearColumn(title=_("Active")),
            ]
        return result


class FlourishSchoolYearContainerLinks(flourish.page.RefineLinksViewlet):
    """SchoolYear container links viewlet."""


class FlourishSchoolYearContainerActionLinks(flourish.page.RefineLinksViewlet):
    """SchoolYear container action links viewlet."""


class FlourishSchoolYearActionLinks(flourish.page.RefineLinksViewlet):
    """SchoolYear action links viewlet."""


class FlourishSchoolYearDeleteLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Delete ${schoolyear}',
                  mapping={'schoolyear': self.context.title})
        return translate(title, context=self.request)


class FlourishSchoolYearDeleteView(flourish.form.DialogForm, form.EditForm):
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
        super(FlourishSchoolYearDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class ISchoolYearAddForm(Interface):

    title = TextLine(
        title=_("Title"))

    first = Date(
        title=_(u"First day"))

    last = Date(
        title=_(u"Last day"))


class SchoolYearAddFormAdapter(object):
    implements(ISchoolYearAddForm)
    adapts(ISchoolYear)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __setattr__(self, name, value):
        setattr(self.context, name, value)

    def __getattr__(self, name):
        return getattr(self.context, name)


class ImportSchoolYearData(object):

    def hasCourses(self, schoolyear):
        courses = ICourseContainer(schoolyear)
        return bool(courses)

    def hasTimetableSchemas(self, schoolyear):
        timetables = ITimetableContainer(schoolyear)
        return bool(timetables)

    def activeSchoolyearInfo(self):
        result = {}
        request = self.request
        collator = ICollator(request.locale)
        activeSchoolyear = self.context.getActiveSchoolYear()
        if activeSchoolyear is not None:
            result['title'] = activeSchoolyear.title
            result['hasCourses'] = self.hasCourses(activeSchoolyear)
            result['hasTimetables'] = self.hasTimetableSchemas(activeSchoolyear)
            result['groups'] = []
            groups = IGroupContainer(activeSchoolyear)
            for groupId, group in sorted(groups.items(),
                                         cmp=collator.cmp,
                                         key=lambda (groupId,group):group.title):
                info = {}
                info['id'] = groupId
                info['title'] = group.title
                info['isDefault'] = groupId in defaultGroups
                info['hasMembers'] = bool(list(group.members))
                info['sent'] = groupId in self.customGroupsToImport
                info['membersSent'] = groupId in self.groupsWithMembersToImport
                result['groups'].append(info)
        return result

    def importAllCourses(self):
        if not self.shouldImportAllCourses():
            return
        oldCourses = ICourseContainer(self.activeSchoolyear)
        newCourses = ICourseContainer(self.newSchoolyear)
        for id, course in oldCourses.items():
            newCourses[course.__name__] = new_course = Course(course.title, course.description)
            new_course.course_id = course.course_id
            new_course.government_id = course.government_id
            new_course.credits = course.credits
            for level in course.levels:
                new_course.levels.add(removeSecurityProxy(level))

    def setUpTimetable(self, timetable, old_timetable):
        if IWeekDayTemplates.providedBy(old_timetable.time_slots):
            timetable.time_slots, object_event = containedEvent(
                WeekDayTemplates(), timetable, 'time_slots')
        elif ISchoolDayTemplates.providedBy(old_timetable.time_slots):
            timetable.time_slots, object_event = containedEvent(
                SchoolDayTemplates(), timetable, 'time_slots')
        notify(object_event)
        timetable.time_slots.initTemplates()
        old_templates = old_timetable.time_slots.templates
        for old_template_key, old_template in old_templates.items():
            template = DayTemplate(old_template.title)
            timetable.time_slots.templates[old_template_key] = template
            for old_timeslot_key, old_timeslot in old_template.items():
                timeslot = TimeSlot(old_timeslot.tstart,
                                    old_timeslot.duration,
                                    old_timeslot.activity_type)
                template[old_timeslot_key] = timeslot
        if IWeekDayTemplates.providedBy(old_timetable.periods):
            timetable.periods, object_event = containedEvent(
                WeekDayTemplates(), timetable, 'periods')
        elif ISchoolDayTemplates.providedBy(old_timetable.periods):
            timetable.periods, object_event = containedEvent(
                SchoolDayTemplates(), timetable, 'periods')
        notify(object_event)
        timetable.periods.initTemplates()
        old_templates = old_timetable.periods.templates
        for old_template_key, old_template in old_templates.items():
            template = DayTemplate(old_template.title)
            timetable.periods.templates[old_template_key] = template
            for old_period_key, old_period in old_template.items():
                period = Period(old_period.title, old_period.activity_type)
                template[old_period_key] = period

    def importAllTimetables(self):
        if not self.shouldImportAllTimetables():
            return
        oldTimetables = ITimetableContainer(self.activeSchoolyear)
        newTimetables = ITimetableContainer(self.newSchoolyear)
        chooser = INameChooser(newTimetables)
        app = ISchoolToolApplication(None)
        tzname = IApplicationPreferences(app).timezone
        for schooltt in oldTimetables.values():
            newSchooltt = Timetable(
                self.newSchoolyear.first, self.newSchoolyear.last,
                title=schooltt.title,
                timezone=tzname)
            name = chooser.chooseName(schooltt.__name__, newSchooltt)
            newTimetables[name] = newSchooltt
            self.setUpTimetable(newSchooltt, schooltt)
            if (oldTimetables.default is not None and
                sameProxiedObjects(oldTimetables.default, schooltt)):
                newTimetables.default = newSchooltt

    def importGroupMembers(self, sourceGroup, targetGroup):
        for member in sourceGroup.members:
            targetGroup.members.add(member)

    def importGroup(self, groupId, shouldImportMembers=False):
        oldGroups = IGroupContainer(self.activeSchoolyear)
        newGroups = IGroupContainer(self.newSchoolyear)
        if groupId in oldGroups:
            oldGroup = oldGroups[groupId]
            newGroup = newGroups[groupId] = Group(oldGroup.title,
                                                   oldGroup.description)
            if shouldImportMembers:
                self.importGroupMembers(oldGroup, newGroup)

    def importCustomGroups(self):
        for groupId in self.customGroupsToImport:
            shouldImportMembers = groupId in self.groupsWithMembersToImport
            self.importGroup(groupId, shouldImportMembers)

    def importDefaultGroupsMembers(self):
        oldGroups = IGroupContainer(self.activeSchoolyear)
        newGroups = IGroupContainer(self.newSchoolyear)
        for groupId in defaultGroups:
            if groupId in oldGroups and groupId in self.groupsWithMembersToImport:
                oldGroup = oldGroups[groupId]
                newGroup = newGroups[groupId]
                self.importGroupMembers(oldGroup, newGroup)

    def shouldImportData(self):
        return self.activeSchoolyear is not None and \
               not sameProxiedObjects(self.activeSchoolyear, self.newSchoolyear)

    def shouldImportAllCourses(self):
        return 'importAllCourses' in self.request and \
               self.hasCourses(self.activeSchoolyear)

    def shouldImportAllTimetables(self):
        return 'importAllTimetables' in self.request and \
               self.hasTimetableSchemas(self.activeSchoolyear)

    @property
    def customGroupsToImport(self):
        result = self.request.get('groups', [])
        if not isinstance(result, list):
            result = [result]
        return result

    @property
    def groupsWithMembersToImport(self):
        result = self.request.get('members', [])
        if not isinstance(result, list):
            result = [result]
        return result

    def importData(self, newSchoolyear):
        self.newSchoolyear = newSchoolyear
        self.activeSchoolyear = self.context.getActiveSchoolYear()
        if self.shouldImportData():
            self.importAllCourses()
            self.importAllTimetables()
            self.importCustomGroups()
            self.importDefaultGroupsMembers()


class SchoolYearAddView(form.AddForm, ImportSchoolYearData):
    """School Year add form for school years."""
    label = _("Add new school year")
    template = ViewPageTemplateFile('templates/schoolyear_add.pt')

    fields = field.Fields(ISchoolYearAddForm)

    def updateActions(self):
        super(SchoolYearAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        obj = self.createAndAdd(data)

        if obj is not None:
            # mark only as finished if we get the new object
            self._finishedAdd = True

    def create(self, data):
        schoolyear = SchoolYear(data['title'], data['first'], data['last'])
        form.applyChanges(self, schoolyear, data)
        self._schoolyear = schoolyear
        return schoolyear

    def nextURL(self):
        return absoluteURL(self._schoolyear, self.request)

    def add(self, schoolyear):
        """Add `schoolyear` to the container."""
        chooser = INameChooser(self.context)
        name = chooser.chooseName(schoolyear.title, schoolyear)
        self.context[name] = schoolyear
        self.importData(schoolyear)
        return schoolyear

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class FlourishSchoolYearAddView(flourish.form.AddForm, SchoolYearAddView):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('School Year Details')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishSchoolYearAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        super(FlourishSchoolYearAddView, self).handle_cancel_action.func(self,
            action)

    def updateWidgets(self):
        super(FlourishSchoolYearAddView, self).updateWidgets()
        self.widgets['title'].maxlength = 12
        title_description =  _('Limited to 12 characters or less')
        self.widgets['title'].field.description = title_description


class SchoolYearEditView(form.EditForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/schoolyear_edit.pt')

    fields = field.Fields(ISchoolYearAddForm)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SchoolYearEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def label(self):
        return _(u'Change information for ${schoolyear_title}',
                 mapping={'schoolyear_title': self.context.title})


class FlourishSchoolYearEditView(flourish.form.Form, SchoolYearEditView):
    """flourish Edit form for schoolyear."""

    template = InheritTemplate(flourish.page.Page.template)
    label = None

    def update(self):
        SchoolYearEditView.update(self)

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishSchoolYearEditView, self).handleApply.func(self, action)
        if self.status == self.successMessage:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateWidgets(self):
        super(FlourishSchoolYearEditView, self).updateWidgets()
        self.widgets['title'].maxlength = 12
        title_description =  _('Limited to 12 characters or less')
        self.widgets['title'].field.description = title_description

    @property
    def legend(self):
        return _(u'Change information for ${schoolyear_title}',
                 mapping={'schoolyear_title': self.context.title})


class AddSchoolYearOverlapValidator(InvariantsValidator):

    def validateObject(self, obj):
        errors = super(AddSchoolYearOverlapValidator, self).validateObject(obj)
        try:
            dr = DateRange(obj.first, obj.last)
            try:
                validateScholYearsForOverlap(self.view.context, dr, None)
            except SchoolYearOverlapError, e:
                errors += (e, )
        except ValueError, e:
            errors += (Invalid(_("School year must begin before it ends.")), )
        except NoInputData:
            return errors
        return errors

WidgetsValidatorDiscriminators(
    AddSchoolYearOverlapValidator,
    view=SchoolYearAddView,
    schema=getSpecification(ISchoolYearAddForm, force=True))


class EditSchoolYearValidator(InvariantsValidator):

    def validateObject(self, obj):
        errors = super(EditSchoolYearValidator, self).validateObject(obj)
        try:
            dr = DateRange(obj.first, obj.last)
            try:
                validateScholYearsForOverlap(self.view.context.__parent__, dr, self.view.context)
            except SchoolYearOverlapError, e:
                errors += (e, )

            try:
                validateScholYearForOverflow(dr, self.view.context)
            except TermOverflowError, e:
                errors += (e, )
        except ValueError, e:
            errors += (Invalid(_("School year must begin before it ends.")), )
        except NoInputData:
            return errors
        return errors


WidgetsValidatorDiscriminators(
    EditSchoolYearValidator,
    view=SchoolYearEditView,
    schema=getSpecification(ISchoolYearAddForm, force=True))


class FlourishInvalidDateRangeError(ValidationError):
    __doc__ = _('School year must begin before it ends')


class FlourishOverlapError(ValidationError):
    __doc__ = _('Date range overlaps another school year')


class FlourishOverflowError(ValidationError):
    __doc__ = _('Date range too small to contain the currently set up term(s)')


class FlourishOverlapValidator(SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the overlap error next to the widget!
        rv = super(FlourishOverlapValidator, self).validate(value)
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
            validateScholYearsForOverlap(self.container, dr, self.schoolyear)
        except SchoolYearOverlapError, e:
            raise FlourishOverlapError()
        if self.schoolyear:
            try:
                validateScholYearForOverflow(dr, self.schoolyear)
            except TermOverflowError, e:
                raise FlourishOverflowError()


class FlourishOverlapAddValidator(FlourishOverlapValidator):
    schoolyear = None

    @property
    def container(self):
        return self.context


class FlourishOverlapEditValidator(FlourishOverlapValidator):

    @property
    def schoolyear(self):
        return self.context

    @property
    def container(self):
        return self.context.__parent__


WidgetValidatorDiscriminators(FlourishOverlapAddValidator,
                              view=FlourishSchoolYearAddView,
                              field=ISchoolYearAddForm['first'])


WidgetValidatorDiscriminators(FlourishOverlapEditValidator,
                              view=FlourishSchoolYearEditView,
                              field=ISchoolYearAddForm['first'])


class OverlapErrorViewSnippet(ErrorViewSnippet):

    adapts(SchoolYearOverlapError, None, None, None, None, None)

    render = ViewPageTemplateFile("templates/school_year_overlap_error.pt")

    def schoolyears(self):
        return self.context.overlapping_schoolyears

    def createMessage(self):
        return self.context.__repr__()


class OverflowErrorViewSnippet(ErrorViewSnippet):

    adapts(TermOverflowError, None, None, None, None, None)

    render = ViewPageTemplateFile("templates/term_overflow_error.pt")

    def terms(self):
        return self.context.overflowing_terms

    def createMessage(self):
        return self.context.__repr__()


class SchoolYearView(TableContainerView):
    """School Year view."""

    __used_for__ = ISchoolYear
    delete_template = ViewPageTemplateFile("templates/term-delete.pt")
    template = ViewPageTemplateFile("templates/schoolyear.pt")

    index_title = _("School Year")

    @property
    def sorted_terms(self):
        return sorted(self.context.values(), key=lambda t: t.last)

    @property
    def first(self):
        return self.context.first

    @property
    def last(self):
        return self.context.last

    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                del self.context[key]


class SchoolYearViewMenuViewletManager(OrderedViewletManager):
    """Viewlet manager for displaying the various menus at the top of a page."""

    implements(ISchoolYearViewMenuViewletManager)


class ActiveSchoolYears(ViewletBase):

    def activeSchoolYear(self):
        """Return the active school year."""
        return ISchoolYearContainer(ISchoolToolApplication(None)).getActiveSchoolYear()

    def nextSchoolYear(self):
        """Return the next school year."""
        syc = ISchoolYearContainer(ISchoolToolApplication(None))
        if checkPermission("schooltool.edit", syc):
            return syc.getNextSchoolYear()


class FlourishManageYearOverview(flourish.page.Content,
                                 ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_year_overview.pt')


class FlourishSchoolYearView(flourish.page.Page):
    """flourish SchoolYear view."""

    @property
    def subtitle(self):
        return self.context.title


class FlourishSchoolYearDetails(flourish.form.FormViewlet):

    fields = field.Fields(ISchoolYearAddForm).omit('title')
    template = ViewPageTemplateFile("templates/f_schoolyear.pt")
    mode = DISPLAY_MODE

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishSchoolYearActivateView(flourish.page.Page):

    message = None

    def years(self):
        for year in reversed(tuple(self.context.values())):
            yield {
                'obj': year,
                'active': year.__name__ == year.__parent__.active_id,
                }

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        if 'SUBMIT' in self.request:
            if self.request.get('ACTIVATE'):
                self.context.activateNextSchoolYear(self.request['ACTIVATE'])
                self.request.response.redirect(self.nextURL())
            else:
                self.message = _("Please select a school year before clicking "
                                 "'Submit'.")

    def nextURL(self):
        next = self.request.get('next')
        if next:
            app_url = absoluteURL(ISchoolToolApplication(None), self.request)
            return app_url + '/' + next
        return absoluteURL(self.context, self.request)


class ManageSchoolTertiaryNavigation(flourish.page.Content,
                                     flourish.page.TertiaryNavigationManager,
                                     ActiveSchoolYearContentMixin):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class"
            tal:condition="view/items">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class">
              <a tal:attributes="href item/url"
                 tal:content="item/schoolyear/@@title" />
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        active = self.schoolyear
        schoolyears = active.__parent__ if active is not None else {}
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'manage',
                schoolyear.__name__)
            css_class = schoolyear.first == active.first and 'active' or None
            result.append({
                    'class': css_class,
                    'url': url,
                    'schoolyear': schoolyear,
                    })
        return result


class SchoolyearNavBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    traversal_name = u''

    @property
    def schoolyear_id(self):
        sy = ISchoolYear(self.context, None)
        if sy is None:
            return u''
        return sy.__name__

    @property
    def crumb_parent(self):
        return ISchoolToolApplication(None)

    @property
    def url(self):
        if not self.checkPermission():
            return False
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        link = '%s/%s' % (app_url, self.traversal_name)
        sy_id = self.schoolyear_id
        if sy_id:
            link += '?schoolyear_id=%s' % sy_id
        return link


class FlourishSchoolYearsOverview(flourish.page.Content):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_schoolyears_overview.pt')

    @Lazy
    def schoolyears(self):
        syc = ISchoolYearContainer(self.context)
        return syc


class SchoolYearAddLink(flourish.page.LinkViewlet):

    @property
    def url(self):
        schoolyears = ISchoolYearContainer(self.context)
        return absoluteURL(schoolyears, self.request) + '/add.html'


class FlourishActivateNewYearLink(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        if not flourish.canEdit(self.schoolyears):
            return False
        return super(FlourishActivateNewYearLink, self).enabled

    @property
    def schoolyears(self):
        return ISchoolYearContainer(ISchoolToolApplication(None))

    @property
    def url(self):
        link = self.link
        if not link:
            return None
        return "%s/%s?next=%s" % (
            absoluteURL(self.schoolyears, self.request),
            self.link,
            self.view.__name__)
