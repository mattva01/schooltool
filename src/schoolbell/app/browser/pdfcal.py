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

import os.path
import datetime
from cStringIO import StringIO

from zope.app.publisher.browser import BrowserView
from zope.i18n import translate
from schoolbell.app.interfaces import ISchoolBellCalendar
from schoolbell.calendar.utils import parse_date, week_start
from schoolbell.app.browser.cal import month_names, day_of_week_names
from schoolbell import SchoolBellMessageID as _

global disabled
disabled = True

SANS = 'Arial_Normal'
SANS_OBLIQUE = 'Arial_Italic'
SANS_BOLD = 'Arial_Bold'
SERIF = 'Times_New_Roman'



class PDFCalendarViewBase(BrowserView):
    """The daily view of a calendar in PDF."""

    # We do imports from reportlab locally to avoid a hard dependency.

    __used_for__ = ISchoolBellCalendar

    title = None # override this in subclasses

    pdf_disabled_text = _("PDF support is disabled."
                          "  It can be enabled by your administrator.")

    def pdfdata(self):
        """Return the PDF representation of a calendar."""
        global disabled
        if disabled:
            return translate(self.pdf_disabled_text, context=self.request)

        from reportlab.platypus import SimpleDocTemplate
        if 'date' in self.request:
            date = parse_date(self.request['date'])
        else:
            date = datetime.date.today()

        datafile = StringIO()
        doc = SimpleDocTemplate(datafile)

        self.configureStyles()
        story = self.buildStory(date)
        doc.build(story)

        data = datafile.getvalue()
        self.setUpPDFHeaders(data)
        return data

    def buildStory(self, date):
        """Build a platypus story that draws the PDF report."""
        owner = self.context.__parent__
        story = self.buildPageHeader(owner.title, date)
        story.extend(self.buildEventTables(date))
        return story

    def configureStyles(self):
        """Store some styles in instance attributes.

        These would be done in the class declaration if we could do a
        global import of ParagraphStyle.
        """
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER

        self.normal_style = ParagraphStyle(name='Normal', fontName=SANS,
                                           fontsize=10, leading=12)
        self.title_style = ParagraphStyle(name='Title', fontName=SANS_BOLD,
                                          parent=self.normal_style,
                                          fontsize=18, leading=22,
                                          alignment=TA_CENTER, spaceAfter=6)
        self.subtitle_style = ParagraphStyle(name='Subtitle',
                                             parent=self.title_style,
                                             spaceBefore=16)
        self.italic_style = ParagraphStyle(name='Italic',
                                           parent=self.normal_style,
                                           fontName=SANS_OBLIQUE)

    def setUpPDFHeaders(self, data):
        """Set up HTTP headers to serve data as PDF."""
        response = self.request.response
        response.setHeader('Content-Type', 'application/pdf')
        response.setHeader('Content-Length', len(data))
        # We don't really accept ranges, but Acrobat Reader will not show the
        # report in the browser page if this header is not provided.
        response.setHeader('Accept-Ranges', 'bytes')
        # TODO: test reports with Acrobat Reader

    def buildPageHeader(self, owner_title, date):
        """Build a story that constructs the top of the first page."""
        from reportlab.platypus import Image, Paragraph
        from reportlab.lib.units import cm

        # TODO: Use a hires logo, this one is too blurry.
        logo_path = os.path.join(os.path.dirname(__file__),
                                 'resources', 'logo.png')
        logo = Image(logo_path)
        logo.hAlign = 'LEFT'

        title = translate(self.title, context=self.request) % owner_title
        date_title = self.dateTitle(date)

        story = [logo,
                 Paragraph(title.encode('utf-8'), self.title_style),
                 Paragraph(date_title.encode('utf-8'), self.title_style)]
        return story

    def buildDayTable(self, events):
        """Return the platypus table that shows events."""
        from reportlab.platypus import Paragraph
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm

        rows = []
        for event in events:
            if event.allday:
                time_cell_text = translate(_("all day"), context=self.request)
            else:
                dtend = event.dtstart + event.duration
                time_cell_text = "%s-%s" % (event.dtstart.strftime('%H:%M'),
                                            dtend.strftime('%H:%M'))
            time_cell = Paragraph(time_cell_text.encode('utf-8'),
                                  self.italic_style)
            text_cell = self.eventInfoCell(event)
            rows.append([time_cell, text_cell])

        tstyle = TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                       ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                       ('VALIGN', (0, 0), (0, -1), 'TOP')])
        table = Table(rows, colWidths=(2.5 * cm, 16 * cm), style=tstyle)
        return table

    def eventInfoCell(self, event):
        """Return the contents of an event information cell."""
        from reportlab.platypus import Paragraph
        title = event.title.encode('utf-8')
        paragraphs = [Paragraph(title, self.normal_style)]
        if event.description:
            description = event.description.encode('utf-8')
            paragraphs.append(Paragraph(description, self.italic_style))
        if event.location:
            location_template = translate(_('Location: %s'),
                                              context=self.request)
            location = location_template % event.location.encode('utf-8')
            paragraphs.append(Paragraph(location, self.normal_style))
        if event.resources:
            resource_titles = [resource.title for resource in event.resources]
            resource_str_template = translate(_('Booked resources: %s'),
                                              context=self.request)
            resources = resource_str_template % ', '.join(resource_titles)
            paragraphs.append(Paragraph(resources.encode('utf-8'),
                                        self.normal_style))
        if event.recurrence:
            recurrent_text = translate(_("(recurrent)"), context=self.request)
            paragraphs.append(Paragraph(recurrent_text.encode('utf-8'),
                                        self.normal_style))
        return paragraphs

    def dayEvents(self, date):
        """Return a list of events that should be shown.

        All-day events are placed in front.
        """
        allday_events = [event for event in self.context
                         if event.dtstart.date() == date and event.allday]
        allday_events.sort()
        events = [event for event in self.context
                  if event.dtstart.date() == date and not event.allday]
        events.sort()
        return allday_events + events

    def daySubtitle(self, date):
        """Return a readable representation of a date.

        This is used in captions for individual days in views that
        span multiple days.
        """
        day_of_week_msgid = day_of_week_names[date.weekday()]
        day_of_week = translate(day_of_week_msgid, context=self.request)
        return "%s, %s" % (date.isoformat(), day_of_week)

    def buildEventTables(self, date): # override in subclasses
        """Return the story that draws events in the current time period."""
        raise NotImplementedError()

    def dateTitle(self, date): # override in subclasses
        """Return the title for the current time period.

        Used at the top of the page.
        """
        raise NotImplementedError()


class DailyPDFCalendarView(PDFCalendarViewBase):

    title = _("Daily calendar for %s")

    def buildEventTables(self, date):
        events = self.dayEvents(date)
        if events:
            return [self.buildDayTable(events)]
        else:
            return []

    dateTitle = PDFCalendarViewBase.daySubtitle


class WeeklyPDFCalendarView(PDFCalendarViewBase):

    title = _("Weekly calendar for %s")

    def dateTitle(self, date):
        year, week = date.isocalendar()[:2]
        start = week_start(date, 0) # TODO: first_day_of_week
        end = start + datetime.timedelta(weeks=1)
        template = translate(_("Week %d (%s - %s), %d"), context=self.request)
        return template % (week, start, end, year)

    def buildEventTables(self, date):
        from reportlab.platypus import Paragraph
        story = []
        start = week_start(date, 0) # TODO: first_day_of_week
        for weekday in range(7):
            day = start + datetime.timedelta(days=weekday)
            events = self.dayEvents(day)
            if events:
                story.append(Paragraph(self.daySubtitle(day),
                                       self.subtitle_style))
                story.append(self.buildDayTable(events))
        return story

class MonthlyPDFCalendarView(PDFCalendarViewBase):

    title = _("Monthly calendar for %s")

    def dateTitle(self, date):
        # TODO: take format from user preferences
        month_name = translate(month_names[date.month], context=self.request)
        return "%s, %d" % (month_name, date.year)

    def buildEventTables(self, date):
        from reportlab.platypus import Paragraph
        story = []
        day = datetime.date(date.year, date.month, 1)
        while day.month == date.month:
            events = self.dayEvents(day)
            if events:
                story.append(Paragraph(self.daySubtitle(day),
                                       self.subtitle_style))
                story.append(self.buildDayTable(events))
            day = day + datetime.timedelta(days=1)
        return story


# ------------------
# Font configuration
# ------------------

def registerTTFont(fontname, filename):
    """Register a TrueType font with ReportLab.

    Clears up the incorrect straight-through mappings that ReportLab 1.19
    unhelpfully gives us.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab.lib.fonts

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


# 'Arial' is predefined in ReportLab, so we use 'Arial_Normal'

font_map = {'Arial_Normal': 'arial.ttf',
            'Arial_Bold': 'arialbd.ttf',
            'Arial_Italic': 'ariali.ttf',
            'Arial_Bold_Italic': 'arialbi.ttf',
            'Times_New_Roman': 'times.ttf',
            'Times_New_Roman_Bold': 'timesbd.ttf',
            'Times_New_Roman_Italic': 'timesi.ttf',
            'Times_New_Roman_Bold_Italic': 'timesbi.ttf'}


def setUpMSTTCoreFonts(directory):
    """Set up ReportGen to use MSTTCoreFonts."""
    import reportlab.rl_config
    from reportlab.lib.fonts import addMapping

    ttfpath = reportlab.rl_config.TTFSearchPath
    ttfpath.append(directory)

    reportlab.rl_config.warnOnMissingFontGlyphs = 0

    for font_name, font_file in font_map.items():
        registerTTFont(font_name, font_file)

    addMapping('Arial_Normal', 0, 0, 'Arial_Normal')
    addMapping('Arial_Normal', 0, 1, 'Arial_Italic')
    addMapping('Arial_Normal', 1, 0, 'Arial_Bold')
    addMapping('Arial_Normal', 1, 1, 'Arial_Bold_Italic')

    addMapping('Times_New_Roman', 0, 0, 'Times_New_Roman')
    addMapping('Times_New_Roman', 0, 1, 'Times_New_Roman_Italic')
    addMapping('Times_New_Roman', 1, 0, 'Times_New_Roman_Bold')
    addMapping('Times_New_Roman', 1, 1, 'Times_New_Roman_Bold_Italic')

    global disabled
    disabled = False
