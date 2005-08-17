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
RESTive views for Courses

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
from zope.component import adapts

from schoolbell.app.rest import View, Template
from schoolbell.app.rest.app import ApplicationObjectFile
from schoolbell.app.rest.app import ApplicationObjectFileFactory
from schoolbell.app.rest.app import GenericContainerView
from schoolbell.app.rest.errors import RestError

from schooltool.app import getSchoolToolApplication
from schooltool.course.section import Section
from schooltool.course.interfaces import ISectionContainer, ISection

class SectionFileFactory(ApplicationObjectFileFactory):
    """Adapter that adapts SectionContainer to FileFactory."""

    adapts(ISectionContainer)

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
                <attribute name="course">
                  <text/>
                </attribute>
              </optional>
              <optional>
                <attribute name="description">
                  <text/>
                </attribute>
              </optional>
              <optional>
                <attribute name="location">
                  <text/>
                </attribute>
              </optional>
            </element>
          </start>
        </grammar>
        '''

    factory = Section

    def parseDoc(self, doc):
        kwargs = {}
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        kwargs['description'] = node.get('description')
        # Locations can be requested by title, we map them to the actual
        # Resource object here:
        desired_location = node.get('location')
        if desired_location:
            resources = getSchoolToolApplication()['resources']
            try:
                location = resources[desired_location]
                kwargs['location'] = location
            except KeyError:
                raise RestError("No such location.")
        return kwargs


class SectionContainerView(GenericContainerView):
    """RESTive view of a section container."""


class SectionFile(ApplicationObjectFile):
    """Adapter that adapts ISection to IWriteFile"""

    adapts(ISection)

    def modify(self, title=None, description=None):
        """Modifies underlying schema."""
        self.context.title = title
        self.context.description = description


class SectionView(View):
    """RESTive view for sections."""

    template = Template("section.pt",
                        content_type="text/xml; charset=UTF-8")
