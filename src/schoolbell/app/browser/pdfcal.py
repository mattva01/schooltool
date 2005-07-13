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

from cStringIO import StringIO

from zope.app.publisher.browser import BrowserView
from schoolbell.app.interfaces import ISchoolBellCalendar
from schoolbell.calendar.utils import parse_date

global disabled
disabled = False

try:
    import reportlab
except ImportError:
    disabled = True
else:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.platypus import Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.rl_config import defaultPageSize
    from reportlab.lib.units import cm

disabled = False
# TODO: handle this flag

SANS = 'Arial_Normal'
SANS_OBLIQUE = 'Arial_Italic'
SANS_BOLD = 'Arial_Bold'
SERIF = 'Times_New_Roman'


class DailyCalendarView(BrowserView):

    __used_for__ = ISchoolBellCalendar

    def pdfdata(self):
        """Return the PDF representation of a calendar."""
        date = parse_date(self.request['date']) # TODO: default to today

        datafile = StringIO()
        doc = SimpleDocTemplate(datafile)

        story = self.buildStory(date)
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

    def buildStory(self, date):
        """Build a platypus story."""
        owner = self.context.__parent__

        # TODO: fix style variable names, do not use sample stylesheet
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontName = SANS
        style_italic = styles["Italic"]
        style_italic.fontName = SANS_OBLIQUE
        style_title = styles["Title"]
        style_title.fontName = SANS_BOLD

        # TODO: Use a hires logo, this one is too blurry.
        logo_path = os.path.join(os.path.dirname(__file__),
                                 'resources', 'logo.png')
        logo = Image(logo_path)
        logo.hAlign = 'LEFT'

        story = [logo,
                 Paragraph(owner.title.encode('utf-8'), style_title),
                 Paragraph(date.isoformat(), style_title),
                 Spacer(0, 1 * cm)]

        events = [event for event in self.context
                  if event.dtstart.date() == date]
        events.sort() # TODO: test sort

        if events:
            rows = []
            for event in events:
                title = event.title.encode('utf-8')
                text_cell = [Paragraph(title, style)]
                if event.description:
                    description = event.description.encode('utf-8')
                    text_cell.append(Paragraph(description, style_italic))
                if event.resources:
                    # TODO: i18n
                    resource_titles = [resource.title
                                       for resource in event.resources]
                    resources = 'Booked: ' + ', '.join(resource_titles)
                    text_cell.append(Paragraph(resources.encode('utf-8'),
                                               style))
                # TODO: show recurrence

                dtend = event.dtstart + event.duration
                time = "%s-%s" % (event.dtstart.strftime('%H:%M'),
                                  dtend.strftime('%H:%M'))
                rows.append([Paragraph(time, style_italic), text_cell])

            tstyle = TableStyle([('BOX', (0,0), (-1,-1), 0.25, colors.black),
                           ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                           ('VALIGN', (0,0), (0,-1), 'TOP')])
            table = Table(rows, colWidths=(3 * cm, 10 * cm), style=tstyle)
            story.append(table)

        return story


# ------------------
# Font configuration
# ------------------

import os.path
import reportlab.rl_config
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping


def registerTTFont(fontname, filename):
    """Register a TrueType font with ReportLab.

    Clears up the incorrect straight-through mappings that ReportLab 1.19
    unhelpfully gives us.
    """
    pdfmetrics.registerFont(TTFont(fontname, filename))
    # For some reason pdfmetrics.registerFont for TrueType fonts explicitly
    # calls addMapping with incorrect straight-through mappings, at least in
    # reportlab version 1.19.  We thus need to stick our dirty fingers in
    # reportlab's internal data structures and undo those changes so that we
    # can call addMapping with correct values.
    key = fontname.lower()
    del reportlab.lib.fonts._tt2ps_map[key, 0, 0]
    del reportlab.lib.fonts._tt2ps_map[key, 0, 1]
    del reportlab.lib.fonts._tt2ps_map[key, 1, 0]
    del reportlab.lib.fonts._tt2ps_map[key, 1, 1]
    del reportlab.lib.fonts._ps2tt_map[key]


def registerFontPath(directory):
    if not os.path.isdir(directory):
        # TODO: make the error friendlier
        raise ValueError("Directory '%s' does not exist." % directory)
    else:
        ttfpath = reportlab.rl_config.TTFSearchPath
        ttfpath.append(directory)


def setUpMSTTCoreFonts():
    """Set up ReportGen to use MSTTCoreFonts"""
    reportlab.rl_config.warnOnMissingFontGlyphs = 0

    # 'Arial' is predefined in ReportLab, so we use 'Arial_Normal'

    registerTTFont('Arial_Normal', 'arial.ttf')
    registerTTFont('Arial_Bold', 'arialbd.ttf')
    registerTTFont('Arial_Italic', 'ariali.ttf')
    registerTTFont('Arial_Bold_Italic', 'arialbi.ttf')

    addMapping('Arial_Normal', 0, 0, 'Arial_Normal')
    addMapping('Arial_Normal', 0, 1, 'Arial_Italic')
    addMapping('Arial_Normal', 1, 0, 'Arial_Bold')
    addMapping('Arial_Normal', 1, 1, 'Arial_Bold_Italic')

    registerTTFont('Times_New_Roman', 'times.ttf')
    registerTTFont('Times_New_Roman_Bold', 'timesbd.ttf')
    registerTTFont('Times_New_Roman_Italic', 'timesi.ttf')
    registerTTFont('Times_New_Roman_Bold_Italic', 'timesbi.ttf')

    addMapping('Times_New_Roman', 0, 0, 'Times_New_Roman')
    addMapping('Times_New_Roman', 0, 1, 'Times_New_Roman_Italic')
    addMapping('Times_New_Roman', 1, 0, 'Times_New_Roman_Bold')
    addMapping('Times_New_Roman', 1, 1, 'Times_New_Roman_Bold_Italic')
