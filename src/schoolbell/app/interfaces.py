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
SchoolBell application interfaces

Overview
--------

ISchoolBellApplication is the main interface.  From it you can get to all
persons, groups and resources in the system via IPersonContainer,
IGroupContainer and IResourceContainer.

Persons, as described by IPerson, are users of the system.  Groups and
resources (IGroup, IResource) are passive objects.  Groups may contain
persons and resources, but there are no additional semantics attached
to group membership (at the time of this writing).

IPersonContained, IGroupContained and IResourceContained describe persons,
groups and resources in context of the rest of the application.  Partly it is
done to avoid a circular dependency between IXxxContained and IXxxContainer.

$Id$
"""

from zope.interface import Interface, Attribute
from zope.schema import Text, TextLine, Bytes, Object
from zope.app.container.interfaces import IReadContainer, IContainer
from zope.app.container.interfaces import IContained
from zope.app.container.constraints import contains, containers
from zope.app.security.interfaces import IAuthentication
from schoolbell.calendar.interfaces import ICalendar
from schoolbell.calendar.interfaces import ICalendar, ICalendarEvent


class IContainedCalendarEvent(ICalendarEvent, IContained):
    """An event that is contained in a calendar."""

class INote(Interface):
    """A note."""

    title = TextLine(title=u"Title",
        description=u"Title of the note.")

    body = Text(title=u"Body",
        description=u"Body of the note.")


class INotes(Interface):
    """A set of notes.

    Objects that can have notes are those that have an adapter to INotes.

    See also `INote`.
    """

    def __iter__():
        """Iterate over all notes."""

    def add(note):
        """Add a new note."""

    def remove(note):
        """Remove a note.

        Raises ValueError if note is not in the set.
        """

    def clear():
        """Remove all notes."""

class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Object(
        title=u"The object's calendar.",
        schema=ICalendar)


class IAdaptableToSchoolBellApplication(Interface):
    """An object that knows which application it came from.

    This is a marker interface.  Objects providing this interface can be
    adapted to ISchoolBellApplication.
    """


class IGroupMember(Interface):
    """An object that knows the groups it is a member of."""

    groups = Attribute("""Groups (see IRelationshipProperty)""")


class IReadPerson(IGroupMember):
    """Publically accessible part of IPerson."""

    title = TextLine(title=u"Full name",
        description=u"Name that should be displayed")

    photo = Bytes(title=u"Photo",
        required=False,
        description=u"""Photo (in JPEG format)""")

    username = TextLine(title=u"Username")

    def checkPassword(password):
        """Check if the provided password is the same as the one set
        earlier using setPassword.

        Returns True if the passwords match.
        """

    def hasPassword():
        """Check if the user has a password.

        You can remove user's password (effectively disabling the account) by
        passing None to setPassword.  You can reenable the account by passing
        a new password to setPassword.
        """


class IWritePerson(Interface):
    """Protected part of IPerson."""

    def setPassword(password):
        """Set the password in a hashed form, so it can be verified later.

        Setting password to None disables the user account.
        """


class IPerson(IReadPerson, IWritePerson, ICalendarOwner):
    """Person.

    A person has a number of informative fields such as name, an optional
    photo, and so on.

    A person can also be a user of the system, therefore IPerson defines
    `username`, and methods for setting/checking passwords (`setPassword`,
    `checkPassword` and `hasPassword`).

    Use IPersonContained instead if you want a person in context (that is,
    one that you can use to traverse to other persons/groups/resources).
    """


class IPersonContainer(IContainer, IAdaptableToSchoolBellApplication):
    """Container of persons."""

    contains(IPerson)


class IPersonContained(IPerson, IContained, IAdaptableToSchoolBellApplication):
    """Person contained in an IPersonContainer."""

    containers(IPersonContainer)


class IGroup(ICalendarOwner):
    """Group."""

    title = TextLine(title=u"Title",
        description=u"Title of the group.")

    description = Text(title=u"Description",
        required=False,
        description=u"Description of the group.")

    members = Attribute("""Members of the group (see IRelationshipProperty)""")


class IGroupContainer(IContainer, IAdaptableToSchoolBellApplication):
    """Container of groups."""

    contains(IGroup)


class IGroupContained(IGroup, IContained, IAdaptableToSchoolBellApplication):
    """Group contained in an IGroupContainer."""

    containers(IGroupContainer)


class IResource(IGroupMember, ICalendarOwner):
    """Resource."""

    title = TextLine(title=u"Title",
        description=u"Title of the resource.")

    description = Text(title=u"Description",
        required=False,
        description=u"Description of the resource.")


class IResourceContainer(IContainer, IAdaptableToSchoolBellApplication):
    """Container of resources."""

    contains(IResource)


class IResourceContained(IResource, IContained,
                         IAdaptableToSchoolBellApplication):
    """Group contained in an IGroupContainer."""

    containers(IResourceContainer)


class ISchoolBellApplication(IReadContainer):
    """The main SchoolBell application object.

    The application is a read-only container with the following items:

        'persons' - IPersonContainer
        'groups' - IGroupContainer
        'resources' - IResourceContainer

    This object can be added as a regular content object to a folder, or
    TODO: it can be used as the application root object.
    """


class ISchoolBellAuthentication(IAuthentication):
    """A local authentication utility for SchoolBell"""

    def setCredentials(request, username, password):
        """Save the username and password in the session.

        If the credentials passed are invalid, ValueError is raised.
        """

    def clearCredentials(request):
        """Forget the username and password stored in a session"""
