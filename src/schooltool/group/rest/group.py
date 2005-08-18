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
RESTive views for Groups

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
from zope.component import adapts

from schoolbell.app.rest import View, Template
from schoolbell.app.rest.app import ApplicationObjectFile
from schoolbell.app.rest.app import ApplicationObjectFileFactory
from schoolbell.app.rest.app import GenericContainerView

from schoolbell.app.group.group import Group
from schoolbell.app.group.interfaces import IGroupContainer, IGroup


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

    factory = Group

    def parseDoc(self, doc):
        kwargs = {}
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        kwargs['description'] = node.get('description')
        return kwargs


class GroupFile(ApplicationObjectFile):
    """Adapter that adapts IGroup to IWriteFile"""

    adapts(IGroup)

    def modify(self, title=None, description=None):
        """Modify underlying schema."""
        self.context.title = title
        self.context.description = description


class GroupContainerView(GenericContainerView):
    """RESTive view of a group container."""


class GroupView(View):
    """RESTive view for groups"""

    template = Template("group.pt",
                        content_type="text/xml; charset=UTF-8")
    factory = GroupFile
