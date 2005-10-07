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
REST interface for academic records

$Id: app.py 4109 2005-06-15 17:36:38Z bskahan $
"""
import zope.component
import zope.interface
import zope.security
import zope.wfmc
from zope.app import zapi

import schooltool
from schooltool import person
from schooltool.app import app, rest
from schooltool.level import interfaces
from schooltool.xmlparsing import XMLDocument


class PersonHTTPTraverser(object):

    zope.component.adapts(person.interfaces.IPerson)
    zope.interface.implements(rest.IRestTraverser)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        record = interfaces.IAcademicRecord(self.context)
        if name == 'academicStatus':
            return AcademicStatus(record)
        elif name == 'academicHistory':
            return AcademicHistory(record)
        elif name == 'promotion':
            if record.levelProcess is None:
                return AcademicProcessCreator(record)
            manager = app.getSchoolToolApplication()['groups']['manager']
            return [
                item
                for item in interfaces.IManagerWorkItems(manager).items
                if (item.participant.activity.process.workflowRelevantData.student == self.context)][0]


class AcademicStatus(object):

    def __init__(self, record):
        self.record = record

    def getStatus(self):
        return self.record.status

    def setStatus(self, status):
        self.record.status = status


class AcademicStatusView(rest.View):

    def PUT(self):

        for name in self.request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                self.request.response.setStatus(501)
                return ''

        body = self.request.bodyFile
        status = body.read().split("\n")[0]
        self.context.setStatus(status)
        self.request.response.setStatus("200")
        return ''

    POST = PUT

    def GET(self):
        self.request.response.setHeader('Content-Type', "text/plain")
        self.request.response.setStatus(200)
        return self.context.getStatus() or ''


class AcademicHistory(object):

    def __init__(self, record):
        self.record = record
        
        
class AcademicHistoryView(rest.View):

    template = rest.Template("history.pt",
                             content_type="text/xml; charset=UTF-8")

    def history(self):
        formatter = self.request.locale.dates.getFormatter('dateTime', 'medium')
        for record in self.context.record.history:
            yield {'title': record.title,
                   'description': record.description,
                   'timestamp': formatter.format(record.timestamp)}


class AcademicProcessCreator(object):

    def __init__(self, record):
        self.record = record

    def create(self):
        pd = zapi.getUtility(zope.wfmc.interfaces.IProcessDefinition,
                             name='schooltool.promotion')
        process = pd()
        process.start(
            zope.security.proxy.removeSecurityProxy(self.record).context,
            None, None)
        self.record.levelProcess = process
    
        
class AcademicProcessCreatorView(rest.View):

    def PUT(self):
        self.context.create()
        self.request.response.setStatus("200")
        return ''


    def GET(self):
        self.request.response.setHeader('Content-Type', "text/plain")
        self.request.response.setStatus(200)
        return ''


class SelectInitialLevelView(rest.View):

    template = rest.Template("selectinitiallevel.pt",
                             content_type="text/xml; charset=UTF-8")

    schema = '''<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0"
         xmlns:xlink="http://www.w3.org/1999/xlink"
         ns="http://schooltool.org/ns/model/0.1"
         datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
      <start>
        <element name="object">
          <attribute name="initialLevel">
            <text/>
          </attribute>
        </element>
      </start>
    </grammar>'''

    def POST(self):
        body = self.request.bodyFile.read()
        doc = XMLDocument(body, self.schema)
        doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
        node = doc.query('/m:object')[0]
        levels = app.getSchoolToolApplication()['levels']
        try:
            level = levels[node['initialLevel']]
        except KeyError:
            raise rest.errors.RestError("No such level.")
        else:
            zope.security.proxy.removeSecurityProxy(self.context).finish(level)

        return "Initial Level selected."


class SetLevelOutcomeView(rest.View):

    template = rest.Template("setleveloutcome.pt",
                             content_type="text/xml; charset=UTF-8")

    schema = '''<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0"
         xmlns:xlink="http://www.w3.org/1999/xlink"
         ns="http://schooltool.org/ns/model/0.1"
         datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
      <start>
        <element name="object">
          <attribute name="outcome">
            <text/>
          </attribute>
          <optional>
            <attribute name="level">
              <text/>
            </attribute>
          </optional>
        </element>
      </start>
    </grammar>'''

    def level(self):
        process = zope.security.proxy.removeSecurityProxy(
            self.context).participant.activity.process
        return zapi.getName(process.workflowRelevantData.level)

    def POST(self):
        body = self.request.bodyFile.read()
        doc = XMLDocument(body, self.schema)
        doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
        node = doc.query('/m:object')[0]
        zope.security.proxy.removeSecurityProxy(self.context).finish(
            node['outcome'])

        return "Outcome submitted."
