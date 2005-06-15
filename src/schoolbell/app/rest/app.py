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
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile
from zope.app.http.put import FilePUT
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.i18n import translate
from zope.schema.interfaces import IField

from schoolbell.app.rest import View, Template, IRestTraverser
from schoolbell.app.rest.errors import RestError
from schoolbell.app.rest.interfaces import IPasswordWriter, IPersonPhoto
from schoolbell.app.rest.interfaces import IPersonPreferencesAdapter
from schoolbell.app.rest.xmlparsing import XMLValidationError, XMLParseError
from schoolbell.app.rest.xmlparsing import XMLDocument
from schoolbell.calendar.icalendar import convert_calendar_to_ical
from schoolbell.app.interfaces import IWriteCalendar

from schoolbell.app.app import Group, Resource, Person
from schoolbell.app.interfaces import IGroupContainer, IGroup
from schoolbell.app.interfaces import IResourceContainer, IResource
from schoolbell.app.interfaces import IPersonContainer, IPerson
from schoolbell.app.interfaces import IPersonPreferences
from schoolbell.app.browser.cal import CalendarOwnerHTTPTraverser

class ApplicationObjectFileFactory(object):
    """A superclass for ApplicationObjectContainer to FileFactory adapters."""

    implements(IFileFactory)

    def __init__(self, container):
        self.context = container

    def parseXML(self, data):
        """Gets values from document, and puts them into a dict"""
        doc = XMLDocument(data, self.schema)
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            return self.parseDoc(doc)
        finally:
            doc.free()

    def __call__(self, name, content_type, data):
        return self.factory(**self.parseXML(data))


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
        """Gets values from document, and puts them into a dict"""
        kwargs = {}
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        kwargs['description'] = node.get('description')
        kwargs['isLocation'] = (node.get('isLocation') == "true")
        return kwargs


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

    factory = Person

    def parseDoc(self, doc):
        """Gets values from document, and puts them into a dict"""
        kwargs = {}
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        return kwargs

    def __call__(self, name, content_type, data):
        #Call is overrided in here so we could pass the name to
        #Persons __init__
        return self.factory(username=name, **self.parseXML(data))


class ApplicationObjectFile(object):
    """Adapter adapting Application Objects to IWriteFile"""

    implements(IWriteFile)

    def __init__(self, context):
        self.context = context

    def write(self, data):
        """See IWriteFile"""
        container = self.context.__parent__
        factory = IFileFactory(container)
        kwargs = factory.parseXML(data)
        self.modify(**kwargs)


class GroupFile(ApplicationObjectFile):
    """Adapter that adapts IGroup to IWriteFile"""

    adapts(IGroup)

    def modify(self, title=None, description=None):
        """Modifies underlying schema."""
        self.context.title = title
        self.context.description = description


class ResourceFile(ApplicationObjectFile):
    """Adapter that adapts IResource to IWriteFile"""

    adapts(IResource)

    def modify(self, title=None, description=None, isLocation=False):
        """Modifies underlying object."""
        self.context.title = title
        self.context.description = description
        self.context.isLocation = isLocation


class PersonFile(ApplicationObjectFile):
    """Adapter that adapts IPerson to IWriteFile"""

    adapts(IPerson)

    def modify(self, title=None):
        """Modifies underlying object."""
        self.context.title = title


class ApplicationView(View):
    """The root view for the application."""

    template = Template("templates/app.pt",
                        content_type="text/xml; charset=UTF-8")

    def getContainers(self):
        return [{'href': zapi.absoluteURL(self.context[key], self.request),
                 'title': key} for key in self.context.keys()]


class GenericContainerView(View):
    """A RESTive container view superclass."""

    template = Template("templates/aoc.pt",
                        content_type="text/xml; charset=UTF-8")

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
        """Create a new object from the data supplied in the request."""

        response = self.request.response
        body = self.request.bodyFile.read()

        factory = IFileFactory(self.context)
        item = factory(None, None, body)
        self.add(item)
        location = zapi.absoluteURL(item, self.request)

        response.setStatus(201, 'Created')
        response.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        response.setHeader('Location', location)
        return u"Object created: %s" % location


class GroupContainerView(GenericContainerView):
    """RESTive view of a group container."""


class ResourceContainerView(GenericContainerView):
    """RESTive view of a resource container."""


class PersonContainerView(GenericContainerView):
    """RESTive view of a person container."""


class GroupView(View):
    """RESTive view for groups"""

    template = Template("templates/group.pt",
                        content_type="text/xml; charset=UTF-8")
    factory = GroupFile


class ResourceView(View):
    """RESTive view for resources"""

    template = Template("templates/resource.pt",
                        content_type="text/xml; charset=UTF-8")
    factory = ResourceFile


class PersonView(View):
    """RESTive view for persons"""

    template = Template("templates/person.pt",
                        content_type="text/xml; charset=UTF-8")
    factory = PersonFile



def getCharset(content_type, default="UTF-8"):
    """Get charset out of content-type

        >>> getCharset('text/xml; charset=latin-1')
        'latin-1'

        >>> getCharset('text/xml; charset=yada-yada')
        'yada-yada'

        >>> getCharset('text/xml; charset=yada-yada; fo=ba')
        'yada-yada'

        >>> getCharset('text/plain')
        'UTF-8'

        >>> getCharset(None)
        'UTF-8'

    """
    if not content_type:
        return default

    parts = content_type.split(";")
    if len(parts) == 0:
        return default

    stripped_parts = [part.strip() for part in parts]

    charsets = [part for part in stripped_parts
                if part.startswith("charset=")]

    if len(charsets) == 0:
        return default

    return charsets[0].split("=")[1]


class CalendarView(View):
    """Restive view for calendars"""

    def GET(self):
        data = "\r\n".join(convert_calendar_to_ical(self.context)) + "\r\n"
        request = self.request
        request.response.setHeader('Content-Type',
                                   'text/calendar; charset=UTF-8')
        request.response.setHeader('Content-Length', len(data))
        request.response.setStatus(200)
        request.response.write(data)
        return request.response

    def PUT(self):
        request = self.request

        for name in request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                request.response.setStatus(501)
                return ''

        body = self.request.bodyFile
        data = body.read()
        charset = getCharset(self.request.getHeader("Content-Type"))

        adapter = IWriteCalendar(self.context)
        adapter.write(data, charset)
        return ''


class PersonHTTPTraverser(CalendarOwnerHTTPTraverser):
    """A traverser that allows to traverse to a persons password, preferences or photo."""

    adapts(IPerson)
    implements(IRestTraverser)

    def publishTraverse(self, request, name):
        if name == 'password':
            return PersonPasswordWriter(self.context)
        elif name == 'photo':
            return PersonPhotoAdapter(self.context)
        elif name == 'preferences':
            return PersonPreferencesAdapter(self.context)

        return CalendarOwnerHTTPTraverser.publishTraverse(self, request, name)


class PersonPasswordWriter(object):
    """Adapter of person to IPasswordWriter."""

    implements(IPasswordWriter)

    def __init__(self, person):
        self.person = person

    def setPassword(self, password):
        """See IPasswordWriter."""

        self.person.setPassword(password)


class PasswordWriterView(View):
    """A view that enables setting password of a Person."""

    def PUT(self):
        request = self.request

        for name in request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                request.response.setStatus(501)
                return ''

        body = self.request.bodyFile
        password = body.read().split("\n")[0]
        self.context.setPassword(password)
        self.request.response.setStatus("200")
        return ''


class PersonPhotoAdapter(object):
    """Adapts a Person to PersonPhoto."""

    implements(IPersonPhoto)

    def __init__(self, person):
        self.person = person

    def writePhoto(self, data):
        """See IPersonPhoto."""

        self.person.photo = data

    def deletePhoto(self):
        """See IPersonPhoto."""

        self.person.photo = None

    def getPhoto(self):
        """See IPersonPhoto."""

        return self.person.photo


class PersonPhotoView(View):
    """A view for Persons photo."""

    def GET(self):
        photo = self.context.getPhoto()

        if photo is None:
            raise NotFound(self.context, u'photo', self.request)

        self.request.response.setHeader('Content-Type', "image/jpeg")
        self.request.response.setStatus(200)
        self.request.response.write(photo)
        return self.request.response

    def DELETE(self):
        self.context.deletePhoto()
        return ''

    def PUT(self):
        request = self.request

        for name in request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                request.response.setStatus(501)
                return ''

        body = self.request.bodyFile
        self.context.writePhoto(body.read())
        self.request.response.setStatus("200")
        return ''


class PersonPreferencesAdapter(object):
    """Adapter of person to IPreferencesWriter"""

    implements(IPersonPreferencesAdapter)

    def __init__(self, person):
        self.person = person


class PersonPreferencesView(View):
    """A view for Persons preferences."""

    template = Template("templates/person-preferences.pt",
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
        """Gets values from document, and puts them into a dict"""
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
            raise RestError('Preference value "%s" does not pass validation on "%s"' % (value, name))

    def PUT(self):
        """Extract data and validate it.

        Validates preferences through validatePreference which can return a
        RestError.
        """
        data = self.parseData(self.request.bodyFile.read())
        for name,value in data.items():
            self.validatePreference(name, value)
            setattr(self.preferences, name, value)

        return "Preferences updated"


class CalendarNullTraverser(object):
    """A null traverser for calendars

    It allows to access .../calendar/calendar.ics and similar.

    >>> calendar = object()
    >>> request = object()
    >>> trav = CalendarNullTraverser(calendar, request)
    >>> trav.publishTraverse(request, 'calendar.ics') is calendar
    True
    >>> trav.publishTraverse(request, 'calendar.vfb') is calendar
    True
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        return self.context
