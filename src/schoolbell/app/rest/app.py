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
RESTive views for SchoolBellApplication

$Id$
"""
from zope.app import zapi
from zope.interface import implements
from zope.component import adapts
from zope.app.container.interfaces import INameChooser
from zope.app.filerepresentation.interfaces import IFileFactory

from schoolbell.app.rest import View, Template, textErrorPage
from schoolbell.app.rest.xmlparsing import XMLValidationError, XMLParseError
from schoolbell.app.rest.xmlparsing import XMLDocument

from schoolbell.app.app import Group
from schoolbell.app.interfaces import IGroupContainer

from schoolbell.app.app import Resource
from schoolbell.app.interfaces import IResourceContainer

from schoolbell.app.app import Person
from schoolbell.app.interfaces import IPersonContainer

from schoolbell import SchoolBellMessageID as _


class ApplicationObjectFileFactory(object):
    """A superclass for ApplicationObjectContainer to FileFactory adapters."""

    implements(IFileFactory)

    def __init__(self, container):
        self.context = container

    def __call__(self, name, content_type, data):
        doc = XMLDocument(data, self.schema)
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            obj = self.create(doc, name)
        finally:
            doc.free()

        return obj


class GroupFileFactory(ApplicationObjectFileFactory):
    """Adapter that adapts GroupContainer to FileFactory"""

    adapts(IGroupContainer)

    schema = '''<?xml version="1.0" encoding="UTF-8"?>
        <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                 ns="http://schooltool.org/ns/model/0.1"
                 datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
          <start>
            <element name="object">
              <attribute name="title">
                <text/>
              </attribute>
              <optional>
                <attribute name="description">
                  <text/>
                </attribute>
              </optional>
            </element>
          </start>
        </grammar>
        '''

    def create(self, doc, name=None):
        """Extract data from an XMLDocument and create a Group."""
        node = doc.query('/m:object')[0]
        title = node['title']
        description = node.get('description')
        return Group(title=title, description=description)


class ResourceFileFactory(ApplicationObjectFileFactory):
    """Adapter that adapts ResourceContainer to FileFactory"""

    adapts(IResourceContainer)

    schema = '''<?xml version="1.0" encoding="UTF-8"?>
        <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                 ns="http://schooltool.org/ns/model/0.1"
                 datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
          <start>
            <element name="object">
              <attribute name="title">
                <text/>
              </attribute>
              <optional>
                <attribute name="description">
                  <text/>
                </attribute>
              </optional>
            </element>
          </start>
        </grammar>
        '''

    def create(self, doc, name=None):
        """Extract data from an XMLDocument and create a Resource."""
        node = doc.query('/m:object')[0]
        title = node['title']
        description = node.get('description')
        return Resource(title=title, description=description)


class PersonFileFactory(ApplicationObjectFileFactory):
    """Adapter that adapts PersonContainer to FileFactory"""

    adapts(IPersonContainer)

    schema = '''<?xml version="1.0" encoding="UTF-8"?>
        <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                 ns="http://schooltool.org/ns/model/0.1"
                 datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
          <start>
            <element name="object">
              <attribute name="title">
                <text/>
              </attribute>
            </element>
          </start>
        </grammar>
        '''

    def create(self, doc, name):
        """Extract data from an XMLDocument and create a Person."""
        node = doc.query('/m:object')[0]
        title = node['title']
        return Person(title=title, username=name)


class ApplicationView(View):
    """The root view for the application."""

    template = Template("www/app.pt", content_type="text/xml; charset=UTF-8")

    def getContainers(self):
        return [{'href': zapi.absoluteURL(self.context[key], self.request),
                 'title': key} for key in self.context.keys()]


class GenericContainerView(View):
    """A RESTive container view superclass."""

    template = Template("www/aoc.pt", content_type="text/xml; charset=UTF-8")

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
        """Creates a new object from the data supplied in the request."""

        response = self.request.response
        body = self.request.bodyFile.read()

        factory = self._factory(self.context)
        item = factory(None, None, body)
        self.add(item)
        location = zapi.absoluteURL(item, self.request)

        response.setStatus(201, 'Created')
        response.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        response.setHeader('Location', location)

        return _("Object created: %s") % location


class GroupContainerView(GenericContainerView):
    """RESTive view of a group container."""

    _factory = GroupFileFactory


class ResourceContainerView(GenericContainerView):
    """RESTive view of a resource container."""

    _factory = ResourceFileFactory


class PersonContainerView(GenericContainerView):
    """RESTive view of a person container."""

    _factory = PersonFileFactory

