#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
The mockup objects for the HTTP server.

$Id$
"""
import os
from persistence import Persistent
from schooltool.model import Person, Group
from schooltool.views import View, Template

#
# Some fake content
#

def readFile(filename):
    dirname = os.path.dirname(__file__)
    pathname = os.path.join(dirname, filename)
    f = open(pathname)
    data = f.read()
    f.close()
    return data


class FakePhoto:

    format = 'image/jpeg'
    data = readFile('photo.jpg')


class FakePerson(Person):

    photo = FakePhoto()


class FakeApplication(Persistent):

    def __init__(self):
        self.root = Group("root")
        self.people = Group("people")
        self.people.add(FakePerson('John'))
        self.people.add(FakePerson('Steve'))
        self.people.add(FakePerson('Mark'))
        self.counter = 0
        self.root = Group("root")
        self.root.add(self.people)



#
#  Views for mockup objects
#

class RootView(View):
    """View for the application root."""

    template = Template('www/root.pt')

    def counter(self):
        self.context.counter += 1
        return self.context.counter

    def _traverse(self, name, request):
        if name == 'people':
            return PeopleView(self.context.people)
        raise KeyError(name)


class PeopleView(View):
    """View for /people"""

    template = Template('www/people.pt')

    def _traverse(self, name, request):
        person = self.context[int(name)]
        return PersonView(person)


class PersonView(View):
    """View for /people/person_name"""

    template = Template('www/person.pt')

    def _traverse(self, name, request):
        if name == 'photo':
            return PhotoView(self.context.photo)
        raise KeyError(name)


class PhotoView(View):
    """View for /people/person_name/photo"""

    def render(self, request):
        if request.method == 'GET':
            request.setHeader('Content-Type', self.context.format)
            return self.context.data
        elif request.method == 'HEAD':
            request.setHeader('Content-Type', self.context.format)
            request.setHeader('Content-Length', len(self.context.data))
            return ""
        else:
            request.setHeader('Allow', 'GET, HEAD')
            return errorPage(request, 405, "Method Not Allowed")

