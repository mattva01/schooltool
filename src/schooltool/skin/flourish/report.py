#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
SchoolTool report pages.
"""
import urllib
import datetime

from reportlab.lib import units, pagesizes

import zope.component
import zope.location
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.interface import implements, Interface
from zope.i18n import translate
from z3c.rml import rml2pdf

from schooltool.app import pdf
from schooltool.common import getResourceURL
from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish import page
from schooltool.skin.flourish import viewlet
from schooltool.skin.flourish import templates

from schooltool.common import SchoolToolMessage as _


class Box(object):

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


def quoteFilename(filename):
    if not filename:
        return filename
    if type(filename) is unicode:
        encoded = filename.encode('UTF-8')
    else:
        encoded = str(filename)
    return urllib.quote(encoded)


class PDFPage(page.PageBase):
    implements(interfaces.IPDFPage)

    default_content_type = 'xml'
    template = templates.XMLFile('rml/pdf.pt')
    content_template = None

    page_size = pagesizes.A4
    margin = Box(0.75*units.inch)
    rotation = 0

    title = u''
    author = _("SchoolTool")

    inline = False # Display PDF in browser? (otherwise download)

    pdf_disabled_text = _("PDF support is disabled."
                          "  It can be enabled by your administrator.")

    def renderPDF(self, xml):
        filename = self.filename
        stream = rml2pdf.parseString(xml, filename=filename or None)
        data = stream.getvalue()
        response = self.request.response
        response.setHeader('Content-Type', 'application/pdf')
        response.setHeader('Content-Length', len(data))
        # We don't really accept ranges, but Acrobat Reader will not show the
        # report in the browser page if this header is not provided.
        response.setHeader('Accept-Ranges', 'bytes')
        disposition = self.inline and 'inline' or 'attachment'
        quoted_filename = quoteFilename(filename)
        if quoted_filename:
            disposition += '; filename="%s"' % quoted_filename
        response.setHeader('Content-Disposition', disposition)
        return data

    @property
    def base_filename(self):
        filename = self.__name__
        if filename.strip().lower().endswith('.pdf'):
            filename = filename[:-4]
        return filename

    def makeFileName(self, basename):
        if self.render_invariant:
            return '%s.pdf' % basename
        timestamp = datetime.datetime.now().strftime('%y-%m-%d-%H-%M')
        return '%s_%s.pdf' % (basename, timestamp)

    @property
    def filename(self):
        return self.makeFileName(self.base_filename)

    @property
    def render_debug(self):
        # TODO: Should return True when devmode enabled
        return False

    @property
    def render_invariant(self):
        # TODO: Should return True when running tests
        return False

    def __call__(self):
        if not pdf.isEnabled():
            return translate(self.pdf_disabled_text, context=self.request)
        self.update()
        if self.request.response.getStatus() in [300, 301, 302, 303,
                                                 304, 305, 307]:
            return u''

        rml = self.render()
        data = self.renderPDF(rml)

        return data



class IPlainPDFPage(interfaces.IPDFPage):

    name = zope.schema.TextLine(
        title=u"Report name", required=False)

    scope = zope.schema.TextLine(
        title=u"Report scope (e.g. date range)", required=False)

    title = zope.schema.TextLine(
        title=u"Title", required=False)

    subtitles_left = zope.schema.Text(
        title=u"Subtitles at left", required=False)

    subtitles_right = zope.schema.TextLine(
        title=u"Subtitles at right", required=False)


class PlainPDFPage(PDFPage):
    implements(IPlainPDFPage)

    name = None
    scope = None
    title = None
    subtitles_left = None
    subtitles_right = None


class PDFInitSection(viewlet.ViewletManager):
    pass


class PDFPageInfoSection(viewlet.ViewletManager):

    @property
    def page_size(self):
        return self.view.page_size


class PDFStylesheetInitSection(viewlet.ViewletManager):
    pass


class PDFStylesheetSection(viewlet.ViewletManager):
    pass


class PDFTemplateSection(viewlet.ViewletManager):

    page_size = property(lambda self: self.view.page_size)
    margin = property(lambda self: self.view.margin)
    rotation = property(lambda self: self.view.rotation)
    title = property(lambda self: self.view.title)
    author = property(lambda self: self.view.author)


class PDFStory(viewlet.ViewletManager):
    pass


class PageTemplate(viewlet.Viewlet):
    implements(interfaces.IPageTemplate)

    template = None
    slots_interface = interfaces.ITemplateSlots

    @Lazy
    def slots(self):
        interface = self.slots_interface
        if interface is None:
            return None
        slots = zope.component.queryMultiAdapter(
            (self.context, self.request, self.view, self), interface)
        return slots


class PageTemplateSlots(object):
    implements(interfaces.ITemplateSlots)
    zope.component.adapts(Interface, interfaces.IFlourishLayer,
                          interfaces.IPDFPage, interfaces.IPageTemplate)

    __name__ = 'template_slots'

    def __init__(self, context, request, view, template):
        self.__parent__ = self.context = context
        self.request = request
        self.view = view
        self.template = template


class IPlainTemplateSlots(interfaces.ITemplateSlots):

    top_left = zope.schema.TextLine(title=u"Text at top bar left", required=False)
    top_center = zope.schema.TextLine(title=u"Text at top bar center", required=False)
    top_right = zope.schema.TextLine(title=u"Text at top bar right", required=False)

    title = zope.schema.TextLine(title=u"Title", required=False)
    subtitles_left = zope.schema.Tuple(
        title=u"Subtitles (left)",
        value_type=zope.schema.TextLine(title=u"subtitle", required=False),
        required=False,
        max_length=4,
        )
    subtitles_right = zope.schema.Tuple(
        title=u"Subtitles (right)",
        value_type=zope.schema.TextLine(title=u"subtitle", required=False),
        required=False,
        max_length=6,
        )


class PlainPageTemplate(PageTemplate):

    slots_interface = IPlainTemplateSlots

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
        doc_w, doc_h = self.manager.page_size
        title = {
            'fontSize': 24,
            'margin': Box(0, 0, 8, 0),
            'content': self.slots.title,
            }
        subtitle = {
            'fontSize': 12,
            'margin': Box(0, 0, 6, 0),
            'content': self.slots.subtitles_left,
            }
        top = self.top_bar['y']
        left = self.manager.margin.left
        title_height, title_lines = self.lines(title, top, left)
        title['lines'] = title_lines
        top -= title_height
        subtitle_height, subtitle_lines = self.lines(subtitle, top, left)
        subtitle['lines'] = subtitle_lines
        height = title_height + subtitle_height
        width = doc_w - self.manager.margin.left - self.manager.margin.right
        x = self.manager.margin.left
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
        doc_w, doc_h = self.manager.page_size
        width = doc_w - self.manager.margin.left - self.manager.margin.right
        x = self.manager.margin.left
        y = doc_h - self.manager.margin.top - height
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
        doc_w, doc_h = self.manager.page_size
        width = doc_w - self.manager.margin.left - self.manager.margin.right
        x = self.manager.margin.left
        y = self.manager.margin.bottom
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
        doc_w, doc_h = self.manager.page_size
        margin = Box(8, 0)
        width = (doc_w - self.manager.margin.left - self.manager.margin.right
                 - margin.left - margin.right)
        height = (doc_h - self.manager.margin.top - self.manager.margin.bottom
                  - self.top_bar['height'] - self.bottom_bar['height']
                  - self.header['height']
                  - margin.top - margin.bottom)
        x = self.manager.margin.left + margin.left
        y = (self.manager.margin.bottom + self.bottom_bar['height'] +
             margin.bottom)
        return {
            'height': height,
            'margin': margin,
            'width': width,
            'x': x,
            'y': y,
            }


class PlainPageTemplateSlots(PageTemplateSlots):
    zope.component.adapts(Interface, interfaces.IFlourishLayer, interfaces.IPDFPage,
                          PlainPageTemplate)
    implements(IPlainTemplateSlots)

    @property
    def top_left(self):
        return self.view.name

    @property
    def top_right(self):
        return self.view.scope

    @property
    def title(self):
        return self.view.title

    @property
    def subtitles_left(self):
        subtitles = self.view.subtitles_left or []
        if (subtitles and
            not isinstance(subtitles, (list, tuple))):
            subtitles = translate(subtitles, context=self.request)
            subtitles = [s.strip() for s in subtitles.strip().splitlines()]
        subtitles = subtitles[:IPlainTemplateSlots['subtitles_left'].max_length]
        return subtitles

    @property
    def subtitles_right(self):
        subtitles = self.view.subtitles_right or []
        if (subtitles and
            not isinstance(subtitles, (list, tuple))):
            subtitles = translate(subtitles, context=self.request)
            subtitles = [s.strip() for s in subtitles.strip().splitlines()]
        subtitles = subtitles[:IPlainTemplateSlots['subtitles_right'].max_length]
        return subtitles


class PDFPart(viewlet.Viewlet):

    @property
    def templates(self):
        return self.view.providers.get('template')
