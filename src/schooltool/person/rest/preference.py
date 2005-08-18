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
RESTive views for Person Preferences

$Id: app.py 4596 2005-08-08 12:53:09Z gintas $
"""
from zope.component import adapts
from zope.interface import implements

from schoolbell.app.rest import View, Template, IRestTraverser
from schoolbell.app.rest.errors import RestError
from schoolbell.app.rest.xmlparsing import XMLDocument

from schoolbell.app.person.interfaces import IPerson
from schoolbell.app.person.interfaces import IPersonPreferences
from schoolbell.app.person.rest.interfaces import IPersonPreferencesAdapter


class PersonPreferencesAdapter(object):
    """Adapter of person to IPreferencesWriter"""

    implements(IPersonPreferencesAdapter)

    def __init__(self, person):
        self.person = person


class PersonPreferencesView(View):
    """A view for Persons preferences."""

    template = Template("person-preferences.pt",
                        content_type="text/xml; charset=UTF-8")

    schema = """<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0"
         xmlns:xlink="http://www.w3.org/1999/xlink"
         ns="http://schooltool.org/ns/model/0.1"
         datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
      <start>
        <element name="preferences">
          <zeroOrMore>
            <element name="preference">
              <attribute name="id"><text/></attribute>
              <attribute name="value"><text/></attribute>
            </element>
          </zeroOrMore>
        </element>
      </start>
    </grammar>"""

    def __init__(self, context, request):
        View.__init__(self, context, request)
        self.preferences = IPersonPreferences(context.person)

    def parseData(self, body):
        """Get values from document, and put them into a dict"""
        doc = XMLDocument(body, self.schema)
        results = {}
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            for preference in doc.query('/m:preferences/m:preference'):
                results[preference['id']] = preference['value']
        finally:
            doc.free()

        return results

    def validatePreference(self, name, value):
        """Validate a preference.

        Validates against IPersonPreferences widgets and raises RestError if:

        * 'name' is not defined in the interface
        * 'value' does not pass widget validation
        """
        if name not in IPersonPreferences.names():
            raise RestError('Preference "%s" unknown' % name)

        try:
            IPersonPreferences.get(name).validate(value)
        except Exception:
            raise RestError('Preference value "%s" does not'
                            ' pass validation on "%s"' % (value, name))

    def PUT(self):
        """Extract data and validate it.

        Validates preferences through validatePreference which can return a
        RestError.
        """
        data = self.parseData(self.request.bodyFile.read())
        for name, value in data.items():
            self.validatePreference(name, value)
            setattr(self.preferences, name, value)

        return "Preferences updated"


class PersonPreferencesHTTPTraverser(object):
    """Traverser to person preferences."""

    adapts(IPerson)
    implements(IRestTraverser)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        return PersonPreferencesAdapter(self.context)
