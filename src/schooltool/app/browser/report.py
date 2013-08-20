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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool PDF report views.
"""

import urllib
from datetime import datetime

from zope.interface import implements
from zope.cachedescriptors.property import Lazy
from zope.component import getMultiAdapter
from reportlab.lib import units
from reportlab.lib import pagesizes
from zope.publisher.browser import BrowserView
from zope.i18n import translate
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from z3c.rml import rml2pdf

from schooltool.common import SchoolToolMessage as _
from schooltool.common.inlinept import InlinePageTemplate
from schooltool.table.column import getResourceURL
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

    def renderToFile(self):
        filename = _quoteUrl(self.filename)
        if not pdf.isEnabled():
            return filename, None
        filename = _quoteUrl(self.filename)
        xml = self.template()
        stream = rml2pdf.parseString(xml, filename=filename)
        data = stream.getvalue()
        return filename, data

    def __call__(self):
        if not pdf.isEnabled():
            return translate(self.pdf_disabled_text, context=self.request)
        filename, data = self.renderToFile()
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


class Box(object):
    """XXX: Scheduled for demolition"""

    def __init__(self, top, right=None, bottom=None, left=None):
        self.top = top
        if right is None:
            assert bottom is None, "Need to set right"
            assert left is None, "Need to set right"
            right = top
        self.right = right
        if left is None:
            self.left = right
            if bottom is None:
                self.bottom = top
            else:
                self.bottom = bottom
        else:
            assert bottom is not None, "Need to set bottom"
            self.left = left
            self.bottom = bottom


class ReportPDFView(PDFView):
    leftMargin = 0.25 * units.inch
    rightMargin = 0.25 * units.inch
    topMargin = 0.25 * units.inch
    bottomMargin = 0.25 * units.inch
    margin = Box(topMargin, rightMargin, bottomMargin, leftMargin)
    rotation = 0
    pageSize = pagesizes.A4
    title = u""

    def __init__(self, *args, **kw):
        PDFView.__init__(self, *args, **kw)
        self.page_templates = []
        self.use_template = PageTemplateEnablingHelper(self)


class FlourishDefaultPageTemplate(ReportPageTemplate):
    """XXX: Scheduled for demolition"""

    template = ViewPageTemplateFile(
        'templates/f_default_report_template.pt',
        content_type='text/xml')
    style_template = ViewPageTemplateFile(
        'templates/f_default_style_template.pt',
        content_type='text/xml')

    def lines(self, attr, top, left):
        content = attr['content']
        if not isinstance(content, list):
            content = [content]
        content = filter(None, content)
        margin = attr['margin']
        result = []
        line_height = attr['fontSize'] + margin.top + margin.bottom
        for i, line in enumerate(content):
            result.append({
                    'content': line,
                    'x': left,
                    'y': top - (line_height * (i+1)) + margin.bottom,
                    })
        return line_height * len(result), result

    @Lazy
    def top_line(self):
        width = self.frame['width']
        x1 = self.frame['x']
        x2 = x1 + width
        y = self.header['y'] - (self.frame['margin'].top / 2.0)
        return {
            'coords': '%d %d %d %d' % (x1, y, x2, y),
            'color': '#000000',
            'style': 'square',
            }

    @Lazy
    def bottom_line(self):
        width = self.frame['width']
        x1 = self.frame['x']
        x2 = x1 + width
        y = self.frame['y'] - (self.frame['margin'].top / 2.0)
        return {
            'coords': '%d %d %d %d' % (x1, y, x2, y),
            'color': '#000000',
            'style': 'square',
            }

    @Lazy
    def header(self):
        doc_w, doc_h = self.parent.pageSize
        title = {
            'fontSize': 24,
            'margin': Box(0, 0, 8, 0),
            'content': self.parent.title,
            }
        subtitle = {
            'fontSize': 12,
            'margin': Box(0, 0, 6, 0),
            'content': getattr(self.parent, 'subtitle'),
            }
        top = self.top_bar['y']
        left = self.parent.margin.left
        title_height, title_lines = self.lines(title, top, left)
        title['lines'] = title_lines
        top -= title_height
        subtitle_height, subtitle_lines = self.lines(subtitle, top, left)
        subtitle['lines'] = subtitle_lines
        height = title_height + subtitle_height
        width = doc_w - self.parent.margin.left - self.parent.margin.right
        x = self.parent.margin.left
        y = self.top_bar['y'] - height
        backgroundColor = '#ffffff'
        color = '#000000'
        return {
            'backgroundColor': backgroundColor,
            'color': color,
            'title': title,
            'subtitle': subtitle,
            'height': height,
            'width': width,
            'x': x,
            'y': y,
            }

    @Lazy
    def top_bar(self):
        fontSize = 12
        padding = Box(8, 10.5)
        height = fontSize + padding.top + padding.bottom
        doc_w, doc_h = self.parent.pageSize
        width = doc_w - self.parent.margin.left - self.parent.margin.right
        x = self.parent.margin.left
        y = doc_h - self.parent.margin.top - height
        slot_y = y + padding.bottom
        backgroundColor = '#636466'
        color = '#ffffff'
        return {
            'backgroundColor': backgroundColor,
            'color': color,
            'fontSize': fontSize,
            'height': height,
            'width': width,
            'x': x,
            'y': y,
            'slots': {
                'left': {
                    'x': x + padding.left,
                    'y': slot_y,
                    },
                'center': {
                    'x': x + padding.left,
                    'y': slot_y,
                    },
                'right': {
                    'x': x + width - padding.right,
                    'y': slot_y,
                    },
                }
            }

    @Lazy
    def bottom_bar(self):
        fontSize = 8.5
        padding = Box(1.5, 10.5)
        height = fontSize + padding.top + padding.bottom
        doc_w, doc_h = self.parent.pageSize
        width = doc_w - self.parent.margin.left - self.parent.margin.right
        x = self.parent.margin.left
        y = self.parent.margin.bottom
        slot_y = y + padding.bottom
        backgroundColor = '#ffffff'
        color = '#000000'
        url = getResourceURL('schooltool.skin.flourish',
                             'logo_bw.png',
                             self.request)
        return {
            'logo_url': url,
            'backgroundColor': backgroundColor,
            'color': color,
            'fontSize': fontSize,
            'height': height,
            'width': width,
            'x': x,
            'y': y,
            'slots': {
                'left': {
                    'x': x + padding.left,
                    'y': slot_y,
                    },
                'center': {
                    'x': x + padding.left,
                    'y': slot_y,
                    },
                'right': {
                    'x': x + width - padding.right,
                    'y': slot_y,
                    },
                }
            }

    @Lazy
    def frame(self):
        doc_w, doc_h = self.parent.pageSize
        margin = Box(8, 0)
        width = (doc_w - self.parent.margin.left - self.parent.margin.right
                 - margin.left - margin.right)
        height = (doc_h - self.parent.margin.top - self.parent.margin.bottom
                  - self.top_bar['height'] - self.bottom_bar['height']
                  - self.header['height']
                  - margin.top - margin.bottom)
        x = self.parent.margin.left + margin.left
        y = (self.parent.margin.bottom + self.bottom_bar['height'] +
             margin.bottom)
        return {
            'height': height,
            'margin': margin,
            'width': width,
            'x': x,
            'y': y,
            }


class FlourishReportPDFView(PDFView):
    """XXX: Scheduled for demolition"""

    margin = Box(0.75*units.inch)
    rotation = 0
    pageSize = pagesizes.A4
    title = u''
    subtitle = u''
    slots = {
        'top_left': u'',
        'top_center': u'',
        'top_right': u'',
        }

    def __init__(self, *args, **kw):
        super(FlourishReportPDFView, self).__init__(*args, **kw)
        self.page_templates = []
        self.use_template = PageTemplateEnablingHelper(self)
