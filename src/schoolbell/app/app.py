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
from zope.app.container.contained import NameChooser
from zope.app.container.interfaces import INameChooser
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.site.servicecontainer import SiteManagerContainer
from zope.app.location.interfaces import ILocation
from zope.app.annotation.interfaces import IAnnotations
from zope.app.component.hooks import setSite, getSite

from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import IPersonContainer, IPersonContained
from schoolbell.app.interfaces import IPersonPreferences
from schoolbell.app.interfaces import IGroupContainer, IGroupContained
from schoolbell.app.interfaces import IResourceContainer, IResourceContained
from schoolbell.app.interfaces import IHavePreferences
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIMember, URIGroup
from schoolbell.app.overlay import OverlaidCalendarsProperty
from schoolbell.relationship import RelationshipProperty


class SchoolBellApplication(Persistent, SampleContainer,
                            SiteManagerContainer):
    """The main application object.

    This object can be added as a regular content object to a folder,
    or it can be used as the application root object.
    """

    implements(ISchoolBellApplication, IAttributeAnnotatable)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = PersonContainer()
        self['groups'] = GroupContainer()
        self['resources'] = ResourceContainer()

    def _newContainerData(self):
        return PersistentDict()


class PersonContainer(BTreeContainer):
    """Container of persons."""

    implements(IPersonContainer, IAttributeAnnotatable)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__

    def __setitem__(self, key, person):
        """See `IWriteContainer`

        Ignores `key` and uses `person.username` as the key.
        """
        key = person.username
        BTreeContainer.__setitem__(self, key, person)


class GroupContainer(BTreeContainer):
    """Container of groups."""

    implements(IGroupContainer, IAttributeAnnotatable)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__


class ResourceContainer(BTreeContainer):
    """Container of resources."""

    implements(IResourceContainer, IAttributeAnnotatable)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__


class SimpleNameChooser(NameChooser):
    """A name chooser that uses object titles as names.

    SimpleNameChooser is an adapter for containers

        >>> container = {}
        >>> chooser = SimpleNameChooser(container)

    It expects objects to have a `title` attribute, so only register it
    as an adapter for containers that limit their contents to objects
    with such attribute.

    `chooseName` uses the title of the object to be added, converts it to
    lowercase, strips punctuation, and replaces spaces with hyphens:

        >>> obj = Person(title='Mr. Smith')
        >>> chooser.chooseName('', obj)
        u'mr-smith'

    If the name is already taken, SimpleNameChooser adds a number at the end

        >>> container['mr-smith'] = 42
        >>> chooser.chooseName('', obj)
        u'mr-smith-2'

    If you provide a suggested name, it uses that one.

        >>> chooser.chooseName('suggested-name', obj)
        'suggested-name'

    Bad names cause errors

        >>> chooser.chooseName('@notallowed', obj)
        Traceback (most recent call last):
          ...
        UserError: Names cannot begin with '+' or '@' or contain '/'

    """

    implements(INameChooser)

    def chooseName(self, name, obj):
        """See INameChooser."""
        if not name:
            name = u''.join([c for c in obj.title.lower()
                             if c.isalnum() or c == ' ']).replace(' ', '-')
        n = name
        i = 1
        while n in self.context:
            i += 1
            n = name + u'-' + unicode(i)
        # Make sure the name is valid
        self.checkName(n, obj)
        return n


class Person(Persistent, Contained):
    """Person."""

    implements(IPersonContained, IHavePreferences, IAttributeAnnotatable)

    photo = None
    username = None
    _hashed_password = None

    groups = RelationshipProperty(URIMembership, URIMember, URIGroup)
    overlaid_calendars = OverlaidCalendarsProperty()

    def __init__(self, username=None, title=None):
        self.title = title
        self.username = username
        self.calendar = Calendar(self)

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


class PersonPreferences(Persistent):

    implements(IPersonPreferences)

    def __init__(self):
        self.timezone = "UTC"
        self.dateformat = "YYYY-MM-DD"
        self.timeformat = "HH:MM"
        self.weekstart = "Monday"


def getPersonPreferences(person):
    """Adapt an IAnnotatable object to IPersonPreferences."""
    annotations = IAnnotations(person)
    key = 'schoolbell.app.PersonPreferences'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = PersonPreferences()
        annotations[key].__parent__ = person
        return annotations[key]


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

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__.__parent__


class Resource(Persistent, Contained):
    """Resource."""

    implements(IResourceContained, IAttributeAnnotatable)

    groups = RelationshipProperty(URIMembership, URIMember, URIGroup)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)

    def __conform__(self, protocol):
        if protocol is ISchoolBellApplication:
            return self.__parent__.__parent__


def getSchoolBellApplication():
    """Return the nearest ISchoolBellApplication"""

    candidate = getSite()
    if ISchoolBellApplication.providedBy(candidate):
        return candidate
    else:
        raise ValueError("can't get a SchoolBellApplication")
