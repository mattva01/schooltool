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
RESTive views for SchoolToolApplication

$Id: app.py 3419 2005-04-14 18:34:36Z alga $
"""

from zope.app import zapi
from zope.interface import implements
from zope.app.container.interfaces import INameChooser
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile

from schooltool.xmlparsing import XMLDocument
from schooltool.app.rest import View, Template
from schooltool.app.interfaces import IWriteCalendar, ISchoolToolCalendar
from schooltool.calendar.icalendar import convert_calendar_to_ical
from schooltool.traverser.traverser import NullTraverserPlugin
from schooltool.traverser.traverser import AdapterTraverserPlugin


class ApplicationObjectFileFactory(object):
    """A superclass for ApplicationObjectContainer to FileFactory adapters."""

    implements(IFileFactory)

    def __init__(self, container):
        self.context = container

    def parseXML(self, data):
        """Get values from document, and put them into a dict."""
        doc = XMLDocument(data, self.schema)
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            return self.parseDoc(doc)
        finally:
            doc.free()

    def __call__(self, name, content_type, data):
        return self.factory(**self.parseXML(data))


class ApplicationObjectFile(object):
    """Adapter adapting Application Objects to IWriteFile"""

    implements(IWriteFile)

    def __init__(self, context):
        self.context = context

    def write(self, data):
        """See IWriteFile"""
        container = self.context.__parent__
        factory = IFileFactory(container)
        kwargs = factory.parseXML(data)
        self.modify(**kwargs)


class ApplicationView(View):
    """The root view for the application."""

    template = Template("templates/app.pt",
                        content_type="text/xml; charset=UTF-8")

    def getContainers(self):
        return [{'href': zapi.absoluteURL(self.context[key], self.request),
                 'title': key} for key in self.context.keys()]


class GenericContainerView(View):
    """A RESTive container view superclass."""

    template = Template("templates/aoc.pt",
                        content_type="text/xml; charset=UTF-8")

    def getName(self):
        return self.context.__name__

    def items(self):
        return [{'href': zapi.absoluteURL(self.context[key], self.request),
                 'title': self.context[key].title}
                for key in self.context.keys()]

    def add(self, obj):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(None, obj)
        self.context[name] = obj

    def POST(self):
        return self.create()

    def create(self):
        """Create a new object from the data supplied in the request."""

        response = self.request.response
        body = self.request.bodyStream.read()

        factory = IFileFactory(self.context)
        item = factory(None, None, body)
        self.add(item)
        location = zapi.absoluteURL(item, self.request)

        response.setStatus(201, 'Created')
        response.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        response.setHeader('Location', location)
        return u"Object created: %s" % location


def getCharset(content_type, default="UTF-8"):
    """Get charset out of content-type

        >>> getCharset('text/xml; charset=latin-1')
        'latin-1'

        >>> getCharset('text/xml; charset=yada-yada')
        'yada-yada'

        >>> getCharset('text/xml; charset=yada-yada; fo=ba')
        'yada-yada'

        >>> getCharset('text/plain')
        'UTF-8'

        >>> getCharset(None)
        'UTF-8'

    """
    if not content_type:
        return default

    parts = content_type.split(";")
    if len(parts) == 0:
        return default

    stripped_parts = [part.strip() for part in parts]

    charsets = [part for part in stripped_parts
                if part.startswith("charset=")]

    if len(charsets) == 0:
        return default

    return charsets[0].split("=")[1]


class CalendarView(View):
    """Restive view for calendars"""

    def GET(self):
        data = "\r\n".join(convert_calendar_to_ical(self.context)) + "\r\n"
        request = self.request
        request.response.setHeader('Content-Type',
                                   'text/calendar; charset=UTF-8')
        request.response.setHeader('Content-Length', len(data))
        request.response.setStatus(200)
        return data

    def PUT(self):
        request = self.request

        for name in request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                request.response.setStatus(501)
                return ''

        body = self.request.bodyStream
        data = body.read()
        charset = getCharset(self.request.getHeader("Content-Type"))

        adapter = IWriteCalendar(self.context)
        adapter.write(data, charset)
        return ''


NullICSCalendarTraverserPlugin = NullTraverserPlugin('calendar.ics')
NullVFBCalendarTraverserPlugin = NullTraverserPlugin('calendar.vfb')

CalendarTraverserPlugin = AdapterTraverserPlugin(
    'calendar', ISchoolToolCalendar)
ICSCalendarTraverserPlugin = AdapterTraverserPlugin(
    'calendar.ics', ISchoolToolCalendar)
VFBCalendarTraverserPlugin = AdapterTraverserPlugin(
    'calendar.vfb', ISchoolToolCalendar)
