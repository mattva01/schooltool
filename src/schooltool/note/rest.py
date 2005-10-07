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
RESTive views for notes

$Id$
"""

from zope.interface import Interface, Attribute, implements
from zope.security.checker import ProxyFactory

from schooltool.xmlparsing import XMLDocument
from schooltool.app.rest import View, Template
from schooltool.note.interfaces import INotes
from schooltool.note.note import Note


def NotesViewFactory(context, request):
    return ProxyFactory(NotesView(context, request))

class INotesView(Interface):
    """Interface for RESTive view of notes."""

    notes = Attribute("A list of Note objects")

    schema = Attribute("A RNG schema for the accepted XML document")

    template = Attribute("The template of the generated XML document")

    def GET():
        """The GET handler."""

    def POST():
        """The POST handler."""


class NotesView(View):
    """A view of notes on IHaveNotes providers."""

    implements(INotesView)

    template = Template("rest_notes.pt",
                        content_type="text/xml; charset=UTF-8")

    schema = """<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0"
             ns="http://schooltool.org/ns/model/0.1"
             datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
      <start>
        <element name="notes">
          <zeroOrMore>
            <element name="note">
              <attribute name="title">
                <text/>
              </attribute>
              <attribute name="privacy">
                <choice>
                  <value>private</value>
                  <value>public</value>
                </choice>
              </attribute>
              <attribute name="body">
                <text/>
              </attribute>
            </element>
          </zeroOrMore>
        </element>
      </start>
    </grammar>"""

    def __init__(self, adapter, request):
        self.context = adapter.context
        self.request = request
        self._notes = INotes(self.context)

    def _getNotes(self):
        return [note for note in self._notes if note.privacy == 'public'
                or note.owner == self.request.principal.id]

    notes = property(_getNotes)

    def POST(self):
        body = self.request.bodyFile.read()

        doc = XMLDocument(body, self.schema)
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            for node in doc.query('/m:notes/m:note'):
                self.createAndAdd(node)
        finally:
            doc.free()

        return ''

    def createAndAdd(self, node):
        owner = self.request.principal.id
        note = Note(title=node['title'], body=node['body'],
                    privacy=node['privacy'], owner=owner)

        self._notes.add(note)


class NotesTraverser(object):
    """Allows traversing into notes of an IHaveNotes provider."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        return NotesAdapter(self.context)


class INotesAdapter(Interface):
    """Adapter for RESTivew view of notes."""


class NotesAdapter:
    """A proxy to which the Notes view is hooked up"""

    implements(INotesAdapter)

    def __init__(self, context):
        self.context = context


