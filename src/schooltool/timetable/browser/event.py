#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Views for timetable event.

$Id$
"""

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter
from zope.interface import Interface
from zope.schema import Text
from zope.formlib import form
from zope.html.field import HtmlFragment
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.skin.containers import TableContainerView
from schooltool.app.browser.cal import CalendarEventView
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import SchoolToolMessage as _
from schooltool.timetable.interfaces import ITimetableDict, ITimetable
from schooltool.table.interfaces import ITableFormatter
from schooltool.table.table import DependableCheckboxColumn
from schooltool.table.table import url_cell_formatter

class TimetableContainerView(TableContainerView):
    """Timetable Container View."""

    __used_for__ = ITimetableDict
    delete_template = ViewPageTemplateFile("templates/timetable-container-delete.pt")
    view_template = ViewPageTemplateFile("templates/timetable_list.pt")
    index_title = _("Timetables")


    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                del self.context[key]


class TimetableEventEditView(CalendarEventView, form.Form):

    title = _("Modify event information")

    form_fields = form.fields(HtmlFragment(__name__='description',
                                           title=_("Description"),
                                           required=False))
    template = ViewPageTemplateFile("templates/timetable_event_edit.pt")

    def setUpEditorWidget(self, editor):
        editor.editorWidth = 430
        editor.editorHeight = 300
        editor.toolbarConfiguration = "schooltool"
        url = absoluteURL(ISchoolToolApplication(None), self.request)
        editor.configurationPath = (url + '/@@/editor_config.js')

    def setUpWidgets(self, ignore_request=False):
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request=ignore_request)
        self.setUpEditorWidget(self.widgets["description"])

    def __init__(self, context, request):
        form.Form.__init__(self, context, request)
        CalendarEventView.__init__(self, context, request)

    def redirect_to_parent(self):
        url = absoluteURL(self.context.__parent__, self.request)
        self.request.response.redirect(url)
        return ''

    @form.action(_("Apply"))
    def handle_edit_action(self, action, data):
        self.context.description = data['description']
        return self.redirect_to_parent()

    @form.action(_("Cancel"), condition=form.haveInputWidgets)
    def handle_cancel_action(self, action, data):
        return self.redirect_to_parent()

