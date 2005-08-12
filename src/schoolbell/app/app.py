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
__docformat__ = 'restructuredtext'

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.component import adapts
from zope.event import notify
from zope.interface import implements

from zope.app.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.app.component.hooks import getSite
from zope.app.component.site import SiteManagerContainer
from zope.app.container import btree, sample
from zope.app.container.contained import Contained, NameChooser
from zope.app.container.interfaces import INameChooser, IObjectAddedEvent
from zope.app.location.interfaces import ILocation

import schoolbell.app.note.interfaces
from schoolbell.app import interfaces
from schoolbell.app import note
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIMember, URIGroup
from schoolbell.app.overlay import OverlaidCalendarsProperty
from schoolbell.relationship import RelationshipProperty


class SchoolBellApplication(Persistent, sample.SampleContainer,
                            SiteManagerContainer):
    """The main application object.

    This object can be added as a regular content object to a folder,
    or it can be used as the application root object.
    """

    implements(interfaces.ISchoolBellApplication, IAttributeAnnotatable)

    def __init__(self):
        super(SchoolBellApplication, self).__init__()
        self['groups'] = GroupContainer()
        self['resources'] = ResourceContainer()
        self.calendar = Calendar(self)
        notify(interfaces.ApplicationInitializationEvent(self))

    def _newContainerData(self):
        return PersistentDict()

    def title(self):
        """This is required for the site calendar views to work."""
        return interfaces.IApplicationPreferences(self).title
    title = property(title)


class GroupContainer(btree.BTreeContainer):
    """Container of groups."""

    implements(interfaces.IGroupContainer, IAttributeAnnotatable)


class ResourceContainer(btree.BTreeContainer):
    """Container of resources."""

    implements(interfaces.IResourceContainer, IAttributeAnnotatable)


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

        >>> from schoolbell.app.person.person import Person
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


class Group(Persistent, Contained):
    """Group."""

    implements(interfaces.IGroupContained, note.interfaces.IHaveNotes,
               IAttributeAnnotatable)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)


class Resource(Persistent, Contained):
    """Resource."""

    implements(interfaces.IResourceContained, note.interfaces.IHaveNotes,
               IAttributeAnnotatable)

    isLocation = False # backwards compatibility

    def __init__(self, title=None, description=None, isLocation=False):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)
        self.isLocation = isLocation


def getSchoolBellApplication():
    """Return the nearest ISchoolBellApplication"""
    candidate = getSite()
    if interfaces.ISchoolBellApplication.providedBy(candidate):
        return candidate
    else:
        raise ValueError("can't get a SchoolBellApplication")


class ApplicationPreferences(Persistent):
    """Object for storing any application-wide preferences we have.

    See schoolbell.app.interfaces.ApplicationPreferences.
    """
    implements(interfaces.IApplicationPreferences)
    adapts(interfaces.ISchoolBellApplication)

    title = 'SchoolBell'

    frontPageCalendar = True


def getApplicationPreferences(app):
    """Adapt a SchoolBellApplication to IApplicationPreferences."""

    annotations = IAnnotations(app)
    key = 'schoolbell.app.ApplicationPreferences'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = ApplicationPreferences()
        annotations[key].__parent__ = app
        return annotations[key]
