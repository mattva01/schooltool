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
SchoolBell calendar views.

$Id$
"""

from StringIO import StringIO

# TODO: make things work without reportlab installed
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import cm

from zope.app.publisher.browser import BrowserView
from schoolbell.app.interfaces import ISchoolBellCalendar

styles = getSampleStyleSheet()


class DailyCalendarView(BrowserView):

    __used_for__ = ISchoolBellCalendar

    def pdfdata(self):
        """Return the PDF representation of a calendar."""
        datafile = StringIO()
        doc = SimpleDocTemplate(datafile)

        story = self.buildStory()
        doc.build(story)

        data = datafile.getvalue()
        self.setUpPDFHeaders(data)
        return data

    def setUpPDFHeaders(self, data):
        """Set up headers to serve data as PDF."""
        response = self.request.response
        response.setHeader('Content-Type', 'application/pdf')
        response.setHeader('Content-Length', len(data))
        # We don't really accept ranges, but Acrobat Reader will not show the
        # report in the browser page if this header is not provided.
        response.setHeader('Accept-Ranges', 'bytes')

    def buildStory(self):
        owner = self.context.__parent__
        date = self.request['date']

        story = [Paragraph(owner.title, styles["Normal"]),
                 Paragraph(date, styles["Normal"])]

        for event in self.context:
            start = event.dtstart.strftime('%H:%M')
            text = '<i>%s</i> %s' % (event.dtstart, event.title)
            story.append(Paragraph(text, styles["Normal"]))
        return story
