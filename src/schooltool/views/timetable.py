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
from schooltool.interfaces import ITimePeriodService
from schooltool.views import View, Template, textErrorPage, notFoundPage
from schooltool.views import absoluteURL
from schooltool.views.cal import SchooldayModelCalendarView
from schooltool.timetable import Timetable, TimetableDay, TimetableActivity
from schooltool.component import getTimetableSchemaService
from schooltool.component import getTimePeriodService
from schooltool.component import registerView, getPath, traverse
from schooltool.component import getRelatedObjects
from schooltool.schema.rng import validate_against_schema
from schooltool.uris import URIMember, URITaught
from schooltool.cal import SchooldayModel

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


class TimetableContentNegotiation:
    """Mixin for figguring out the representation of timetables."""

    def chooseRepresentation(self, request):
        """Choose the appropriate timetable representation.

        Looks at user-provided Accept and User-Agent headers.  Returns a
        page template to use.

        Subclasses should provide the following attributes:
          - template
          - html_template
          - wxhtml_template
        """
        user_agent = request.getHeader('User-Agent') or ''
        if 'wxWindows' in user_agent:
            # wxHTML is an extremely ill-behaved HTTP client
            return self.wxhtml_template
        if 'Mozilla' in user_agent:
            # A hack to override content negotiation for Mozilla, IE and
            # other common browsers that won't know what to do with XML
            return self.html_template
        mtype = request.chooseMediaType(['text/xml', 'text/html'])
        if mtype == 'text/html':
            return self.html_template
        else:
            return self.template


class TimetableReadView(View, TimetableContentNegotiation):
    """Read-only view for ITimetable."""

    template = Template("www/timetable.pt", content_type="text/xml")
    html_template = Template("www/timetable_html.pt")
    # wxWindows has problems with UTF-8
    wxhtml_template = Template("www/timetable_html.pt", charset='ISO-8859-1')

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def title(self):
        timetabled = self.context.__parent__.__parent__
        return "%s's complete timetable for %s" % (timetabled.title,
                                                   ", ".join(self.key))

    def do_GET(self, request):
        template = self.chooseRepresentation(request)
        return template(request, view=self, context=self.context)

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
        TimetableReadView.__init__(self, timetable, key)
        self.timetabled = timetabled

    def title(self):
        timetabled = self.context.__parent__.__parent__
        return "%s's own timetable for %s" % (timetabled.title,
                                              ", ".join(self.key))

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
        try:
            doc = libxml2.parseDoc(xml)
            ns = 'http://schooltool.org/ns/timetable/0.1'
            xpathctx = doc.xpathNewContext()
            xpathctx.xpathRegisterNs('tt', ns)

            time_period_id, schema_id = self.key
            if time_period_id not in getTimePeriodService(self.timetabled):
                return textErrorPage(request, "Time period not defined: %s"
                                     % time_period_id)
            try:
                tt = getTimetableSchemaService(self.timetabled)[schema_id]
            except KeyError:
                return textErrorPage(request,
                                     "Timetable schema not defined: %s"
                                     % schema_id)
            for day in xpathctx.xpathEval('/tt:timetable/tt:day'):
                day_id = day.nsProp('id', None)
                if day_id not in tt.keys():
                    return textErrorPage(request,
                                         "Unknown day id: %r" % day_id)
                ttday = tt[day_id]
                xpathctx.setContextNode(day)
                for period in xpathctx.xpathEval('tt:period'):
                    period_id = period.nsProp('id', None)
                    if period_id not in ttday.periods:
                        return textErrorPage(request,
                                             "Unknown period id: %r"
                                             % period_id)
                    xpathctx.setContextNode(period)
                    for activity in xpathctx.xpathEval('tt:activity'):
                        title = activity.get_content().strip()
                        ttday.add(period_id,
                                  TimetableActivity(title, self.timetabled))
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

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
        TimetableReadView.__init__(self, timetable, key)
        self.service = service

    def title(self):
        return "Timetable schema: %s" % self.key

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
        try:
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
                    return textErrorPage(request,
                                         "Duplicate periods in schema")
                timetable[day_id] = TimetableDay(period_ids)
            self.service[self.key] = timetable
            request.setHeader('Content-Type', 'text/plain')
            return "OK"
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()


class BaseTimetableTraverseView(View, TimetableContentNegotiation):
    """Base class for timetable traversal views.

    context is usually an ITimetabled.

    .../obj/timetables/2003-fall/weekly
         ^      ^      ^         ^
         |      |      |         |
         |      |      |   TimetableReadWriteView(obj, ('2003-fall, 'weekly'))
         |      |      |
      ctx=obj   |    TimetableTraverseView(obj, '2003-fall')
                |
              TimetableTraverseView(obj, None)

    Subclasses should provide the following methods:
     - title
     - template
     - html_template
     - wxhtml_template
     - _traverse
    """

    template = Template("www/timetables.pt", content_type="text/xml")
    html_template = Template("www/timetables_html.pt")
    # wxWindows has problems with UTF-8
    wxhtml_template = Template("www/timetables_html.pt", charset='ISO-8859-1')

    def __init__(self, context, time_period=None):
        View.__init__(self, context)
        self.time_period = time_period

    def do_GET(self, request):
        if self.time_period is not None:
            return notFoundPage(request)
        else:
            template = self.chooseRepresentation(request)
            return template(request, view=self, context=self.context)


class TimetableTraverseView(BaseTimetableTraverseView):
    """View for obj/timetables."""

    def title(self):
        return "Timetables for %s" % self.context.title

    def timetables(self):
        basepath = getPath(self.context) + '/timetables'
        results = []
        for period_id, schema_id in self.context.timetables:
            path = '%s/%s/%s' % (basepath, period_id, schema_id)
            results.append({'schema': schema_id,
                            'period': period_id,
                            'path': path,
                            'uri': absoluteURL(self.request, path)})
        return results

    def _traverse(self, name, request):
        if self.time_period is None:
            return TimetableTraverseView(self.context, name)
        else:
            key = (self.time_period, name)
            return TimetableReadWriteView(self.context, key)


class CompositeTimetableTraverseView(BaseTimetableTraverseView):
    """View for obj/composite-timetables."""

    def title(self):
        return "Composite timetables for %s" % self.context.title

    def timetables(self):
        basepath = getPath(self.context) + '/composite-timetables'
        results = []
        for period_id, schema_id in self.context.listCompositeTimetables():
            path = '%s/%s/%s' % (basepath, period_id, schema_id)
            results.append({'schema': schema_id,
                            'period': period_id,
                            'path': path,
                            'uri': absoluteURL(self.request, path)})
        return results

    def _traverse(self, name, request):
        if self.time_period is None:
            return CompositeTimetableTraverseView(self.context, name)
        else:
            tt = self.context.getCompositeTimetable(self.time_period, name)
            if tt is None:
                raise KeyError(name)
            key = (self.time_period, name)
            return TimetableReadView(tt, key)


class SchoolTimetableTraverseView(BaseTimetableTraverseView):
    """View for /schooltt."""

    def title(self):
        return "School timetables"

    def timetables(self):
        basepath = '/schooltt'
        periods = getTimePeriodService(self.context).keys()
        schemas = getTimetableSchemaService(self.context).keys()
        results = []
        for period_id in periods:
            for schema_id in schemas:
                path = '%s/%s/%s' % (basepath, period_id, schema_id)
                results.append({'schema': schema_id,
                                'period': period_id,
                                'path': path,
                                'uri': absoluteURL(self.request, path)})
        return results

    def _traverse(self, name, request):
        if self.time_period is None:
            if name not in getTimePeriodService(self.context):
                raise KeyError(name)
            return SchoolTimetableTraverseView(self.context, name)
        else:
            getTimetableSchemaService(self.context)[name]
            return SchoolTimetableView(self.context,
                                       key=(self.time_period, name))


class TimetableSchemaServiceView(View):
    """View for the timetable schema service"""

    template = Template("www/tt_service.pt", content_type="text/xml")

    def schemas(self):
        base = getPath(self.context)
        return [{'name': key, 'path': '%s/%s' % (base, key)}
                for key in self.context.keys()]

    def _traverse(self, key, request):
        return TimetableSchemaView(self.context, key)


class SchoolTimetableView(View):
    """A view for the timetable management of the whole school"""

    group = '/groups/teachers'

    template = Template("www/schooltt.pt", content_type="text/xml")

    schema = read_file("../schema/schooltt.rng")

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def do_PUT(self, request):
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                                     "Timetable not valid according to schema")
        except libxml2.parserError:
            return textErrorPage(request, "Timetable not valid XML")

        try:
            doc = libxml2.parseDoc(xml)
            ns = 'http://schooltool.org/ns/schooltt/0.1'
            xpathctx = doc.xpathNewContext()
            xpathctx.xpathRegisterNs('st', ns)

            timetables = {}
            service = getTimetableSchemaService(self.context)
            schema = service[self.key[1]]
            groups = {}
            for teacher_node in xpathctx.xpathEval('/st:schooltt/st:teacher'):
                path = teacher_node.nsProp('path', None)
                try:
                    teacher = traverse(self.context, path)
                except KeyError:
                    return textErrorPage(request, "Invalid path: %s" % path)
                groups[path] = list(getRelatedObjects(teacher, URITaught))
                for group in groups[path]:
                    path = getPath(group)
                    if path in timetables:
                        continue
                    if self.key in group.timetables:
                        tt = group.timetables[self.key]
                    else:
                        tt = schema.cloneEmpty()
                    tt.clear()
                    group.timetables[self.key] = tt
                    timetables[path] = tt

            for teacher_node in xpathctx.xpathEval('/st:schooltt/st:teacher'):
                teacher_path = teacher_node.nsProp('path', None)
                xpathctx.setContextNode(teacher_node)
                for day in xpathctx.xpathEval('st:day'):
                    day_id = day.nsProp('id', None)
                    if day_id not in schema.keys():
                        return textErrorPage(request,
                                             "Unknown day id: %r" % day_id)
                    xpathctx.setContextNode(day)
                    for period in xpathctx.xpathEval('st:period'):
                        period_id = period.nsProp('id', None)
                        if period_id not in schema[day_id].periods:
                            return textErrorPage(request,
                                       "Unknown period id: %r" % period_id)
                        xpathctx.setContextNode(period)
                        for activity in xpathctx.xpathEval('st:activity'):
                            path = activity.nsProp('group', None)
                            title = activity.get_content().strip()
                            if path not in timetables:
                                return textErrorPage(request,
                                           "Invalid group: %s" % path)
                            group = traverse(self.context, path)
                            if group not in groups[teacher_path]:
                                return textErrorPage(request,
                                           "Invalid group %s for teacher %s"
                                           % (path, teacher_path))
                            timetables[path][day_id].add(period_id,
                                TimetableActivity(title, group))

            request.setHeader('Content-Type', 'text/plain')
            return "OK"
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

    def getTeachersTimetables(self):
        result = []
        service = getTimetableSchemaService(self.context)
        schema = service[self.key[1]]
        teachers_group = traverse(self.context, self.group)
        for teacher in getRelatedObjects(teachers_group, URIMember):
            tt = schema.cloneEmpty()
            for group in getRelatedObjects(teacher, URITaught):
                group_tt = group.timetables.get(self.key)
                if group_tt is not None:
                    tt.update(group_tt)
            result.append((teacher, tt))
        return result

    def getPath(self, obj):
        return getPath(obj)


class TimePeriodServiceView(View):
    """View for the time period service"""

    template = Template("www/time_service.pt", content_type="text/xml")

    def periods(self):
        base = getPath(self.context)
        return [{'name': key, 'path': '%s/%s' % (base, key)}
                for key in self.context.keys()]

    def _traverse(self, key, request):
        return TimePeriodCreatorView(self.context, key)


class TimePeriodCreatorView(SchooldayModelCalendarView):
    """View for the time period service items"""

    def __init__(self, service, key):
        if key in service:
            context = service[key]
        else:
            context = None
        View.__init__(self, context)
        self.service = service
        self.key = key

    def do_GET(self, request):
        if self.context is None:
            return notFoundPage(request)
        else:
            return SchooldayModelCalendarView.do_GET(self, request)

    def do_PUT(self, request):
        if self.context is None:
            self.context = self.service[self.key] = SchooldayModel(None, None)
            self.context.__parent__ = self.service
            self.context.__name__ = self.key
        return SchooldayModelCalendarView.do_PUT(self, request)

    def do_DELETE(self, request):
        try:
            del self.service[self.key]
        except KeyError:
            return notFoundPage(request)
        else:
            request.setHeader('Content-Type', 'text/plain')
            return "OK"


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(ITimetableSchemaService, TimetableSchemaServiceView)
    registerView(ITimePeriodService, TimePeriodServiceView)

