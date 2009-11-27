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
"""

import urllib
from datetime import datetime

from zope.interface import implements
from zope.component import getMultiAdapter
from reportlab.lib import units
from reportlab.lib import pagesizes
from zope.publisher.browser import BrowserView
from zope.i18n import translate
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from z3c.rml import rml2pdf

from schooltool.common import SchoolToolMessage as _
from schooltool.common.inlinept import InlinePageTemplate
from schooltool.app import pdf
from schooltool.app.browser.interfaces import IReportPageTemplate


def _quoteUrl(url):
    if not url:
        return url
    if type(url) is unicode:
        encoded = url.encode('UTF-8')
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
        if not pdf.isEnabled():
            return translate(self.pdf_disabled_text, context=self.request)
        filename = _quoteUrl(self.filename)
        xml = self.template()
        stream = rml2pdf.parseString(xml, filename=filename)
        data = stream.getvalue()
        self.setUpResponse(data, filename)
        return data


class PageTemplateEnablingHelper(object):

    def __init__(self, view):
        self.view = view

    def __getitem__(self, template_name):
        templates = dict(self.view.page_templates)
        if template_name in templates:
            return ''
        page_template = getMultiAdapter(
            (self.view.context, self.view.request, self.view),
            IReportPageTemplate,
            name=template_name)
        self.view.page_templates.append((template_name, page_template))
        return page_template


class ReportPageTemplate(object):
    implements(IReportPageTemplate)

    template = None # Page template for rendering RML page template tag
    style_template = None # Page template for rendering RML stylesheet contents

    def __init__(self, context, request, view):
        self.context, self.request = context, request
        self.parent = view

    def stylesheet(self):
        if self.style_template is not None:
            return self.style_template(
                view=self, context=self.context, request=self.request)
        return ''

    def __call__(self):
        return self.template()


class DefaultPageTemplate(ReportPageTemplate):

    template=ViewPageTemplateFile('templates/default_report_template.pt',
                                  content_type="text/xml")
    style_template = InlinePageTemplate("""
      <paraStyle name="_footer_page_number"
        xmlns:tal="http://xml.zope.org/namespaces/tal"
        alignment="center" fontName="Times_New_Roman"
        tal:attributes="fontSize view/footer/font_height" />
    """, content_type="text/xml")

    footer_text = u"" # additional short footer text
    report_date = None # report generation date

    def __init__(self, *args, **kw):
        ReportPageTemplate.__init__(self, *args, **kw)
        self.report_date = datetime.today()

    @property
    def header(self):
        if not self.parent.title:
            return {'height': 0}
        doc_w, doc_h = self.parent.pageSize
        font_height = 0.25 * units.inch
        header_height = font_height + 0.2 * units.inch
        return {
            'title': {
                'x': (doc_w/2.0),
                'y': (doc_h - self.parent.topMargin - font_height),
                },
            'height': header_height,
            }

    @property
    def footer(self):
        doc_w, doc_h = self.parent.pageSize

        footer_height = 0.6 * units.inch
        font_height = 10 # ~0.14 inch
        rule_y = (self.parent.bottomMargin + 0.55 * units.inch)

        return {
            'rule': '%d %d %d %d' % (
                self.parent.leftMargin, rule_y,
                doc_w - self.parent.rightMargin, rule_y),
            'logo': {
                'x': self.parent.leftMargin,
                'y': self.parent.bottomMargin,
                'height': 0.5 * units.inch,
                },
            'font_height': font_height,
            'center_place': {
                'x': self.parent.leftMargin,
                'y': (self.parent.bottomMargin + footer_height
                      - 0.2 * units.inch
                      - font_height),
                'width': (doc_w - self.parent.leftMargin - self.parent.rightMargin),
                'height': font_height + 0.1 * units.inch,
                },
            'right_str': {
                'x': (doc_w - self.parent.rightMargin),
                'y': (self.parent.bottomMargin + footer_height
                      - 0.1 * units.inch - font_height),
                },
            'right_str_2': {
                'x': (doc_w - self.parent.rightMargin),
                'y': (self.parent.bottomMargin + footer_height
                      - 0.15 * units.inch - font_height * 2),
                },
            'height': footer_height,
            }

    @property
    def frame(self):
        doc_w, doc_h = self.parent.pageSize
        return {
            'x': self.parent.leftMargin,
            'y': self.parent.bottomMargin + self.footer['height'],
            'width': doc_w - self.parent.leftMargin - self.parent.rightMargin,
            'height': (doc_h - self.parent.topMargin - self.parent.bottomMargin
                       - self.header['height'] - self.footer['height']),
            }


class ReportPDFView(PDFView):
    leftMargin = 0.25 * units.inch
    rightMargin = 0.25 * units.inch
    topMargin = 0.25 * units.inch
    bottomMargin = 0.25 * units.inch
    pageSize = pagesizes.A4
    title = u""

    def __init__(self, *args, **kw):
        PDFView.__init__(self, *args, **kw)
        self.page_templates = []
        self.use_template = PageTemplateEnablingHelper(self)
