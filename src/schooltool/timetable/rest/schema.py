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
RESTive views for timetable schemas

$Id: app.py 3419 2005-04-14 18:34:36Z alga $
"""
import sets
import datetime

from zope.interface import implements
from zope.component import adapts
from zope.app import zapi
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile

from schooltool.app.rest import View, Template
from schooltool.app.rest.app import GenericContainerView
from schooltool.app.rest.errors import RestError
from schooltool.xmlparsing import XMLDocument
from schooltool.common import parse_date, parse_time
from schooltool.timetable import SchooldayTemplate, SchooldaySlot
from schooltool.timetable.interfaces import ITimetableModelFactory
from schooltool.timetable.schema import TimetableSchema, TimetableSchemaDay
from schooltool.timetable.schema import TimetableSchemaContainer


class TimetableSchemaContainerView(GenericContainerView):
    """RESTive view of a TimetableSchemaContainer."""

    def items(self):
        return [{'href': zapi.absoluteURL(self.context[key], self.request),
                 'title': self.context[key].__name__}
                for key in self.context.keys()]


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
                    {'tstart': period.tstart.strftime("%H:%M"),
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
                    {'tstart': period.tstart.strftime("%H:%M"),
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
                         <optional>
                           <!-- Backwards compat -->
                           <ref name="idattr"/>
                         </optional>
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
                    tstart_str = period['tstart']
                    dur_str = period['duration']
                    try:
                        tstart = parse_time(tstart_str)
                        duration = datetime.timedelta(minutes=int(dur_str))
                    except ValueError:
                        raise RestError("Bad period")
                    else:
                        day.add(SchooldaySlot(tstart, duration))
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
            raise RestError("Time table schemas can't have dots in "
                            "their names.")
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
