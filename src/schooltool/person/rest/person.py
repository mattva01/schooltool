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
RESTive views for Person

$Id: app.py 4596 2005-08-08 12:53:09Z gintas $
"""
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces import NotFound

from schooltool.app.rest import View, Template
from schooltool.app.rest.app import ApplicationObjectFile
from schooltool.app.rest.app import ApplicationObjectFileFactory
from schooltool.app.rest.app import GenericContainerView
from schooltool.traverser.traverser import AdapterTraverserPlugin

from schooltool.person.interfaces import IPersonContainer, IPerson
from schooltool.person.person import Person
from schooltool.person.rest.interfaces import IPasswordWriter, IPersonPhoto


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
        """Get values from document, and puts them into a dict."""
        kwargs = {}
        node = doc.query('/m:object')[0]
        kwargs['title'] = node['title']
        return kwargs

    def __call__(self, name, content_type, data):
        #Call is overrided in here so we could pass the name to
        #Persons __init__
        return self.factory(username=name, **self.parseXML(data))


class PersonFile(ApplicationObjectFile):
    """Adapter that adapts IPerson to IWriteFile"""

    adapts(IPerson)

    def modify(self, title=None):
        """Modify underlying object."""
        self.context.title = title


class PersonContainerView(GenericContainerView):
    """RESTive view of a person container."""


class PersonView(View):
    """RESTive view for persons"""

    template = Template("person.pt",
                        content_type="text/xml; charset=UTF-8")
    factory = PersonFile


PersonPasswordHTTPTraverser = AdapterTraverserPlugin(
    'password', IPasswordWriter)


class PersonPasswordWriter(object):
    """Adapter of person to IPasswordWriter."""
    adapts(IPerson)
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

        body = self.request.bodyStream
        password = body.read().split("\n")[0]
        self.context.setPassword(password)
        self.request.response.setStatus("200")
        return ''


PersonPhotoHTTPTraverser = AdapterTraverserPlugin('photo', IPersonPhoto)


class PersonPhotoAdapter(object):
    """Adapt a Person to PersonPhoto."""
    adapts(IPerson)
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
        return photo

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

        body = self.request.bodyStream
        self.context.writePhoto(body.read())
        self.request.response.setStatus("200")
        return ''


