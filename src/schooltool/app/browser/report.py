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
SchoolTool PDF report views.

$Id$
"""

import urllib
from datetime import datetime

from reportlab.lib import units
from reportlab.lib import pagesizes
from zope.publisher.browser import BrowserView
from zope.i18n import translate
from z3c.rml import rml2pdf
from schooltool.common import SchoolToolMessage as _
from schooltool.app.browser import pdfcal
from schooltool.app.interfaces import ISchoolToolApplication


def _quoteUrl(url):
    if not url:
        return url
    if type(url) is unicode:
        encoded = directive.encode('UTF-8')
    else:
        encoded = str(url)
    return urllib.quote(encoded)


class PDFView(BrowserView):

    template = None # Page template for rendering RML
    filename = '' # Suggested PDF file name
    inline = False # Display PDF in browser? (otherwise download)

    pdf_disabled_text = _("PDF support is disabled."
                          "  It can be enabled by your administrator.")

    def setUpResponse(self, data, filename):
        response = self.request.response
        response.setHeader('Content-Type', 'application/pdf')
        response.setHeader('Content-Length', len(data))
        # We don't really accept ranges, but Acrobat Reader will not show the
        # report in the browser page if this header is not provided.
        response.setHeader('Accept-Ranges', 'bytes')

        disposition = self.inline and 'inline' or 'attachment'
        if filename:
            disposition += '; filename="%s"' % filename
        response.setHeader('Content-Disposition', disposition)

    def __call__(self):
        if pdfcal.disabled:
            return translate(self.pdf_disabled_text, context=self.request)
        filename = _quoteUrl(self.filename)
        xml = self.template()
        stream = rml2pdf.parseString(xml, filename=filename)
        data = stream.getvalue()
        self.setUpResponse(data, filename)
        return data


class ReportPDFView(PDFView):
    leftMargin = 0.25 * units.inch
    rightMargin = 0.25 * units.inch
    topMargin = 0.25 * units.inch
    bottomMargin = 0.25 * units.inch
    pageSize = pagesizes.A4

    title = u"" # the title (rendered in PDF on every page)
    footer_text = u"" # additional short footer text
    report_date = None # report generation date

    def __init__(self, *args, **kw):
        PDFView.__init__(self, *args, **kw)
        self.report_date = datetime.today()

    @property
    def header(self):
        if not self.title:
            return {'height': 0}
        doc_w, doc_h = self.pageSize
        font_height = 0.25 * units.inch
        header_height = font_height + 0.2 * units.inch
        return {
            'title': {
                'x': (doc_w/2.0),
                'y': (doc_h - self.topMargin - font_height),
                },
            'height': header_height,
            }

    @property
    def footer(self):
        doc_w, doc_h = self.pageSize

        footer_height = 0.6 * units.inch
        font_height = 10 # ~0.14 inch
        rule_y = (self.bottomMargin + 0.55 * units.inch)

        return {
            'rule': '%d %d %d %d' % (
                self.leftMargin, rule_y, doc_w - self.rightMargin, rule_y),
            'logo': {
                'x': self.leftMargin,
                'y': self.bottomMargin,
                'height': 0.5 * units.inch,
                },
            'font_height': font_height,
            'center_place': {
                'x': self.leftMargin,
                'y': (self.bottomMargin + footer_height
                      - 0.2 * units.inch
                      - font_height),
                'width': (doc_w - self.leftMargin - self.rightMargin),
                'height': font_height + 0.1 * units.inch,
                },
            'right_str': {
                'x': (doc_w - self.rightMargin),
                'y': (self.bottomMargin + footer_height
                      - 0.1 * units.inch - font_height),
                },
            'right_str_2': {
                'x': (doc_w - self.rightMargin),
                'y': (self.bottomMargin + footer_height
                      - 0.15 * units.inch - font_height * 2),
                },
            'height': footer_height,
            }

    @property
    def frame(self):
        doc_w, doc_h = self.pageSize
        return {
            'x': self.leftMargin,
            'y': self.bottomMargin + self.footer['height'],
            'width': doc_w - self.leftMargin - self.rightMargin,
            'height': (doc_h - self.topMargin - self.bottomMargin
                       - self.header['height'] - self.footer['height']),
            }

