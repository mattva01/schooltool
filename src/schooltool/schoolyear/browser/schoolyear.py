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
Views for school years and school year container implementation
"""
from zope.viewlet.viewlet import ViewletBase
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts, getMultiAdapter
from zope.security import checkPermission
from zope.schema import Date, TextLine
from zope.interface.exceptions import Invalid
from zope.interface import implements
from zope.interface import Interface
from zope.traversing.browser.absoluteurl import AbsoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.container.interfaces import INameChooser
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.proxy import sameProxiedObjects
from zope.i18n.interfaces.locales import ICollator
from zope.security.checker import canAccess

from z3c.form import form, field, button
from z3c.form.util import getSpecification
from z3c.form.validator import NoInputData
from z3c.form.validator import WidgetsValidatorDiscriminators
from z3c.form.validator import InvariantsValidator
from z3c.form.error import ErrorViewSnippet

from zc.table import column

import schooltool.skin.flourish.containers
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.demographics.browser.table import DateColumn
from schooltool.table.table import url_cell_formatter
from schooltool.table.table import DependableCheckboxColumn
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
from schooltool.common import DateRange
from schooltool.common import SchoolToolMessage as _
from schooltool.common.inlinept import InheritTemplate
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.course import Course
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.group import Group, defaultGroups


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
            columns_before = [DependableCheckboxColumn(prefix="delete",
                                                       name='delete_checkbox',
                                                       title=u'')]
        columns_after = [DateColumn(title=_("Starts"),
                                    getter=lambda x, y: x.first),
                         DateColumn(title=_("Ends"),
                                    getter=lambda x, y: x.last)]
        formatter.setUp(formatters=[url_cell_formatter],
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


class FlourishActiveSchoolYearColumn(column.Column):
    """Table column that displays whether a schoolyear is the active one.
    """

    def renderCell(self, item, formatter):
        if item.__parent__.active_id == item.__name__:
            return '<span class="ui-icon ui-icon-check"></span>'
        else:
            return ''


class FlourishSchoolYearContainerView(flourish.containers.TableContainerView):
    """flourish SchoolYear container view."""

    def setUpTableFormatter(self, formatter):
        columns_after = [
            DateColumn(title=_("First Day"),
                       getter=lambda x, y: x.first),
            DateColumn(title=_("Last Day"),
                       getter=lambda x, y: x.last),
            FlourishActiveSchoolYearColumn(title=_("Active")),
            ]
        formatter.setUp(formatters=[url_cell_formatter],
                        columns_after=columns_after)


class FlourishSchoolYearContainerLinks(flourish.page.RefineLinksViewlet):
    """SchoolYear container links viewlet."""


class FlourishSchoolYearContainerActionLinks(flourish.page.RefineLinksViewlet):
    """SchoolYear container action links viewlet."""


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
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.interfaces import ITimetableSchemaContainer
        timetables = ITimetableSchemaContainer(schoolyear)
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
            newCourses[course.__name__] = Course(course.title, course.description)

    def importAllTimetables(self):
        # XXX: temporary isolation of timetable imports
        from schooltool.timetable.interfaces import ITimetableSchemaContainer
        # XXX: would be nice to replace with something else
        from schooltool.timetable.schema import locationCopy

        if not self.shouldImportAllTimetables():
            return
        oldTimetables = ITimetableSchemaContainer(self.activeSchoolyear)
        newTimetables = ITimetableSchemaContainer(self.newSchoolyear)
        for schooltt in oldTimetables.values():
            newSchooltt = locationCopy(schooltt)
            newSchooltt.__parent__ = None
            newTimetables[newSchooltt.__name__] = newSchooltt

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
            #self.importAllTimetables()
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
    legend = 'School Year Details'

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishSchoolYearAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        super(FlourishSchoolYearAddView, self).handle_cancel_action.func(self,
            action)


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


class FlourishSchoolYearEditView(flourish.page.Page, SchoolYearEditView):
    """flourish Edit form for schoolyear."""

    def update(self):
        SchoolYearEditView.update(self)

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishSchoolYearEditView, self).handleApply.func(self, action)
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


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


class FlourishSchoolYearView(flourish.page.Page):
    """flourish SchoolYear view."""

    fields = field.Fields(ISchoolYearAddForm).omit('title')

    @property
    def subtitle(self):
        return self.context.title

    def makeRow(self, attr, value):
        if value is None:
            value = u''
        return {
            'label': attr,
            'value': unicode(value),
            }

    @property
    def table(self):
        rows = []
        for attr in self.fields:
            value = getattr(self.context, attr)
            if value:
                label = self.fields[attr].field.title
                rows.append(self.makeRow(label, value))
        return rows

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

