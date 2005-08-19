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
REST interface for level objects

$Id$
"""
import zope.component
from schooltool.app import app, rest

from schooltool.level import interfaces, level


class LevelFileFactory(rest.app.ApplicationObjectFileFactory):
    """Adapter that adapts LevelContainer to FileFactory."""

    zope.component.adapts(interfaces.ILevelContainer)

    schema = '''<?xml version="1.0" encoding="UTF-8"?>
        <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                 ns="http://schooltool.org/ns/model/0.1"
                 datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
          <start>
            <element name="object">
              <attribute name="title">
                <text/>
              </attribute>
              <attribute name="isInitial">
                <data type="boolean" />
              </attribute>
              <optional>
                <attribute name="nextLevel">
                  <text/>
                </attribute>
              </optional>
            </element>
          </start>
        </grammar>
        '''

    factory = level.Level

    def parseDoc(self, doc):
        kwargs = {}
        levels = app.getSchoolToolApplication()['levels']
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        kwargs['isInitial'] = node.get('isInitial')
        levelid = node.get('nextLevel')
        try:
            kwargs['nextLevel'] = levelid and levels[levelid] or None
        except KeyError:
            raise rest.errors.RestError("No such level.")
        return kwargs


class LevelContainerView(rest.app.GenericContainerView):
    """RESTive view of a level container."""


class LevelFile(rest.app.ApplicationObjectFile):
    """Adapter that adapts ILevel to IWriteFile"""

    zope.component.adapts(interfaces.ILevel)

    def modify(self, title=None, isInitial=False, nextLevel=None):
        """Modifies underlying schema."""
        self.context.title = title
        self.context.isInitial = isInitial
        self.context.nextLevel = nextLevel


class LevelView(rest.View):
    """RESTive view for levels."""

    template = rest.Template("level.pt",
                             content_type="text/xml; charset=UTF-8")
    factory = LevelFile
