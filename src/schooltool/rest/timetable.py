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
import datetime

from zope.interface import moduleProvides
from zope.component import getUtility
from zope.app.traversing.api import traverse, getPath

from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ITimetableSchemaService
from schooltool.interfaces import ITimePeriodService
from schooltool.interfaces import ITimetableModelFactory
from schooltool.rest import View, Template, textErrorPage, notFoundPage
from schooltool.rest import absoluteURL, absolutePath, read_file
from schooltool.rest import ViewError
from schooltool.rest.cal import SchooldayModelCalendarView
from schooltool.rest.auth import PublicAccess
from schooltool.rest.xmlparsing import XMLDocument
from schooltool.rest.xmlparsing import XMLParseError, XMLValidationError
from schooltool.timetable import Timetable, TimetableDay, TimetableActivity
from schooltool.timetable import TimetableException, ExceptionalTTCalendarEvent
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.common import parse_date, parse_time
from schooltool.component import getTimetableSchemaService
from schooltool.component import getTimePeriodService
from schooltool.component import registerView
from schooltool.component import getRelatedObjects
from schooltool.uris import URIMember, URITaught
from schooltool.cal import SchooldayModel
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


def parseDate(date_str):
    """Parse a date string and return a datetime.date object.

    This is a thin wrapper over parse_date that converts ValueErrors into
    (internationalized) ViewErrors.

        >>> parseDate('2004-10-14')
        datetime.date(2004, 10, 14)
        >>> parseDate('foo')
        Traceback (most recent call last):
          ...
        ViewError: Invalid date: foo

    """
    try:
        return parse_date(date_str)
    except ValueError:
        raise ViewError(_("Invalid date: %s") % date_str)


def parseTime(time_str):
    """Parse a time string and return a datetime.time object.

    This is a thin wrapper over parse_time that converts ValueErrors into
    (internationalized) ViewErrors.

        >>> parseTime('8:45')
        datetime.time(8, 45)
        >>> parseTime('foo')
        Traceback (most recent call last):
          ...
        ViewError: Invalid time: foo
    """
    try:
        return parse_time(time_str)
    except ValueError:
        raise ViewError(_("Invalid time: %s") % time_str)


def parseDuration(duration_str):
    """Parse a duration string and return a datetime.timedelta.

        >>> parseDuration('1')
        datetime.timedelta(0, 60)
        >>> parseDuration('just a minute')
        Traceback (most recent call last):
          ...
        ViewError: Invalid duration: just a minute
        >>> parseDuration('0')
        Traceback (most recent call last):
          ...
        ViewError: Invalid duration: 0
        >>> parseDuration('-1')
        Traceback (most recent call last):
          ...
        ViewError: Invalid duration: -1

    """
    try:
        min = int(duration_str)
        if min <= 0:
            raise ValueError
    except ValueError:
        raise ViewError(_("Invalid duration: %s") % duration_str)
    else:
        return datetime.timedelta(minutes=min)


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

    def absolutePath(self, obj):
        return absolutePath(self.request, obj)

    def do_GET(self, request):
        template = self.chooseRepresentation(request)
        return template(request, view=self, context=self.context)

    def rows(self):
        return format_timetable_for_presentation(self.context)


def format_timetable_for_presentation(timetable):
    """Prepare a timetable for presentation with Page Templates.

    Returns a matrix where columns correspond to days, rows correspond to
    periods, and cells contain a dict with two keys

      'period' -- the name of this period (different days may have different
                  periods)

      'activity' -- activity or activities that occur during that period of a
                    day.

    First, let us create a timetable:

      >>> from pprint import pprint
      >>> timetable = Timetable(['day 1', 'day 2', 'day 3'])
      >>> timetable['day 1'] = TimetableDay(['A', 'B'])
      >>> timetable['day 2'] = TimetableDay(['C', 'D', 'E'])
      >>> timetable['day 3'] = TimetableDay(['F'])
      >>> timetable['day 1'].add('A', TimetableActivity('Something'))
      >>> timetable['day 1'].add('B', TimetableActivity('A2'))
      >>> timetable['day 1'].add('B', TimetableActivity('A1'))

    Some timetable activities may have associated resources

      >>> from schooltool.model import Resource
      >>> from schooltool.rest.tests import setPath
      >>> r1 = Resource('R1'); setPath(r1, '/resources/r1')
      >>> r2 = Resource('R2'); setPath(r2, '/resources/r2')
      >>> timetable['day 2'].add('C', TimetableActivity('Else',
      ...                                               resources=[r1]))
      >>> timetable['day 3'].add('F', TimetableActivity('A3',
      ...                                               resources=[r2, r1]))

    Here's how it looks like

      >>> matrix = format_timetable_for_presentation(timetable)
      >>> for row in matrix:
      ...    for cell in row:
      ...        print '%(period)1s: %(activity)-11s |' % cell,
      ...    print
      A: Something   | C: Else (R1)   | F: A3 (R1, R2) |
      B: A1 / A2     | D:             |  :             |
       :             | E:             |  :             |


    """
    rows = []
    for ncol, (id, day) in enumerate(timetable.items()):
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
        for nrow in range(nrow + 1, len(rows)):
            rows[nrow].append({'period': '', 'activity': ''})
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
        ctype = request.getContentType()
        if ctype != 'text/xml':
            return textErrorPage(request,
                                 _("Unsupported content type: %s") % ctype)
        xml = request.content.read()
        try:
            doc = XMLDocument(xml, self.schema)
        except XMLParseError:
            return textErrorPage(request, _("Timetable not valid XML"))
        except XMLValidationError:
            return textErrorPage(request,
                                 _("Timetable not valid according to schema"))

        try:
            doc.registerNs('tt', 'http://schooltool.org/ns/timetable/0.1')
            doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

            time_period_id, schema_id = self.key
            if time_period_id not in getTimePeriodService(self.timetabled):
                raise ViewError(_("Time period not defined: %s")
                                % time_period_id)
            try:
                tt = getTimetableSchemaService(self.timetabled)[schema_id]
            except KeyError:
                raise ViewError(_("Timetable schema not defined: %s")
                                % schema_id)
            for day in doc.query('/tt:timetable/tt:day'):
                day_id = day['id']
                if day_id not in tt.keys():
                    raise ViewError(_("Unknown day id: %r") % day_id)
                ttday = tt[day_id]
                for period in day.query('tt:period'):
                    period_id = period['id']
                    if period_id not in ttday.periods:
                        raise ViewError(_("Unknown period id: %r") % period_id)
                    for activity in period.query('tt:activity'):
                        ttday.add(period_id, self._parseActivity(activity))
            all_periods = sets.Set()
            for day_id, ttday in tt.items():
                all_periods.update(ttday.keys())
            for exc in doc.query('/tt:timetable/tt:exception'):
                tt.exceptions.append(self._parseException(exc, all_periods))
            doc.free()
        except ViewError, e:
            doc.free()
            return textErrorPage(request, e)

        self.timetabled.timetables[self.key] = tt
        path = getPath(tt)
        request.appLog(_("Timetable of %s (%s) for %s, updated") %
                       (self.timetabled.title, getPath(self.timetabled),
                        ", ".join(self.key)))
        request.setHeader('Content-Type', 'text/plain')
        return _("OK")

    def _parseActivity(self, activity_node):
        """Parse the <activity> element and return a TimetableActivity.

        The element looks like this:

            <activity title="TITLE">
              <resource xlink:href="/PATH1" />
              <resource xlink:href="/PATH2" />
              ...
            </activity>

        There can be zero or more resource elements.
        """
        title = activity_node['title']
        resources = []
        for resource in activity_node.query('tt:resource'):
            path = resource['xlink:href']
            try:
                res = traverse(self.timetabled, path)
            except KeyError:
                raise ViewError(_("Invalid path: %s") % path)
            resources.append(res)
        return TimetableActivity(title, self.timetabled, resources)

    def _parseException(self, exception_node, all_periods):
        """Parse the <exception> element and return a TimetableException.

        The element looks like this:

            <exception date="YYYY-MM-DD" period="PERIOD">
              <activity ... />
              <replacement date="YYYY-MM-DD" time="HH:MM" duration="DUR"
                           uid="UID">
                TITLE
              </replacement>
            </exception>

        The replacement element is optional.  The date attribute of the
        replacement is optional and defaults to the date of the exception.
        """
        date = parseDate(exception_node['date'])
        period = exception_node['period']
        if period not in all_periods:
            raise ViewError(_("Unknown period id: %r") % period)
        activity = self._parseActivity(exception_node.query('tt:activity')[0])
        exc = TimetableException(date, period, activity)
        replacement_nodes = exception_node.query('tt:replacement')
        if replacement_nodes:
            exc.replacement = self._parseReplacement(replacement_nodes[0],
                                                     exc)
        return exc

    def _parseReplacement(self, replacement_node, exception):
        """Parse <replacement> and return an ExceptionalTTCalendarEvent.

        The element looks like this:

            <replacement date="YYYY-MM-DD" time="HH:MM" duration="DUR"
                         uid="UID">
              TITLE
            </replacement>

        The date attribute of the replacement is optional.
        """
        if replacement_node.get('date') is None:
            date = exception.date
        else:
            date = parseDate(replacement_node['date'])
        time = parseTime(replacement_node['time'])
        dtstart = datetime.datetime.combine(date, time)
        duration = parseDuration(replacement_node['duration'])
        uid = replacement_node['uid']
        title = replacement_node.content.strip()
        return ExceptionalTTCalendarEvent(dtstart, duration, title,
                                          unique_id=uid, exception=exception)

    def do_DELETE(self, request):
        if self.context is None:
            return notFoundPage(request)
        path = getPath(self.context)
        timetabled = self.context.__parent__.__parent__
        del self.timetabled.timetables[self.key]
        request.appLog(_("Timetable of %s (%s) for %s, deleted") %
                       (timetabled.title, getPath(self.timetabled),
                        ", ".join(self.key)))
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
            request.appLog(_("Timetable schema %s deleted") %
                           getPath(self.context))
            request.setHeader('Content-Type', 'text/plain')
            return _("Deleted timetable schema")

    def do_PUT(self, request):
        ctype = request.getContentType()
        if ctype != 'text/xml':
            return textErrorPage(request,
                                 _("Unsupported content type: %s") % ctype)
        xml = request.content.read()
        try:
            doc = XMLDocument(xml, self.schema)
        except XMLValidationError:
            return textErrorPage(request,
                                 _("Timetable not valid according to schema"))
        except XMLParseError:
            return textErrorPage(request, _("Not valid XML"))
        try:
            doc.registerNs('tt', 'http://schooltool.org/ns/timetable/0.1')
            days = doc.query('/tt:timetable/tt:day')
            day_ids = [day['id'] for day in days]

            templates = doc.query('/tt:timetable/tt:model/tt:daytemplate')
            template_dict = {}
            model_node = doc.query('/tt:timetable/tt:model')[0]
            factory_id = model_node['factory']
            try:
                factory = getUtility(ITimetableModelFactory, factory_id)
            except KeyError:
                return textErrorPage(request,
                                     _("Incorrect timetable model factory"))
            for template in templates:
                day = SchooldayTemplate()
                for period in template.query('tt:period'):
                    pid = period['id']
                    tstart_str = period['tstart']
                    dur_str = period['duration']
                    try:
                        tstart = parse_time(tstart_str)
                        duration = datetime.timedelta(minutes=int(dur_str))
                    except ValueError:
                        return textErrorPage(request, _("Bad period"))
                    else:
                        day.add(SchooldayPeriod(pid, tstart, duration))
                used = template.query('tt:used')[0]['when']
                if used == 'default':
                    template_dict[None] = day
                else:
                    for dow in used.split():
                        try:
                            template_dict[self.dows.index(dow)] = day
                        except ValueError:
                            return textErrorPage(request,
                                        _("Unrecognised day of week %r") % dow)
            model = factory(day_ids, template_dict)

            if len(sets.Set(day_ids)) != len(day_ids):
                return textErrorPage(request, _("Duplicate days in schema"))
            timetable = Timetable(day_ids)
            timetable.model = model
            for day in days:
                day_id = day['id']
                period_ids = [period['id']
                              for period in day.query('tt:period')]
                if len(sets.Set(period_ids)) != len(period_ids):
                    return textErrorPage(request,
                                         _("Duplicate periods in schema"))
                timetable[day_id] = TimetableDay(period_ids)
            self.service[self.key] = timetable
            request.appLog(_("Timetable schema %s updated") %
                           getPath(self.service[self.key]))
            request.setHeader('Content-Type', 'text/plain')
            return _("OK")
        finally:
            doc.free()


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
        baseuri = absoluteURL(self.request, self.context, 'timetables')
        basepath = absolutePath(self.request, self.context, 'timetables')
        results = []
        for period_id, schema_id in self.context.timetables:
            path = '%s/%s/%s' % (basepath, period_id, schema_id)
            uri = '%s/%s/%s' % (baseuri, period_id, schema_id)
            results.append({'schema': schema_id,
                            'period': period_id,
                            'href': path,
                            'uri': uri})
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
        baseuri = absoluteURL(self.request, self.context,
                              'composite-timetables')
        basepath = absolutePath(self.request, self.context,
                                'composite-timetables')
        results = []
        for period_id, schema_id in self.context.listCompositeTimetables():
            path = '%s/%s/%s' % (basepath, period_id, schema_id)
            uri = '%s/%s/%s' % (baseuri, period_id, schema_id)
            results.append({'schema': schema_id,
                            'period': period_id,
                            'href': path,
                            'uri': uri})
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
        return _("School timetables")

    def timetables(self):
        baseuri = absoluteURL(self.request, self.context, 'schooltt')
        basepath = absolutePath(self.request, self.context, 'schooltt')
        periods = getTimePeriodService(self.context).keys()
        schemas = getTimetableSchemaService(self.context).keys()
        results = []
        for period_id in periods:
            for schema_id in schemas:
                path = '%s/%s/%s' % (basepath, period_id, schema_id)
                uri = '%s/%s/%s' % (baseuri, period_id, schema_id)
                results.append({'schema': schema_id,
                                'period': period_id,
                                'href': path,
                                'uri': uri})
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
        base = absolutePath(self.request, self.context)
        return [{'name': key, 'href': '%s/%s' % (base, key)}
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
            doc = XMLDocument(xml, self.schema)
        except XMLValidationError:
            return textErrorPage(request,
                                 _("Timetable not valid according to schema"))
        except XMLParseError:
            return textErrorPage(request, _("Timetable not valid XML"))

        try:
            doc.registerNs('st', 'http://schooltool.org/ns/schooltt/0.2')
            doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

            timetables = {}
            service = getTimetableSchemaService(self.context)
            schema = service[self.key[1]]
            groups = {}
            for teacher_node in doc.query('/st:schooltt/st:teacher'):
                teacher_path = teacher_node['xlink:href']
                try:
                    teacher = traverse(self.context, teacher_path)
                except KeyError:
                    return textErrorPage(request,
                                         _("Invalid path: %s") % teacher_path)
                groups_taught = list(getRelatedObjects(teacher, URITaught))
                groups[teacher_path] = groups_taught
                for group in groups_taught:
                    group_path = absolutePath(self.request, group)
                    if group_path in timetables:
                        continue
                    tt = schema.cloneEmpty()
                    group.timetables[self.key] = tt
                    timetables[group_path] = tt

            try:
                iterator = self._walkXml(doc, schema, timetables, groups)
                for tt, day_id, period_id, activity in iterator:
                    tt[day_id].add(period_id, activity)
            except ViewError, e:
                return textErrorPage(request, e)

            request.appLog(_("School timetable updated"))
            request.setHeader('Content-Type', 'text/plain')
            return _("OK")
        finally:
            doc.free()

    def _walkXml(self, doc, schema, timetables, groups):
        for teacher_node in doc.query('/st:schooltt/st:teacher'):
            teacher_path = teacher_node['xlink:href']
            for day in teacher_node.query('st:day'):
                day_id = day['id']
                if day_id not in schema.keys():
                    raise ViewError(_("Unknown day id: %r") % day_id)
                for period in day.query('st:period'):
                    period_id = period['id']
                    if period_id not in schema[day_id].periods:
                        raise ViewError(_("Unknown period id: %r") % period_id)
                    for activity in period.query('st:activity'):
                        path = activity['group']
                        title = activity['title']
                        if path not in timetables:
                            raise ViewError(_("%s is not a teacher of %s")
                                            % (teacher_path, path))
                        group = traverse(self.context, path)
                        if group not in groups[teacher_path]:
                            raise ViewError(_("%s is not a teacher of %s")
                                            % (teacher_path, path))
                        resources = []
                        for resource in activity.query('st:resource'):
                            rpath = resource['xlink:href']
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

    def absolutePath(self, obj):
        return absolutePath(self.request, obj)


class TimePeriodServiceView(View):
    """View for the time period service"""

    template = Template("www/time_service.pt", content_type="text/xml")
    authorization = PublicAccess

    def periods(self):
        base = absolutePath(self.request, self.context)
        return [{'name': key, 'href': '%s/%s' % (base, key)}
                for key in self.context.keys()]

    def _traverse(self, key, request):
        return TimePeriodCreatorView(self.context, key)


class TimePeriodCreatorView(SchooldayModelCalendarView):
    """View for the time period service items."""

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
        return SchooldayModelCalendarView.do_PUT(self, request)

    def log_PUT(self, request):
        request.appLog(_("Time period %s updated") % getPath(self.context))

    def do_DELETE(self, request):
        try:
            path = getPath(self.service[self.key])
            del self.service[self.key]
        except KeyError:
            return notFoundPage(request)
        else:
            request.appLog(_("Time period %s deleted") % getPath(self.context))
            request.setHeader('Content-Type', 'text/plain')
            return _("OK")


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(ITimetableSchemaService, TimetableSchemaServiceView)
    registerView(ITimePeriodService, TimePeriodServiceView)
