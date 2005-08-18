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
RESTive views for resource,

$Id: app.py 4704 2005-08-15 13:22:06Z srichter $
"""
from zope.component import adapts

from schooltool.app.rest import View, Template
from schooltool.app.rest.app import ApplicationObjectFile
from schooltool.app.rest.app import ApplicationObjectFileFactory
from schooltool.app.rest.app import GenericContainerView

from schooltool.resource.resource import Resource
from schooltool.resource.interfaces import IResourceContainer, IResource

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
              <optional>
                <attribute name="isLocation">
                  <data type="boolean" />
                </attribute>
              </optional>
            </element>
          </start>
        </grammar>
        '''

    factory = Resource

    def parseDoc(self, doc):
        """Get values from document, and puts them into a dict."""
        kwargs = {}
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        kwargs['description'] = node.get('description')
        kwargs['isLocation'] = (node.get('isLocation') == "true")
        return kwargs


class ResourceFile(ApplicationObjectFile):
    """Adapter that adapts IResource to IWriteFile"""

    adapts(IResource)

    def modify(self, title=None, description=None, isLocation=False):
        """Modify underlying object."""
        self.context.title = title
        self.context.description = description
        self.context.isLocation = isLocation


class ResourceContainerView(GenericContainerView):
    """RESTive view of a resource container."""


class ResourceView(View):
    """RESTive view for resources"""

    template = Template("resource.pt",
                        content_type="text/xml; charset=UTF-8")
    factory = ResourceFile
