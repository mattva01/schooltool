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
"""Emergency Day Views

$Id$
"""
import datetime

from zope.i18n import translate
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool.common import SchoolToolMessage as _
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.cal import CalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.calendar.utils import parse_date
from schooltool.term.interfaces import ITerm
from schooltool.timetable import SchooldayTemplate


class EmergencyDayView(BrowserView):
    """On emergencies such as extreme temperetures, blizzards, etc,
    school is cancelled, and a different day gets added to the term
    instead.

    This view lets the administrator choose the cancelled date and
    presents the user with a choice of non-schooldays within a term
    and the days immediately after the term.
    """

    __used_for__ = ITerm

    template = None
    date_template = ViewPageTemplateFile('emergency_select.pt')
    replacement_template = ViewPageTemplateFile('emergency2.pt')

    error = None
    date = None
    replacement = None

    def replacements(self):
        """Return all non-schooldays in term plus 3 days after the term."""
        result = []
        for date in self.context:
            if date > self.date:
                if not self.context.isSchoolday(date):
                    result.append(date)
        last = self.context.last
        day = datetime.timedelta(1)
        result.append(last + day)
        result.append(last + 2 * day)
        result.append(last + 3 * day)
        return result

    def update(self):
        self.template = self.date_template
        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
            return
        if 'date' in self.request:
            try:
                self.date = parse_date(self.request['date'])
            except ValueError:
                self.error = _("The date you entered is invalid."
                               "  Please use the YYYY-MM-DD format.")
                return
            if not self.date in self.context:
                self.error = _("The date you entered does not belong to"
                               " this term.")
                return
            if not self.context.isSchoolday(self.date):
                self.error = _("The date you entered is not a schoolday.")
                return

            self.template = self.replacement_template
        if 'replacement' in self.request:
            try:
                self.replacement = parse_date(self.request['replacement'])
            except ValueError:
                self.error = _("The replacement date you entered is invalid.")
                return

        if self.date and self.replacement:
            if self.context.last < self.replacement:
                self.context.last = self.replacement
            assert not self.context.isSchoolday(self.replacement)
            assert self.context.isSchoolday(self.date)
            self.context.add(self.replacement)

            # Update all schemas
            ttschemas = getSchoolToolApplication()['ttschemas']
            for schema in ttschemas.values():
                model = schema.model
                exceptionDays = removeSecurityProxy(model.exceptionDays)
                exceptionDayIds = removeSecurityProxy(model.exceptionDayIds)
                exceptionDays[self.date] = SchooldayTemplate()
                day_id = model.getDayId(self.context, self.date)
                exceptionDayIds[self.replacement] = removeSecurityProxy(day_id)

            # Post calendar events to schoolwide calendar
            calendar = ISchoolToolCalendar(getSchoolToolApplication())
            dtstart = datetime.datetime.combine(self.date, datetime.time())
            msg = _('School cancelled due to emergency.'
                    ' Replacement day $replacement.',
                    mapping={'replacement': str(self.replacement)})
            msg = translate(msg, context=self.request)
            calendar.addEvent(
                CalendarEvent(dtstart, datetime.timedelta(),
                              msg, allday=True))

            dtstart = datetime.datetime.combine(self.replacement,
                                                datetime.time())
            msg = _('Replacement day for emergency day $emergency.',
                    mapping={'emergency': str(self.date)})
            msg = translate(msg, context=self.request)
            calendar.addEvent(
                CalendarEvent(dtstart, datetime.timedelta(),
                              msg, allday=True))

            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))



    def __call__(self):
        self.update()
        return self.template()
