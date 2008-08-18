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

$Id$
"""

import datetime
import sets

from zope.event import notify
from zope.component import adapts
from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.http import IHTTPRequest
from zope.security.proxy import removeSecurityProxy
from zope.traversing.api import traverse
from zope.traversing.interfaces import TraversalError
from zope.app.http.put import NullResource
from zope.lifecycleevent import ObjectCreatedEvent
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.rest import View, Template
from schooltool.app.rest.errors import RestError
from schooltool.app.app import getSchoolToolApplication
from zope.app.container.traversal import ItemTraverser
from schooltool.common.xmlparsing import LxmlDocument
from schooltool.common import parse_date, parse_time
from schooltool.term.interfaces import ITermContainer
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableDict
from schooltool.timetable import TimetableActivity, TimetableDict
from schooltool.traverser import traverser
from schooltool.app.rest.interfaces import ITimetableFileFactory
from schooltool.app.rest.interfaces import INullTimetable
from schooltool.common import unquote_uri
from schooltool.common import SchoolToolMessage as _


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


class TimetableReadView(View):
    """Read-only view for ITimetable."""

    template = Template("templates/timetable.pt",
                        content_type="text/xml; charset=UTF-8")

    def absolutePath(self, obj):
        return absoluteURL(obj, self.request)


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
              <element name="timezone">
                <attribute name="name">
                  <text />
                </attribute>
              </element>
              <element name="term">
                <attribute name="id">
                  <text />
                </attribute>
              </element>
              <element name="schooltt">
                <attribute name="id">
                  <text />
                </attribute>
              </element>
              <oneOrMore>
                <element name="day">
                  <ref name="idattr"/>
                  <zeroOrMore>
                    <element name="period">
                      <ref name="idattr"/>
                       <optional>
                         <attribute name="homeroom">
                           <!-- presence of this attribute indicates that this
                                period is the homeroom period -->
                         </attribute>
                       </optional>
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

    nsmap = {'tt': 'http://schooltool.org/ns/timetable/0.1',
             'xlink': 'http://www.w3.org/1999/xlink'}

    def parseXML(self, name, xml):
        doc = LxmlDocument(xml, self.schema)

        term_node = doc.xpath('/tt:timetable/tt:term', self.nsmap)[0]
        time_period_id = term_node.attrib['id']

        schooltt_node = doc.xpath('/tt:timetable/tt:schooltt', self.nsmap)[0]
        schema_id = schooltt_node.attrib['id']

        app = getSchoolToolApplication()

        if time_period_id not in ITermContainer(app):
            raise RestError("Time period not defined: %s" % time_period_id)
        try:
            tt = app["ttschemas"][schema_id].createTimetable(ITermContainer(app)[time_period_id])
        except KeyError:
            raise RestError("Timetable schema not defined: %s" % schema_id)
        tznode = doc.xpath('/tt:timetable/tt:timezone', self.nsmap)[0]
        tt.timezone = tznode.attrib['name']
        for day in doc.xpath('/tt:timetable/tt:day', self.nsmap):
            day_id = day.attrib['id']
            if day_id not in tt.keys():
                #XXX Ftest it!
                raise RestError(_("Unknown day id: %r") % day_id)
            ttday = tt[day_id]
            for period in day.xpath('tt:period', self.nsmap):
                period_id = period.attrib['id']
                if period_id not in ttday.periods:
                    #XXX Ftest it!
                    raise RestError(_("Unknown period id: %r") % period_id)
                for activity in period.xpath('tt:activity', self.nsmap):
                    ttday.add(period_id, self._parseActivity(activity),
                              send_events=False)
        all_periods = sets.Set()
        for day_id, ttday in tt.items():
            all_periods.update(ttday.keys())
        for exc in doc.xpath('/tt:timetable/tt:exception', self.nsmap):
            tt.exceptions.append(self._parseException(exc, all_periods))

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
        title = activity_node.attrib['title']
        resources = []
        for resource in activity_node.xpath('tt:resource', self.nsmap):
            path = unquote_uri(resource.attrib['{http://www.w3.org/1999/xlink}href'])
            try:
                st_app = getSchoolToolApplication()
                st_url = absoluteURL(st_app, self.request)
                path = path.replace("%s/" % st_url, "")
                res = traverse(st_app, path)
            except TraversalError, e:
                raise RestError("Bad URI: %s" % path)

            resources.append(res)

        # removeSecurityProxy needed because we will put the TimetableActivity
        # into ZODB
        owner = removeSecurityProxy(self.context.__parent__)
        return TimetableActivity(title, owner, resources=resources)


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

        body = self.request.bodyStream
        data = body.read()
        container = self.context.__parent__
        name = self.context.__name__

        factory = queryMultiAdapter((container, self.request),
                                    ITimetableFileFactory)
        container[name] = factory.parseXML(name, data)
        return ''


class TimetableTraverser(traverser.NameTraverserPlugin):

    traversalName = 'timetables'
    component = TimetableDict

    def _traverse(self, request, name):
        return ITimetables(self.context).timetables


class NullTimetable(NullResource):
    """Placeholder objects for new timetables to be created via PUT"""

    implements(INullTimetable)


class TimetableDictPublishTraverse(ItemTraverser):
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
        itemTraverse = super(TimetableDictPublishTraverse, self)
        try:
            return itemTraverse.publishTraverse(request, name)
        except NotFound:
            return NullTimetable(self.context, name)


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
        data = self.request.bodyStream.read()
        timetable = factory(name, self.request.getHeader('content-type', ''),
                            data)
        notify(ObjectCreatedEvent(timetable))
        container[name] = timetable
        self.request.response.setStatus(201)
        return ''


class TimetableDictView(View):
    """View for a timetable dict."""

    template = Template("templates/timetables.pt",
                        content_type="text/xml; charset=UTF-8")

    def getTimetables(self):
        return self.context.values()

    def _timetables(self):
        timetables = []
        for timetable in self.getTimetables():
            term_id = timetable.term.__name__
            schooltt_id = timetable.schooltt.__name__
            timetables.append({
                'url': absoluteURL(timetable, self.request),
                'term': term_id,
                'schema': schooltt_id})
        return timetables

    timetables = property(_timetables)
