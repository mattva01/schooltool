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
from zodb.btrees.IOBTree import IOBTree
from schooltool.model import Person, Group
from schooltool.views import View, Template
from schooltool.db import PersistentKeysDict


__metaclass__ = type


#
#  Crap ripped off of membership.py
#

class MemberMixin(Persistent):
    """A mixin providing the IGroupMember interface.

    Also, it implements ILocation by setting the first group the
    member is added to as a parent, and clearing it if the member is
    removed from it.
    """

    def __init__(self):
        self._groups = PersistentKeysDict()
        self.__name__ = None
        self.__parent__ = None

    def groups(self):
        """See IGroupMember"""
        return self._groups.keys()

    def notifyAdded(self, group, name):
        """See IGroupMember"""
        self._groups[group] = name
        if self.__parent__ is None:
            self.__parent__ = group
            self.__name__ = str(name)

    def notifyRemoved(self, group):
        """See IGroupMember"""
        del self._groups[group]
        if group == self.__parent__:
            self.__parent__ = None
            self.__name__ = None


class GroupMixin(Persistent):
    """This class is a mixin which makes things a group"""

    def __init__(self):
        self._next_key = 0
        self._members = IOBTree()

    def keys(self):
        """See IGroup"""
        return self._members.keys()

    def values(self):
        """See IGroup"""
        return self._members.values()

    def items(self):
        """See IGroup"""
        return self._members.items()

    def __getitem__(self, key):
        """See IGroup"""
        return self._members[key]

    def add(self, member):
        """See IGroup"""
        key = self._next_key
        self._next_key += 1
        self._members[key] = member
        self._addhook(member)
        member.notifyAdded(self, key)
        # XXX this should send events as well
        return key

    def __delitem__(self, key):
        """See IGroup"""
        member = self._members[key]
        self._deletehook(member)
        del self._members[key]
        member.notifyRemoved(self)
        # XXX this should send event and call unlink notifications as well

    # Hooks for use by mixers-in

    def _addhook(self, member):
        pass

    def _deletehook(self, member):
        pass


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
    data = readFile('www/mockup_photo.jpg')


class FakePerson(Person, MemberMixin):

    def __init__(self, name):
        Person.__init__(self, name)
        MemberMixin.__init__(self)

    photo = FakePhoto()


class FakeGroup(Group, GroupMixin, MemberMixin):

    def __init__(self, name):
        Group.__init__(self, name)
        MemberMixin.__init__(self)
        GroupMixin.__init__(self)


class FakeApplication(Persistent):

    def __init__(self):
        self.root = FakeGroup("root")
        self.people = FakeGroup("people")
        self.root.add(self.people)
        self.people.add(FakePerson('John'))
        self.people.add(FakePerson('Steve'))
        self.people.add(FakePerson('Mark'))
        self.counter = 0
        self.root = FakeGroup("root")


#
#  Views for mockup objects
#

class RootView(View):
    """View for the application root."""

    template = Template('www/mockup_root.pt')

    def counter(self):
        self.context.counter += 1
        return self.context.counter

    def _traverse(self, name, request):
        if name == 'people':
            return PeopleView(self.context.people)
        raise KeyError(name)


class PeopleView(View):
    """View for /people"""

    template = Template('www/mockup_people.pt')

    def _traverse(self, name, request):
        try:
            person = self.context[int(name)]
            return PersonView(person)
        except (ValueError, TypeError):
            raise KeyError(name)


class PersonView(View):
    """View for /people/person_name"""

    template = Template('www/mockup_person.pt')

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

