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

import sets
import libxml2
import datetime
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ITimetableSchemaService
from schooltool.interfaces import ITimePeriodService
from schooltool.views import View, Template, textErrorPage, notFoundPage
from schooltool.views import absoluteURL, read_file
from schooltool.views.cal import SchooldayModelCalendarView
from schooltool.views.auth import PublicAccess
from schooltool.timetable import Timetable, TimetableDay, TimetableActivity
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.component import getTimetableSchemaService
from schooltool.component import getTimePeriodService
from schooltool.component import registerView, getPath, traverse
from schooltool.component import getRelatedObjects
from schooltool.component import getTimetableModel
from schooltool.schema.rng import validate_against_schema
from schooltool.uris import URIMember, URITaught
from schooltool.cal import SchooldayModel

__metaclass__ = type


moduleProvides(IModuleSetup)


class ViewError(Exception):
    pass


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
    authorization = PublicAccess

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def title(self):
        timetabled = self.context.__parent__.__parent__
        return _("%s's complete timetable for %s") % (timetabled.title,
                                                   ", ".join(self.key))

    def do_GET(self, request):
        template = self.chooseRepresentation(request)
        return template(request, view=self, context=self.context,
                        getPath=getPath)

    def rows(self):
        rows = []
        for ncol, (id, day) in enumerate(self.context.items()):
            for nrow, (period, actiter) in enumerate(day.items()):
                activities = []
                for a in actiter:
                    resources = [r.title for r in a.resources]
                    if resources:
                        resources.sort()
                        activities.append('%s (%s)'
                                          % (a.title, ', '.join(resources)))
                    else:
                        activities.append(a.title)
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
        return _("%s's own timetable for %s") % (timetabled.title,
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
                                 _("Unsupported content type: %s") % ctype)
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(
                    request,
                    _("Timetable not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request, _("Timetable not valid XML"))
        doc = libxml2.parseDoc(xml)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/timetable/0.1'
            xpathctx.xpathRegisterNs('tt', ns)
            xlink = "http://www.w3.org/1999/xlink"
            xpathctx.xpathRegisterNs('xlink', xlink)

            time_period_id, schema_id = self.key
            if time_period_id not in getTimePeriodService(self.timetabled):
                return textErrorPage(request, _("Time period not defined: %s")
                                     % time_period_id)
            try:
                tt = getTimetableSchemaService(self.timetabled)[schema_id]
            except KeyError:
                return textErrorPage(request,
                                     _("Timetable schema not defined: %s")
                                     % schema_id)
            for day in xpathctx.xpathEval('/tt:timetable/tt:day'):
                day_id = day.nsProp('id', None)
                if day_id not in tt.keys():
                    return textErrorPage(request,
                                         _("Unknown day id: %r") % day_id)
                ttday = tt[day_id]
                xpathctx.setContextNode(day)
                for period in xpathctx.xpathEval('tt:period'):
                    period_id = period.nsProp('id', None)
                    if period_id not in ttday.periods:
                        return textErrorPage(request,
                                             _("Unknown period id: %r")
                                             % period_id)
                    xpathctx.setContextNode(period)
                    for activity in xpathctx.xpathEval('tt:activity'):
                        title = activity.nsProp('title', None)
                        resources = []
                        xpathctx.setContextNode(activity)
                        for resource in xpathctx.xpathEval('tt:resource'):
                            path = resource.nsProp('href', xlink)
                            try:
                                res = traverse(self.timetabled, path)
                            except KeyError:
                                return textErrorPage(
                                    request,
                                    _("Invalid path: %s") % path)
                            resources.append(res)
                        ttday.add(period_id,
                                  TimetableActivity(title, self.timetabled,
                                                    resources))
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

        if self.context is None:
            self.timetabled.timetables[self.key] = tt
        else:
            for day_id, period_id, activity in self.context.itercontent():
                for resource in activity.resources:
                    resource.timetables[self.key][day_id].remove(period_id,
                                                                 activity)
            self.context.clear()
            self.context.update(tt)
        for day_id, period_id, activity in tt.itercontent():
            for resource in activity.resources:
                if self.key not in resource.timetables:
                    resource.timetables[self.key] = tt.cloneEmpty()
                resource.timetables[self.key][day_id].add(period_id, activity)
        request.setHeader('Content-Type', 'text/plain')
        return _("OK")

    def do_DELETE(self, request):
        if self.context is None:
            return notFoundPage(request)
        else:
            del self.timetabled.timetables[self.key]
            request.setHeader('Content-Type', 'text/plain')
            return _("Deleted timetable")


class TimetableSchemaView(TimetableReadView):
    """Read/write view for a timetable schema."""

    schema = read_file("../schema/tt_schema.rng")

    template = Template("www/timetable_schema.pt", content_type="text/xml")
    authorization = PublicAccess

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    def __init__(self, service, key):
        try:
            timetable = service[key]
        except KeyError:
            timetable = None
        TimetableReadView.__init__(self, timetable, key)
        self.service = service

    def title(self):
        return _("Timetable schema: %s") % self.key

    def daytemplates(self):
        result = []
        for id, day in self.context.model.dayTemplates.items():
            if id is None:
                used = "default"
            else:
                used = self.dows[id]
            periods = []
            for period in day:
                periods.append(
                    {'id': period.title,
                     'tstart': period.tstart.strftime("%H:%M"),
                     'duration': period.duration.seconds / 60})
            for template in result:
                L1 = list(template['periods'])
                L1.sort()
                periods.sort()
                if L1 == periods:
                    days = template['used'].split()
                    days.append(used)
                    days.sort()
                    template['used'] = " ".join(days)
                    break
            else:
                result.append({'used': used, 'periods': periods})
        return result

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
            return _("Deleted timetable schema")

    def do_PUT(self, request):
        ctype = request.getHeader('Content-Type')
        if ';' in ctype:
            ctype = ctype[:ctype.index(';')]
        if ctype != 'text/xml':
            return textErrorPage(request,
                                 _("Unsupported content type: %s") % ctype)
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                                     _("Timetable not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request, _("Not valid XML"))
        doc = libxml2.parseDoc(xml)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/timetable/0.1'
            xpathctx.xpathRegisterNs('tt', ns)
            days = xpathctx.xpathEval('/tt:timetable/tt:day')
            day_ids = [day.nsProp('id', None) for day in days]

            templates = xpathctx.xpathEval(
                '/tt:timetable/tt:model/tt:daytemplate')
            template_dict = {}
            model_node = xpathctx.xpathEval('/tt:timetable/tt:model')[0]
            factory_id = model_node.nsProp('factory', None)
            try:
                factory = getTimetableModel(factory_id)
            except KeyError:
                return textErrorPage(request,
                                     _("Incorrect timetable model factory"))
            for template in templates:
                dayid = template.nsProp('id', None)
                xpathctx.setContextNode(template)
                day = SchooldayTemplate()
                for period in xpathctx.xpathEval('tt:period'):
                    pid = period.nsProp('id', None)
                    tstart_str = period.nsProp('tstart', None)
                    dur_str = period.nsProp('duration', None)
                    try:
                        h, m = [int(s) for s in tstart_str.split(":")]
                        dur = int(dur_str)
                        day.add(SchooldayPeriod(
                            pid, datetime.time(h, m),
                            datetime.timedelta(minutes=dur)))
                    except ValueError:
                        return textErrorPage(request, _("Bad period"))
                used = xpathctx.xpathEval('tt:used')[0].nsProp('when', None)
                if used == 'default':
                    template_dict[None] = day
                else:
                    for dow in used.split():
                        try:
                            template_dict[self.dows.index(dow)] = day
                        except ValueError:
                            return textErrorPage(
                                request,
                                _("Unrecognised day of week %r") % (dow,))
            model = factory(day_ids, template_dict)

            if len(sets.Set(day_ids)) != len(day_ids):
                return textErrorPage(request, _("Duplicate days in schema"))
            timetable = Timetable(day_ids)
            timetable.model = model
            for day in days:
                day_id = day.nsProp('id', None)
                xpathctx.setContextNode(day)
                period_ids = [period.nsProp('id', None)
                              for period in xpathctx.xpathEval('tt:period')]
                if len(sets.Set(period_ids)) != len(period_ids):
                    return textErrorPage(request,
                                         _("Duplicate periods in schema"))
                timetable[day_id] = TimetableDay(period_ids)
            self.service[self.key] = timetable
            request.setHeader('Content-Type', 'text/plain')
            return _("OK")
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
    authorization = PublicAccess

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

    def __init__(self, context, time_period=None, readonly=False):
        BaseTimetableTraverseView.__init__(self, context, time_period)
        self.readonly = readonly

    def title(self):
        return _("Timetables for %s") % self.context.title

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
            return TimetableTraverseView(self.context, name, self.readonly)
        else:
            key = (self.time_period, name)
            if not self.readonly:
                return TimetableReadWriteView(self.context, key)
            tt = self.context.timetables[key]
            return TimetableReadView(tt, key)


class CompositeTimetableTraverseView(BaseTimetableTraverseView):
    """View for obj/composite-timetables."""

    def title(self):
        return _("Composite timetables for %s") % self.context.title

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
    authorization = PublicAccess

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
    authorization = PublicAccess

    schema = read_file("../schema/schooltt.rng")

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def do_PUT(self, request):
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                                     _("Timetable not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request, _("Timetable not valid XML"))

        try:
            doc = libxml2.parseDoc(xml)
            ns = 'http://schooltool.org/ns/schooltt/0.1'
            xpathctx = doc.xpathNewContext()
            xpathctx.xpathRegisterNs('st', ns)
            xlink = "http://www.w3.org/1999/xlink"
            xpathctx.xpathRegisterNs('xlink', xlink)

            timetables = {}
            service = getTimetableSchemaService(self.context)
            schema = service[self.key[1]]
            groups = {}
            for teacher_node in xpathctx.xpathEval('/st:schooltt/st:teacher'):
                path = teacher_node.nsProp('path', None)
                try:
                    teacher = traverse(self.context, path)
                except KeyError:
                    return textErrorPage(request, _("Invalid path: %s") % path)
                groups[path] = list(getRelatedObjects(teacher, URITaught))
                for group in groups[path]:
                    path = getPath(group)
                    if path in timetables:
                        continue
                    if self.key in group.timetables:
                        tt = group.timetables[self.key]
                        for day_id, period_id, activity in tt.itercontent():
                            for resource in activity.resources:
                                res_tt = resource.timetables[self.key]
                                res_tt[day_id].remove(period_id, activity)
                        tt.clear()
                    else:
                        tt = schema.cloneEmpty()
                    group.timetables[self.key] = tt
                    timetables[path] = tt

            try:
                iterator = self._walkXml(xpathctx, schema, timetables, groups)
                for tt, day_id, period_id, activity in iterator:
                    tt[day_id].add(period_id, activity)
                    for res in activity.resources:
                        if self.key not in res.timetables:
                            res.timetables[self.key] = schema.cloneEmpty()
                        res_tt = res.timetables[self.key]
                        res_tt[day_id].add(period_id, activity)
            except ViewError, e:
                return textErrorPage(request, e)

            request.setHeader('Content-Type', 'text/plain')
            return _("OK")
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

    def _walkXml(self, xpathctx, schema, timetables, groups):
        xlink = "http://www.w3.org/1999/xlink"
        for teacher_node in xpathctx.xpathEval('/st:schooltt/st:teacher'):
            teacher_path = teacher_node.nsProp('path', None)
            xpathctx.setContextNode(teacher_node)
            for day in xpathctx.xpathEval('st:day'):
                day_id = day.nsProp('id', None)
                if day_id not in schema.keys():
                    raise ViewError(_("Unknown day id: %r") % day_id)
                xpathctx.setContextNode(day)
                for period in xpathctx.xpathEval('st:period'):
                    period_id = period.nsProp('id', None)
                    if period_id not in schema[day_id].periods:
                        raise ViewError(_("Unknown period id: %r") % period_id)
                    xpathctx.setContextNode(period)
                    for activity in xpathctx.xpathEval('st:activity'):
                        path = activity.nsProp('group', None)
                        title = activity.nsProp('title', None)
                        if path not in timetables:
                            raise ViewError(_("Invalid group: %s") % path)
                        group = traverse(self.context, path)
                        if group not in groups[teacher_path]:
                            raise ViewError(_("Invalid group %s for teacher %s")
                                            % (path, teacher_path))
                        resources = []
                        xpathctx.setContextNode(activity)
                        for resource in xpathctx.xpathEval('st:resource'):
                            rpath = resource.nsProp('href', xlink)
                            try:
                                res = traverse(self.context, rpath)
                            except KeyError:
                                raise ViewError(_("Invalid path: %s") % rpath)
                            resources.append(res)
                        act = TimetableActivity(title, group, resources)
                        yield timetables[path], day_id, period_id, act

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
    authorization = PublicAccess

    def periods(self):
        base = getPath(self.context)
        return [{'name': key, 'path': '%s/%s' % (base, key)}
                for key in self.context.keys()]

    def _traverse(self, key, request):
        return TimePeriodCreatorView(self.context, key)


class TimePeriodCreatorView(SchooldayModelCalendarView):
    """View for the time period service items"""

    authorization = PublicAccess

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
            return _("OK")


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(ITimetableSchemaService, TimetableSchemaServiceView)
    registerView(ITimePeriodService, TimePeriodServiceView)

