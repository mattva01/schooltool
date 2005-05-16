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
from zope.component import adapts
from zope.interface import implements
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile

from schoolbell.app.rest import View, Template
from schoolbell.app.rest.app import GenericContainerView
from schoolbell.app.rest.errors import RestError
from schoolbell.app.rest.xmlparsing import XMLDocument
from schooltool.common import parse_date, parse_time
from schooltool.interfaces import ITimetableModelFactory
from schooltool.timetable import SchooldayPeriod
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable import Timetable, TimetableDay
from schooltool.timetable import TimetableSchema, TimetableSchemaDay
from schooltool.timetable import TimetableSchemaContainer


def parseDate(date_str):
    """Parse a date string and return a datetime.date object.

    This is a thin wrapper over parse_date that converts ValueErrors into
    (internationalized) ViewErrors.

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
    (internationalized) ViewErrors.

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

    template = Template("www/timetable.pt",
                        content_type="text/xml; charset=UTF-8")

    def absolutePath(self, obj):
        return zapi.absoluteURL(obj, self.request)


class TimetableSchemaView(View):
    """View for ITimetableSchema"""

    dows = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    template = Template("www/timetable_schema.pt",
                        content_type="text/xml; charset=UTF-8")

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

    def parseXML(self, xml):

        doc = XMLDocument(xml, self.schema)

        try:
            doc.registerNs('tt', 'http://schooltool.org/ns/timetable/0.1')
            days = doc.query('/tt:timetable/tt:day')
            day_ids = [day['id'] for day in days]

            templates = doc.query('/tt:timetable/tt:model/tt:daytemplate')
            template_dict = {}
            model_node = doc.query('/tt:timetable/tt:model')[0]
            factory_id = model_node['factory']

            factory = zapi.queryUtility(ITimetableModelFactory, factory_id)
            if factory is None:
                raise RestError("Incorrect timetable model factory")

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
                        raise RestError("Bad period")
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
                            raise RestError("Unrecognised day of week %r" % dow)
            model = factory(day_ids, template_dict)

            if len(sets.Set(day_ids)) != len(day_ids):
                raise RestError("Duplicate days in schema")
            timetable = TimetableSchema(day_ids)
            timetable.model = model
            for day in days:
                day_id = day['id']
                period_ids = [period['id']
                              for period in day.query('tt:period')]
                if len(sets.Set(period_ids)) != len(period_ids):
                    # XXX Should raise RestError here.
                    return textErrorPage(request,
                                         "Duplicate periods in schema")
                timetable[day_id] = TimetableSchemaDay(period_ids)

            return timetable
        finally:
            doc.free()

    def __call__(self, name, content_type, data):

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
