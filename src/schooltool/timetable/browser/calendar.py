#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Timetabling calendar integration.
"""

import zope.schema
from zope.app.form.browser.add import AddView
from zope.interface import Interface
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.formlib import form
from zope.html.field import HtmlFragment
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.session.interfaces import ISession

from schooltool.app.browser import ViewPreferences
from schooltool.app.browser.cal import CalendarEventView
from schooltool.app.browser.cal import CalendarEventViewMixin
from schooltool.app.utils import vocabulary
from schooltool.term.interfaces import IDateManager

from schooltool.common import SchoolToolMessage as _


class ScheduleEventEditView(CalendarEventView, form.Form):

    title = _("Modify meeting information")

    form_fields = form.fields(HtmlFragment(
            __name__='description',
            title=_("Description"),
            required=False))

    template = ViewPageTemplateFile("templates/schedule_event_edit.pt")

    def setUpWidgets(self, ignore_request=False):
        self.widgets = form.setUpEditWidgets(
            self.form_fields, self.prefix, self.context, self.request,
            ignore_request=ignore_request)

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


class IScheduleEventAddForm(Interface):
    """Schema for schedule calendar event adding form."""

    title = zope.schema.TextLine(
        title=_("Title"),
        required=False)
    allday = zope.schema.Bool(
        title=_("All day"),
        required=False)
    start_date = zope.schema.Date(
        title=_("Date"),
        required=False)
    start_time = zope.schema.TextLine(
        title=_("Time"),
        description=_("Start time in 24h format"),
        required=False)

    duration = zope.schema.Int(
        title=_("Duration"),
        required=False,
        default=60)

    duration_type = zope.schema.Choice(
        title=_("Duration Type"),
        required=False,
        default="minutes",
        vocabulary=vocabulary([("minutes", _("Minutes")),
                               ("hours", _("Hours")),
                               ("days", _("Days"))]))

    location = zope.schema.TextLine(
        title=_("Location"),
        required=False)

    description = HtmlFragment(
        title=_("Description"),
        required=False)


class ScheduleEventAddView(CalendarEventViewMixin, AddView):
    """A view for adding an event."""

    schema = IScheduleEventAddForm

    title = _("Add meeting")
    submit_button_title = _("Add")

    show_book_checkbox = True
    show_book_link = False
    _event_uid = None

    error = None

    def __init__(self, context, request):

        prefs = ViewPreferences(request)
        self.timezone = prefs.timezone

        if "field.start_date" not in request:
            # XXX: shouldn't use date.today; it depends on the server's timezone
            # which may not match user expectations
            today = getUtility(IDateManager).today.strftime("%Y-%m-%d")
            request.form["field.start_date"] = today
        super(AddView, self).__init__(context, request)

    def create(self, **kwargs):
        """Create an event."""
        data = self.processRequest(kwargs)
        event = self._factory(data['start'], data['duration'], data['title'],
                              location=data['location'],
                              allday=data['allday'],
                              description=data['description'])
        # XXX: also meeting id! Don't forget the meeting id.
        return event

    def add(self, event):
        self.context.addEvent(event)
        uid = event.unique_id
        self._event_name = event.__name__
        session_data = ISession(self.request)['schooltool.calendar']
        session_data.setdefault('added_event_uids', set()).add(uid)
        return event

    def update(self):
        if 'UPDATE' in self.request:
            return self.updateForm()
        elif 'CANCEL' in self.request:
            self.update_status = ''
            self.request.response.redirect(self.nextURL())
            return self.update_status
        else:
            return AddView.update(self)

    def nextURL(self):
        if "field.book" in self.request:
            url = absoluteURL(self.context, self.request)
            return '%s/%s/booking.html' % (url, self._event_name)
        else:
            return absoluteURL(self.context, self.request)
