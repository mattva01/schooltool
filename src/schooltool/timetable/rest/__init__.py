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
RESTive views for SchoolTool timetabling

$Id: app.py 3419 2005-04-14 18:34:36Z alga $
"""

import datetime
import sets

from zope.app import zapi
from zope.event import notify
from zope.component import adapts
from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.interface import Interface
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.http import IHTTPRequest
from zope.security.proxy import removeSecurityProxy
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile
from zope.app.traversing.api import traverse
from zope.app.traversing.interfaces import TraversalError
from zope.app.http.put import NullResource
from zope.app.http.interfaces import INullResource
from zope.app.filerepresentation.interfaces import IWriteDirectory
from zope.app.event.objectevent import ObjectCreatedEvent

from schoolbell.app.rest import View, Template
from schoolbell.app.rest import IRestTraverser
from schoolbell.app.rest.app import GenericContainerView
from schoolbell.app.rest.errors import RestError
from schoolbell.app.rest.xmlparsing import XMLDocument
from schooltool import getSchoolToolApplication
from schooltool.common import parse_date, parse_time
from schooltool.timetable.interfaces import ITimetableModelFactory
from schooltool.timetable.interfaces import IHaveTimetables, ITimetables
from schooltool.timetable.interfaces import ITimetableDict
from schooltool.timetable import SchooldayPeriod
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable import Timetable, TimetableDay, TimetableActivity
from schooltool.timetable import TimetableSchema, TimetableSchemaDay
from schooltool.timetable import TimetableSchemaContainer
from schooltool.rest.interfaces import ITimetableFileFactory
from schooltool.rest.interfaces import INullTimetable, ICompositeTimetables


def parseDate(date_str):
    """Parse a date string and return a datetime.date object.

    This is a thin wrapper over parse_date that converts ValueErrors into
    RestErrors.

        >>> parseDate('2004-10-14')
        datetime.date(2004, 10, 14)
        >>> parseDate('foo')
        Traceback (most recent call last):
          ...
        RestError: Invalid date: foo

    """
    try:
        return parse_date(date_str)
    except ValueError:
        raise RestError("Invalid date: %s" % date_str)


def parseTime(time_str):
    """Parse a time string and return a datetime.time object.

    This is a thin wrapper over parse_time that converts ValueErrors into
    RestErrors.

        >>> parseTime('8:45')
        datetime.time(8, 45)
        >>> parseTime('foo')
        Traceback (most recent call last):
          ...
        RestError: Invalid time: foo
    """
    try:
        return parse_time(time_str)
    except ValueError:
        raise RestError("Invalid time: %s" % time_str)


def parseDuration(duration_str):
    """Parse a duration string and return a datetime.timedelta.

        >>> parseDuration('1')
        datetime.timedelta(0, 60)
        >>> parseDuration('just a minute')
        Traceback (most recent call last):
          ...
        RestError: Invalid duration: just a minute
        >>> parseDuration('0')
        Traceback (most recent call last):
          ...
        RestError: Invalid duration: 0
        >>> parseDuration('-1')
        Traceback (most recent call last):
          ...
        RestError: Invalid duration: -1

    """
    try:
        min = int(duration_str)
        if min <= 0:
            raise ValueError
    except ValueError:
        raise RestError("Invalid duration: %s" % duration_str)
    else:
        return datetime.timedelta(minutes=min)


class TimetableSchemaContainerView(GenericContainerView):
    """RESTive view of a TimetableSchemaContainer."""

    def items(self):
        return [{'href': zapi.absoluteURL(self.context[key], self.request),
                 'title': self.context[key].__name__}
                for key in self.context.keys()]


class TimetableReadView(View):
    """Read-only view for ITimetable."""

    template = Template("templates/timetable.pt",
                        content_type="text/xml; charset=UTF-8")

    def absolutePath(self, obj):
        return zapi.absoluteURL(obj, self.request)


class TimetableSchemaView(View):
    """View for ITimetableSchema"""

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    template = Template("templates/timetable_schema.pt",
                        content_type="text/xml; charset=UTF-8")

    def exceptiondayids(self):
        result = []

        for date, id in self.context.model.exceptionDayIds.items():
            result.append({'when': str(date), 'id': id})

        result.sort(lambda a, b: cmp((a['when'], a['id']),
                                     (b['when'], b['id'])))
        return result

    def daytemplates(self):
        result = []
        for id, day in self.context.model.dayTemplates.items():
            if id is None:
                used = "default"
            elif id in self.context.keys():
                used = id
            else:
                used = self.dows[id]
            periods = []
            for period in day:
                periods.append(
                    {'id': period.title,
                     'tstart': period.tstart.strftime("%H:%M"),
                     'duration': period.duration.seconds / 60})
            periods.sort()
            for template in result:
                if template['periods'] == periods:
                    days = template['used'].split()
                    days.append(used)
                    days.sort()
                    template['used'] = " ".join(days)
                    break
            else:
                result.append({'used': used, 'periods': periods})

        for date, day in self.context.model.exceptionDays.items():
            periods = []
            for period in day:
                periods.append(
                    {'id': period.title,
                     'tstart': period.tstart.strftime("%H:%M"),
                     'duration': period.duration.seconds / 60})
            periods.sort()
            result.append({'used': str(date), 'periods': periods})

        result.sort(lambda a, b: cmp((a['used'], a['periods']),
                                     (b['used'], b['periods'])))

        return result


class TimetableSchemaFileFactory(object):

    implements(IFileFactory)
    adapts(TimetableSchemaContainer)

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    schema = """<?xml version="1.0" encoding="UTF-8"?>
         <!--
         RelaxNG grammar for a timetable.
         -->
         <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                  ns="http://schooltool.org/ns/timetable/0.1"
                  datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
           <define name="idattr">
              <attribute name="id">
                 <text/>
              </attribute>
           </define>
           <define name="daysofweek">
             <!-- space separated list of weekdays -->
             <text/>
           </define>
           <start>
             <ref name="timetable"/>
           </start>
           <define name="timetable">
             <element name="timetable">
               <optional>
                 <element name="title">
                   <text />
                 </element>
               </optional>
               <element name="model">
                 <attribute name="factory">
                   <text/>
                 </attribute>
                 <oneOrMore>
                   <element name="daytemplate">
                     <element name="used">
                       <attribute name="when">
                         <ref name="daysofweek"/>
                       </attribute>
                     </element>
                     <zeroOrMore>
                       <element name="period">
                         <ref name="idattr"/>
                         <attribute name="tstart">
                           <!-- XXX  d?d:dd -->
                           <text/>
                         </attribute>
                         <attribute name="duration">
                           <!-- a natural number (of minutes)-->
                           <text/>
                         </attribute>
                       </element>
                     </zeroOrMore>
                   </element>
                 </oneOrMore>
                 <zeroOrMore>
                   <element name="day">
                     <attribute name="when">
                       <ref name="daysofweek"/>
                     </attribute>
                     <ref name="idattr"/>
                   </element>
                 </zeroOrMore>
               </element>
               <oneOrMore>
                 <element name="day">
                   <ref name="idattr"/>
                   <zeroOrMore>
                     <element name="period">
                       <ref name="idattr"/>
                     </element>
                   </zeroOrMore>
                 </element>
               </oneOrMore>
             </element>
           </define>
         </grammar>
         """

    def __init__(self, container):
        self.container = container

    def setUpSchemaDays(self, timetable, days):
        for day in days:
            day_id = day['id']
            period_ids = [period['id']
                          for period in day.query('tt:period')]
            if len(sets.Set(period_ids)) != len(period_ids):
                raise RestError("Duplicate periods in schema")

            timetable[day_id] = TimetableSchemaDay(period_ids)

    def parseXML(self, xml):
        doc = XMLDocument(xml, self.schema)

        try:
            doc.registerNs('tt', 'http://schooltool.org/ns/timetable/0.1')
            days = doc.query('/tt:timetable/tt:day')
            day_ids = [day['id'] for day in days]

            model_node = doc.query('/tt:timetable/tt:model')[0]
            factory_id = model_node['factory']

            title = None
            titles = doc.query('/tt:timetable/tt:title')
            if titles:
                title_node = titles[0]
                title = title_node.content

            factory = zapi.queryUtility(ITimetableModelFactory, factory_id)
            if factory is None:
                raise RestError("Incorrect timetable model factory")

            templates = doc.query('/tt:timetable/tt:model/tt:daytemplate')
            template_dict = {}
            exceptions = {}

            for template in templates:
                day = SchooldayTemplate()

                # parse SchoolDayPeriods
                for period in template.query('tt:period'):
                    pid = period['id']
                    tstart_str = period['tstart']
                    dur_str = period['duration']
                    try:
                        tstart = parse_time(tstart_str)
                        duration = datetime.timedelta(minutes=int(dur_str))
                    except ValueError:
                        raise RestError("Bad period")
                    else:
                        day.add(SchooldayPeriod(pid, tstart, duration))
                used = template.query('tt:used')[0]['when']

                # the used attribute might contain a date, a list of
                # week days, or a string "default"
                try:
                    date = parse_date(used)
                except ValueError:
                    date = None

                if date is not None:
                    # if used contains a valid date - we treat the
                    # template as an exception
                    exceptions[date] = day
                elif used == 'default':
                    template_dict[None] = day
                elif used in day_ids:
                    template_dict[used] = day
                else:
                    # if used is not "default" and is not a valid date
                    # try processing it as if it was a list of weekdays
                    for dow in used.split():
                        try:
                            template_dict[self.dows.index(dow)] = day
                        except ValueError:
                            raise RestError("Unrecognised day of week %r"
                                            % dow)

            model = factory(day_ids, template_dict)

            for date, day in exceptions.items():
                model.exceptionDays[date] = day

            # Parse exceptionDayIds
            exception_ids = doc.query('/tt:timetable/tt:model/tt:day')
            for exception_id_tag in exception_ids:
                used = exception_id_tag['when']
                exception_id = exception_id_tag['id']

                try:
                    date = parse_date(used)
                except ValueError:
                    raise RestError("Invalid date of an exception day")

                if exception_id not in model.timetableDayIds:
                    raise RestError("Invalid date id of an exception day")

                model.exceptionDayIds[date] = exception_id

            # create and set up the timetable
            if len(sets.Set(day_ids)) != len(day_ids):
                raise RestError("Duplicate days in schema")

            timetable = TimetableSchema(day_ids, title=title, model=model)
            self.setUpSchemaDays(timetable, days)

            return timetable
        finally:
            doc.free()

    def __call__(self, name, content_type, data):
        if "." in name:
            raise RestError("Time table schemas can't have dots in their names.")
        if content_type != 'text/xml':
            raise RestError("Unsupported content type: %s" % content_type)

        return self.parseXML(data)


class TimetableSchemaFile(object):
    implements(IWriteFile)

    def __init__(self, context):
        self.context = context

    def write(self, data):
        container = self.context.__parent__
        factory = IFileFactory(container)

        container[self.context.__name__] = factory.parseXML(data)


class TimetableFileFactory(object):

    implements(ITimetableFileFactory)

    schema = """<?xml version="1.0" encoding="UTF-8"?>
        <!--
        RelaxNG grammar for a timetable.
        -->
        <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 ns="http://schooltool.org/ns/timetable/0.1"
                 datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">

          <define name="idattr">
            <attribute name="id">
              <text/>
            </attribute>
          </define>

          <define name="datetext">
            <!-- date in YYYY-MM-DD format -->
            <text/>
          </define>

          <define name="timetext">
            <!-- time in HH:MM format -->
            <text/>
          </define>

          <define name="duration">
            <!-- duration (minutes) -->
            <text/>
          </define>

          <define name="xlinkattr">
            <attribute name="xlink:type">
              <value>simple</value>
            </attribute>
            <attribute name="xlink:href">
              <data type="anyURI"/>
            </attribute>
            <optional>
              <attribute name="xlink:title">
                <text/>
              </attribute>
            </optional>
          </define>

          <start>
            <ref name="timetable"/>
          </start>

          <define name="activity">
            <element name="activity">
              <attribute name="title">
                <text/>
              </attribute>
              <zeroOrMore>
                <element name="resource">
                  <ref name="xlinkattr"/>
                </element>
              </zeroOrMore>
            </element>
          </define>

          <define name="timetable">
            <element name="timetable">
              <oneOrMore>
                <element name="day">
                  <ref name="idattr"/>
                  <zeroOrMore>
                    <element name="period">
                      <ref name="idattr"/>
                      <zeroOrMore>
                        <ref name="activity"/>
                      </zeroOrMore>
                    </element>
                  </zeroOrMore>
                </element>
              </oneOrMore>
            </element>
          </define>

        </grammar>
        """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, name, content_type, data):

        if content_type != 'text/xml':
            raise RestError("Unsupported content type: %s" % content_type)

        return self.parseXML(name, data)

    def parseXML(self, name, xml):

        doc = XMLDocument(xml, self.schema)

        try:
            doc.registerNs('tt', 'http://schooltool.org/ns/timetable/0.1')
            doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

            time_period_id, schema_id = name.split(".")

            app = getSchoolToolApplication()

            if time_period_id not in app["terms"]:
                raise RestError("Time period not defined: %s" % time_period_id)
            try:
                tt = app["ttschemas"][schema_id].createTimetable()
            except KeyError:
                raise RestError("Timetable schema not defined: %s" % schema_id)
            for day in doc.query('/tt:timetable/tt:day'):
                day_id = day['id']
                if day_id not in tt.keys():
                    #XXX Ftest it!
                    raise RestError(_("Unknown day id: %r") % day_id)
                ttday = tt[day_id]
                for period in day.query('tt:period'):
                    period_id = period['id']
                    if period_id not in ttday.periods:
                        #XXX Ftest it!
                        raise RestError(_("Unknown period id: %r") % period_id)
                    for activity in period.query('tt:activity'):
                        ttday.add(period_id, self._parseActivity(activity))
            all_periods = sets.Set()
            for day_id, ttday in tt.items():
                all_periods.update(ttday.keys())
            for exc in doc.query('/tt:timetable/tt:exception'):
                tt.exceptions.append(self._parseException(exc, all_periods))
        finally:
            doc.free()

        return tt

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
                st_app = getSchoolToolApplication()
                st_url = zapi.absoluteURL(st_app, self.request)
                path = path.replace("%s/" % st_url, "")
                res = traverse(st_app, path)
            except TraversalError, e:
                raise RestError("Bad URI: %s" % path)

            resources.append(res)

        # removeSecurityProxy needed because we will put the TimetableActivity
        # into ZODB
        owner = removeSecurityProxy(self.context.__parent__)
        return TimetableActivity(title, owner, resources)


class TimetablePUT(object):
    """Put handler for existing timetables
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def PUT(self):
        request = self.request

        for name in request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                request.response.setStatus(501)
                return ''

        body = self.request.bodyFile
        data = body.read()
        container = self.context.__parent__
        name = self.context.__name__

        factory = queryMultiAdapter((container, self.request),
                                    ITimetableFileFactory)
        container[name] = factory.parseXML(name, data)
        return ''


class TimetableTraverser(object):
    """Allows traversing into /timetables of a ITimetables object.

    We need a ITimetables object and a request:

        >>> from schooltool.person.person import Person
        >>> from zope.publisher.browser import TestRequest
        >>> person = Person()
        >>> request = TestRequest()

        >>> traverser = TimetableTraverser(person, request)
        >>> timetables = ITimetables(person).timetables
        >>> traverser.publishTraverse(request, "anything") is timetables
        True
    """

    implements(IRestTraverser)
    adapts(IHaveTimetables, IHTTPRequest)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        return ITimetables(self.context).timetables


class NullTimetable(NullResource):
    """Placeholder objects for new timetables to be created via PUT"""

    implements(INullTimetable)


class TimetableDictPublishTraverse(object):
    """Traverser for a_timetabled_object/timetables"""

    adapts(ITimetableDict, IHTTPRequest)
    implements(IPublishTraverse)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        # Note: the way the code is written now lets the user access
        # existing timetables even if their name refers to a deleted
        # term/schema. Not sure if that is a good or a bad thing.
        try:
            return self.context[name]
        except KeyError:
            app = getSchoolToolApplication()
            try:
                term, schema = name.split('.')
            except ValueError:
                raise NotFound(self.context, name, request)
            if term in app['terms'] and schema in app['ttschemas']:
                return NullTimetable(self.context, name)
            else:
                raise NotFound(self.context, name, request)


class NullTimetablePUT(object):
    """Put handler for null timetables

    This view creates new timetable in a TimetableDict.
    """

    __used_for__ = INullTimetable

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def PUT(self):
        for name in self.request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                self.request.response.setStatus(501)
                return ''
        # Zope's NullPUT view adapts the container to IWriteDirectory,
        # but we don't need that here.
        container = self.context.container
        name = self.context.name
        factory = queryMultiAdapter((container, self.request),
                                    ITimetableFileFactory)
        data = self.request.bodyFile.read()
        timetable = factory(name, self.request.getHeader('content-type', ''),
                            data)
        notify(ObjectCreatedEvent(timetable))
        container[name] = timetable
        self.request.response.setStatus(201)
        return ''


class CompositeTimetables(object):
    """Adapter of ITimetables to ICompositeTimetables.

    It just wraps a ITimetables object under an ICompositeTimetables
    interface.

        >>> from schooltool.timetable.tests.test_timetable import Parent
        >>> obj = Parent()
        >>> ct = CompositeTimetables(obj)
        >>> ICompositeTimetables.providedBy(ct)
        True

        >>> obj.getCompositeTimetable = lambda term,schema: [term, schema]
        >>> ct.getCompositeTimetable("term", "schema")
        ['term', 'schema']

    """

    implements(ICompositeTimetables)

    def __init__(self, context):
        self.context = context

    def getCompositeTimetable(self, term, schema):
        """See ICompositeTimetables."""

        return ITimetables(self.context).getCompositeTimetable(term, schema)

    def listCompositeTimetables(self):
        """See ICompositeTimetables."""

        return ITimetables(self.context).listCompositeTimetables()


class CompositeTimetableTraverser(object):
    """Traverser for a_timetabled_object/composite-timetables

    We need a timetabled object and a request:

        >>> from schooltool.person.person import Person
        >>> from zope.publisher.browser import TestRequest
        >>> person = Person()
        >>> request = TestRequest()

        >>> traverser = CompositeTimetableTraverser(person, request)
        >>> result = traverser.publishTraverse(request, "anything")
        >>> ICompositeTimetables.providedBy(result)
        True
        >>> result.context is person
        True

    """

    def __init__(self, context, request):
        self.context = context

    def publishTraverse(self, request, name):
        return CompositeTimetables(self.context)


class CompositeTimetablesPublishTraverse(object):
    """Traverser for ICompositeTimetables objects

    We need a timetabled object and a request:

        >>> from schooltool.person.person import Person
        >>> from zope.publisher.browser import TestRequest
        >>> person = Person()
        >>> request = TestRequest()

    If we provide avalid name we should get the result of
    timetabled.getCompositeTimetable:

        >>> person.getCompositeTimetable = lambda term,schema: [term, schema]
        >>> traverser = CompositeTimetablesPublishTraverse(person, request)
        >>> traverser.publishTraverse(request, "term.schema")
        ['term', 'schema']

    If name is not valid (has too many dots for example) we should get
    a NotFound exception:

        >>> traverser.publishTraverse(request, "term.schema.aa")
        Traceback (most recent call last):
        ...
        NotFound: Object: <schooltool.person.person.Person ...>,
                  name: 'term.schema.aa'

    If timetabled.getCompositeTimetable returns None we should get the
    exception too:

        >>> person.getCompositeTimetable = lambda term,schema: None
        >>> traverser.publishTraverse(request, "term.schema")
        Traceback (most recent call last):
        ...
        NotFound: Object: <schooltool.person.person.Person ...>,
                  name: 'term.schema'

    """

    adapts(ICompositeTimetables, IHTTPRequest)
    implements(IPublishTraverse)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        # Note: the way the code is written now lets the user access
        # existing timetables even if their name refers to a deleted
        # term/schema. Not sure if that is a good or a bad thing.
        try:
            term, schema = name.split('.')
            timetable = self.context.getCompositeTimetable(term, schema)
        except ValueError:
            raise NotFound(self.context, name, request)

        if timetable:
            return timetable

        raise NotFound(self.context, name, request)


class TimetableDictView(View):
    """View for a timetable dict."""

    template = Template("templates/timetables.pt",
                        content_type="text/xml; charset=UTF-8")

    def getTimetables(self):
        return self.context.values()

    def _timetables(self):
        timetables = []
        for timetable in self.getTimetables():
            term, schema = timetable.__name__.split(".")
            timetables.append({
                'url': zapi.absoluteURL(timetable, self.request),
                'term': term,
                'schema': schema})
        return timetables

    timetables = property(_timetables)


class CompositeTimetablesView(TimetableDictView):
    """View listing composite timebables of CompositeTimetabled"""

    def getTimetables(self):
        return [self.context.getCompositeTimetable(term, schema)
                for term, schema in self.context.listCompositeTimetables()]
