#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Views for timetabling.

$Id$
"""

import os
import sets
import libxml2
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ITimetableSchemaService
from schooltool.views import View, Template, textErrorPage, notFoundPage
from schooltool.timetable import Timetable, TimetableDay, TimetableActivity
from schooltool.component import getTimetableSchemaService, getPath
from schooltool.component import registerView
from schooltool.schema.rng import validate_against_schema

__metaclass__ = type


moduleProvides(IModuleSetup)


def read_file(fn):
    """Return the contents of the specified file.

    Filename is relative to the directory this module is placed in.
    """
    basedir = os.path.dirname(__file__)
    f = file(os.path.join(basedir, fn))
    try:
        return f.read()
    finally:
        f.close()


class TimetableReadView(View):
    """Read-only view for ITimetable."""

    template = Template("www/timetable.pt", content_type="text/xml")
    html_template = Template("www/timetable_html.pt", content_type="text/html")

    def do_GET(self, request):
        mtype = request.chooseMediaType(['text/xml', 'text/html'])
        if mtype == 'text/html':
            return self.html_template(request, view=self, context=self.context)
        else:
            return self.template(request, view=self, context=self.context)

    def rows(self):
        rows = []
        for ncol, (id, day) in enumerate(self.context.items()):
            for nrow, (period, actiter) in enumerate(day.items()):
                activities = [a.title for a in actiter]
                activities.sort()
                if nrow >= len(rows):
                    rows.append([{'period': '', 'activity': ''}] * ncol)
                rows[nrow].append({'period': period,
                                   'activity': " / ".join(activities)})
        return rows


class TimetableReadWriteView(TimetableReadView):
    """Read/write view for ITimetable."""

    schema = read_file("../schema/timetable.rng")

    def __init__(self, timetabled, key):
        try:
            timetable = timetabled.timetables[key]
        except KeyError:
            timetable = None
        TimetableReadView.__init__(self, timetable)
        self.timetabled = timetabled
        self.key = key

    def do_GET(self, request):
        if self.context is None:
            return notFoundPage(request)
        else:
            return TimetableReadView.do_GET(self, request)

    def do_PUT(self, request):
        ctype = request.getHeader('Content-Type')
        if ';' in ctype:
            ctype = ctype[:ctype.index(';')]
        if ctype != 'text/xml':
            return textErrorPage(request,
                                 "Unsupported content type: %s" % ctype)
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                                     "Timetable not valid according to schema")
        except libxml2.parserError:
            return textErrorPage(request, "Timetable not valid XML")
        doc = libxml2.parseDoc(xml)
        ns = 'http://schooltool.org/ns/timetable/0.1'
        xpathctx = doc.xpathNewContext()
        xpathctx.xpathRegisterNs('tt', ns)

        time_period_id, schema_id = self.key
        try:
            tt = getTimetableSchemaService(self.timetabled)[schema_id]
        except KeyError:
            return textErrorPage(request, "Timetable schema not defined: %s"
                                           % schema_id)
        for day in xpathctx.xpathEval('/tt:timetable/tt:day'):
            day_id = day.nsProp('id', None)
            if day_id not in tt.day_ids:
                return textErrorPage(request, "Unknown day id: %r" % day_id)
            ttday = tt[day_id]
            xpathctx.setContextNode(day)
            for period in xpathctx.xpathEval('tt:period'):
                period_id = period.nsProp('id', None)
                if period_id not in ttday.periods:
                    return textErrorPage(request,
                                         "Unknown period id: %r" % period_id)
                xpathctx.setContextNode(period)
                for activity in xpathctx.xpathEval('tt:activity'):
                    title = activity.get_content()
                    ttday.add(period_id,
                              TimetableActivity(title, self.timetabled))
        if self.context is None:
            self.timetabled.timetables[self.key] = tt
        else:
            self.context.clear()
            self.context.update(tt)
        request.setHeader('Content-Type', 'text/plain')
        return "OK"

    def do_DELETE(self, request):
        if self.context is None:
            return notFoundPage(request)
        else:
            del self.timetabled.timetables[self.key]
            request.setHeader('Content-Type', 'text/plain')
            return "Deleted timetable"


class TimetableSchemaView(TimetableReadView):
    """Read/write view for a timetable schema."""

    schema = read_file("../schema/tt_schema.rng")

    def __init__(self, service, key):
        try:
            timetable = service[key]
        except KeyError:
            timetable = None
        TimetableReadView.__init__(self, timetable)
        self.service = service
        self.key = key

    def do_GET(self, request):
        if self.context is None:
            return notFoundPage(request)
        else:
            return TimetableReadView.do_GET(self, request)

    def do_DELETE(self, request):
        if self.context is None:
            return notFoundPage(request)
        else:
            del self.service[self.key]
            request.setHeader('Content-Type', 'text/plain')
            return "Deleted timetable schema"

    def do_PUT(self, request):
        ctype = request.getHeader('Content-Type')
        if ';' in ctype:
            ctype = ctype[:ctype.index(';')]
        if ctype != 'text/xml':
            return textErrorPage(request,
                                 "Unsupported content type: %s" % ctype)
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                                     "Timetable not valid according to schema")
        except libxml2.parserError:
            return textErrorPage(request, "Timetable not valid XML")
        doc = libxml2.parseDoc(xml)
        ns = 'http://schooltool.org/ns/timetable/0.1'
        xpathctx = doc.xpathNewContext()
        xpathctx.xpathRegisterNs('tt', ns)
        days = xpathctx.xpathEval('/tt:timetable/tt:day')
        day_ids = [day.nsProp('id', None) for day in days]
        if len(sets.Set(day_ids)) != len(day_ids):
            return textErrorPage(request, "Duplicate days in schema")
        timetable = Timetable(day_ids)
        for day in days:
            day_id = day.nsProp('id', None)
            xpathctx.setContextNode(day)
            period_ids = [period.nsProp('id', None)
                          for period in xpathctx.xpathEval('tt:period')]
            if len(sets.Set(period_ids)) != len(period_ids):
                return textErrorPage(request, "Duplicate periods in schema")
            timetable[day_id] = TimetableDay(period_ids)
        self.service[self.key] = timetable
        request.setHeader('Content-Type', 'text/plain')
        return "OK"


class BaseTimetableTraverseView(View):
    """View for obj/timetable and obj/composite-timetable.

    context is an ITimetabled.

    .../obj/timetable/2003-fall/weekly
         ^      ^      ^         ^
         |      |      |         |
         |      |      |   TimetableReadWriteView(obj, ('2003-fall, 'weekly'))
         |      |      |
      ctx=obj   |    TimetableTraverseView(obj, '2003-fall')
                |
              TimetableTraverseView(obj, None)

    """

    def __init__(self, context, time_period=None):
        View.__init__(self, context)
        self.time_period = time_period

    do_GET = staticmethod(notFoundPage)


class TimetableTraverseView(BaseTimetableTraverseView):
    """View for obj/timetable."""

    def _traverse(self, name, request):
        if self.time_period is None:
            return TimetableTraverseView(self.context, name)
        else:
            key = (self.time_period, name)
            return TimetableReadWriteView(self.context, key)


class CompositeTimetableTraverseView(BaseTimetableTraverseView):
    """View for obj/composite-timetable."""

    def _traverse(self, name, request):
        if self.time_period is None:
            return CompositeTimetableTraverseView(self.context, name)
        else:
            tt = self.context.getCompositeTimetable(self.time_period, name)
            if tt is None:
                raise KeyError(name)
            return TimetableReadView(tt)


class TimetableSchemaServiceView(View):
    """View for the timetable schema service"""

    template = Template("www/tt_service.pt", content_type="text/xml")

    def schemas(self):
        base = getPath(self.context)
        return [{'name': key, 'path': '%s/%s' % (base, key)}
                for key in self.context.keys()]

    def _traverse(self, key, request):
        return TimetableSchemaView(self.context, key)


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(ITimetableSchemaService, TimetableSchemaServiceView)

