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
SchoolBell application object

$Id$
"""

import sha

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app.container.btree import BTreeContainer
from zope.app.container.sample import SampleContainer
from zope.app.container.contained import Contained
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.site.servicecontainer import ServiceManagerContainer
from zope.app.location.interfaces import ILocation

from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import IPersonContainer, IPersonContained
from schoolbell.app.interfaces import IGroupContainer, IGroupContained
from schoolbell.app.interfaces import IResourceContainer, IResourceContained
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIMember, URIGroup
from schoolbell.relationship import RelationshipProperty


class SchoolBellApplication(Persistent, SampleContainer,
                            ServiceManagerContainer):
    """The main application object.

    This object can be added as a regular content object to a folder,
    TODO: or it can be used as the application root object.
    """

    implements(ISchoolBellApplication)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = PersonContainer()
        self['groups'] = GroupContainer()
        self['resources'] = ResourceContainer()

    def _newContainerData(self):
        return PersistentDict()


class PersonContainer(BTreeContainer):
    """Container of persons."""

    implements(IPersonContainer)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__


class GroupContainer(BTreeContainer):
    """Container of groups."""

    implements(IGroupContainer)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__


class ResourceContainer(BTreeContainer):
    """Container of resources."""

    implements(IResourceContainer)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__


class Person(Persistent, Contained):
    """Person."""

    implements(IPersonContained, IAttributeAnnotatable)

    photo = None
    username = None
    _hashed_password = None

    groups = RelationshipProperty(URIMembership, URIMember, URIGroup)

    def __init__(self, title=None):
        self.title = title
        self.calendar = Calendar()

    def setPassword(self, password):
        self._hashed_password = hash_password(password)

    def checkPassword(self, password):
        return (self._hashed_password is not None
                and hash_password(password) == self._hashed_password)

    def hasPassword(self):
        return self._hashed_password is not None

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__.__parent__


def hash_password(password):
    r"""Compute a SHA-1 hash of a given password.

        >>> hash_password('secret')
        '\xe5\xe9\xfa\x1b\xa3\x1e\xcd\x1a\xe8Ou\xca\xaaGO:f?\x05\xf4'

    Passwords should be ASCII or Unicode strings.

        >>> hash_password('\u263B')
        '\xe4\x13\xef\x8dv3\xba*P\xbb1\xa2k\x9c|,n\xe3mL'

    To avoid problems with a multitude of 8-bit encodings, they are forbidden

        >>> hash_password('\xFF') # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        UnicodeDecodeError: 'ascii' codec can't decode byte 0xff in ...

    None means "no password set, account is locked":

        >>> hash_password(None) is None
        True

    Security note: passwords are not salted, so it is possible to detect
    users that have the same password.
    """
    if password is None:
        return None
    return sha.sha(password.encode('UTF-8')).digest()


class Group(Persistent, Contained):
    """Group."""

    implements(IGroupContained, IAttributeAnnotatable)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    groups = RelationshipProperty(URIMembership, URIMember, URIGroup)

    def __init__(self, title=None):
        self.title = title

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__.__parent__


class Resource(Persistent, Contained):
    """Resource."""

    implements(IResourceContained, IAttributeAnnotatable)

    groups = RelationshipProperty(URIMembership, URIMember, URIGroup)

    def __init__(self, title=None):
        self.title = title

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__.__parent__


def getSchoolBellApplication(obj):
    """Return the nearest ISchoolBellApplication from ancestors of obj"""
    cur = obj
    while True:
        if ISchoolBellApplication.providedBy(cur):
            return cur

        if ILocation.providedBy(cur):
            cur = cur.__parent__
        else:
            cur = None

        if cur is None:
            raise ValueError("can't get a SchoolBellApplication from %r" % obj)
