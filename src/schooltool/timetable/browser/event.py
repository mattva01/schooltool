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

from zope.app import zapi
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import Interface
from zope.schema import Text
from zope.formlib import form

from schooltool.app.browser.cal import CalendarEventView
from schooltool import SchoolToolMessage as _

class IEditTimetableEvent(Interface):

    description = Text(
        title=_("Description"),
        required=False)


class TimetableEventEditView(CalendarEventView, form.Form):

    title = _("Modify event information")

    form_fields = form.fields(Text(__name__='description',
                                   title=_("Description"),
                                   required=False))
    template = ViewPageTemplateFile("templates/timetable_event_edit.pt")

    def setUpWidgets(self, ignore_request=False):
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request=ignore_request)

    def __init__(self, context, request):
        form.Form.__init__(self, context, request)
        CalendarEventView.__init__(self, context, request)

    def redirect_to_parent(self):
        url = zapi.absoluteURL(self.context.__parent__, self.request)
        self.request.response.redirect(url)
        return ''

    @form.action(_("Apply"))
    def handle_edit_action(self, action, data):
        self.context.description = data['description']
        return self.redirect_to_parent()

    @form.action(_("Cancel"), condition=form.haveInputWidgets)
    def handle_cancel_action(self, action, data):
        return self.redirect_to_parent()
