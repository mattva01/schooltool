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
from zope.component import adapts
from zope.security import checkPermission
from zope.schema import Date, TextLine
from zope.interface import implements
from zope.interface import Interface
from zope.traversing.browser.absoluteurl import AbsoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.app.container.interfaces import INameChooser
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import form, field, button
from z3c.form.util import getSpecification
from z3c.form.validator import WidgetsValidatorDiscriminators
from z3c.form.validator import InvariantsValidator
from z3c.form.error import ErrorViewSnippet

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
from schooltool.common import DateRange
from schooltool.common import SchoolToolMessage as _


class SchoolYearContainerAbsoluteURLAdapter(AbsoluteURL):

    adapts(ISchoolYearContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def _getContextName(self, context):
        return 'schoolyears'


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

    def setUpTableFormatter(self, formatter):
        columns_before = []
        if self.canModify():
            columns_before = [DependableCheckboxColumn(prefix="delete",
                                                       name='delete_checkbox',
                                                       title=u'')]
        columns_after = [DateColumn(title="Starts", getter=lambda x, y: x.first),
                         DateColumn(title="Ends", getter=lambda x, y: x.last)]
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

    def update(self):
        if 'ACTIVATE_NEXT_SCHOOLYEAR' in self.request:
            self.context.activateNextSchoolYear()


class ISchoolYearAddForm(Interface):

    title = TextLine(
        title=_("Title"))

    first = Date(
        title=u"First day")

    last = Date(
        title=u"Last day")


class SchoolYearAddFormAdapter(object):
    implements(ISchoolYearAddForm)
    adapts(ISchoolYear)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __setattr__(self, name, value):
        setattr(self.context, name, value)

    def __getattr__(self, name):
        return getattr(self.context, name)


class SchoolYearAddView(form.AddForm):
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
        return schoolyear

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class SchoolYearEditView(form.EditForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/schoolyear_add.pt')

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


class AddSchoolYearOverlapValidator(InvariantsValidator):

    def validateObject(self, obj):
        errors = super(AddSchoolYearOverlapValidator, self).validateObject(obj)
        dr = DateRange(obj.first, obj.last)
        try:
            validateScholYearsForOverlap(self.view.context, dr, None)
        except SchoolYearOverlapError, e:
            errors += (e, )
        return errors

WidgetsValidatorDiscriminators(
    AddSchoolYearOverlapValidator,
    view=SchoolYearAddView,
    schema=getSpecification(ISchoolYearAddForm, force=True))


class EditSchoolYearValidator(InvariantsValidator):

    def validateObject(self, obj):
        errors = super(EditSchoolYearValidator, self).validateObject(obj)
        dr = DateRange(obj.first, obj.last)
        try:
            validateScholYearsForOverlap(self.view.context.__parent__, dr, self.view.context)
        except SchoolYearOverlapError, e:
            errors += (e, )

        try:
            validateScholYearForOverflow(dr, self.view.context)
        except TermOverflowError, e:
            errors += (e, )
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
