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
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.component import adapts
from zope.schema import Date, TextLine
from zope.interface import implements
from zope.interface import Interface
from zope.traversing.browser.absoluteurl import AbsoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.app.container.interfaces import INameChooser
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import form, field, button

from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin.containers import TableContainerView
from schooltool.common import SchoolToolMessage as _


class ScholYearContainerAbsoluteURLAdapter(AbsoluteURL):

    adapts(ISchoolYearContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def _getContextName(self, context):
        return 'schoolyears'


class SchoolYearContainerView(TableContainerView):
    """SchoolYear container view."""

    __used_for__ = ISchoolYearContainer

    index_title = _("School Years")


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
        # XXX validation upon cancellation doesn't make any sense
        # how to make this work properly?
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)
