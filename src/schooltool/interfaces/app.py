#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
Interfaces for timetabling objects in SchoolTool.

$Id$
"""

from schooltool.unchanged import Unchanged  # reexport from here
from zope.interface import Interface
from zope.app.location.interfaces import ILocation
from zope.app.traversing.interfaces import ITraversable
from zope.schema import Field, Object, TextLine, Text, List, Set
from zope.schema import Bool, Choice, Date, Datetime, Bytes, BytesLine
from schooltool.interfaces.relationship import IRelatable
from schooltool.interfaces.facet import IFaceted, IFacet
from schooltool.interfaces.event import IEvent, IEventTarget
from schooltool.interfaces.event import IEventConfigurable
from schooltool.interfaces.cal import ICalendarOwner
from schooltool.interfaces.timetable import ITimetabled
from schooltool.interfaces.auth import IACLOwner
from schooltool.interfaces.component import IUtility


class IAvailabilitySearch(Interface):
    """An interface for querying the availability of resources."""

    def getFreeIntervals(first, last, time_periods, duration):
        """Return all intervals of time not shorter than duration
        when the object is free within a range of dates [first, last]
        during the times of day specified by time_periods.

        first, last    datetime.date objects specifying a range of dates.

        time_periods   a sequence of tuples (start_time, duration)
                       specifying the time of day.  These are
                       respectively datetime.time and
                       datetime.timedelta objects

        duration       datetime.timedelta object specifying a minimum
                       interval of time we're searching for.

        The returned value is a sequence of tuples (start_datetime, duration).
        """

    def getFreePeriods(first, last, timetable_periods):
        """Return all timetable periods when the object is free within a range
        of dates [first, last].  Only those timetable periods that are listed
        in timetable_periods are considered.

        first, last    datetime.date objects specifying a range of dates.

        timetable_periods
                       a sequence of timetable period IDs.

        Returns a sequence of tuples (start_datetime, duration, period_id).
        """


class IApplicationObject(ILocation, IRelatable, IEventTarget,
                         IEventConfigurable, IFaceted, ICalendarOwner,
                         ITimetabled, IAvailabilitySearch, IACLOwner):
    """A collection of interfaces common to all application objects."""

    title = TextLine(
        title=u"Title of the application object")


class IGroup(IApplicationObject):
    """A set of group members.

    Participates in URIMembership as URIGroup or URIMember.
    """


class IPerson(IApplicationObject):
    """A person.

    Participates in URIMembership as URIMember.
    """

    title = TextLine(
        title=u"Person's full name""")

    username = TextLine(
        title=u"The username of this person")

    def iterAbsences():
        """Iterate over all absences."""

    def getAbsence(key):
        """Return the absence with a given key."""

    def getCurrentAbsence():
        """Return the current absence or None.

        At any given time a person can have at most one absence that is not
        ended.  It is called the current absence.
        """

    def reportAbsence(comment):
        """Report that this person is absent, still absent, or no
        longer absent.

        Returns the IAbsence which may be a new absence or this
        person's current absence extended by the comment.
        """

    def setPassword(password):
        """Set the password in a hashed form, so it can be verified later."""

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


class IResource(IApplicationObject):
    """A bookable resource used in."""


class IAbsenceComment(Interface):
    """An absence comment."""

    __parent__ = Field(
        title=u"The absence this comment belongs to")

    datetime = Datetime(
        title=u"Date and time of the comment")

    reporter = Object(
        title=u"Person that made this comment",
        schema=IPerson)

    text = Text(
        title=u"Text of the comment")

    absent_from = Object(
        title=u"Application object the person was absent from.",
        required=False,
        schema=IApplicationObject)

    ended = Choice(
        title=u"New value of ended",
        values=[True, False, Unchanged])

    resolved = Choice(
        title=u"New value of resolved",
        values=[True, False, Unchanged])

    expected_presence = Field(
        title=u"New value of expected_presence (datetime, None, or Unchanged)",
        required=False)


class IAbsence(ILocation):
    """Absence object.

    The __parent__ of an absence is its person.  The absence can be
    located by invoking IPerson.getAbsence(absence.__name__).

    All attributes are read-only.  They can be changed by adding new
    comments, therefore the list of comments also doubles as an audit log.
    """

    person = Object(
        title=u"Person that was absent",
        schema=IPerson)

    comments = List(
        title=u"Comments",
        value_type=Object(title=u"Absence comment", schema=IAbsenceComment))

    ended = Bool(
        title=u"Has this absence been ended?")

    resolved = Bool(
        title=u"Has this absence been resolved?")

    expected_presence = Datetime(
        title=u"Date and time after which a person is expected to be present")

    def addComment(comment):
        """Add a comment.

        Sends out an IAbsenceEvent after the comment has been added.  The
        event is sent to the person and all application objects that the
        person was absent from.
        """


class IAttendanceEvent(IEvent):
    """Event that gets sent out when an absence is recorded or updated."""

    absence = Object(
        title=u"The absence",
        schema=IAbsence)

    comment = Object(
        title=u"The absence comment that describes the change",
        schema=IAbsenceComment)


class IAbsenceEvent(IAttendanceEvent):
    """An event that gets sent when a person is found absent."""


class IAbsenceEndedEvent(IAttendanceEvent):
    """An event that gets sent when an absence is ended."""


class IAbsenceTracker(IEventTarget):
    """An object which listens to the AttendanceEvents and keeps a set
    of unended absences."""

    absences = Set(
        title=u"A set of unended absences this object has been notified of.",
        value_type=Object(title=u"Absence", schema=IAbsence))


class IAbsenceTrackerUtility(IUtility, IAbsenceTracker):
    pass


class IAbsenceTrackerFacet(IFacet, IEventConfigurable, IAbsenceTracker):
    pass


class IOptions(Interface):
    """User-selectable options of the system."""

    new_event_privacy = Choice(
        title=u"The default privacy setting of newly created calendar events.",
        values=['public', 'private', 'hidden'])

    timetable_privacy = Choice(
        title=u"The value of the privacy attribute for timetable events.",
        values=['public', 'private', 'hidden'])

    restrict_membership = Bool(
        title=u"Restricted group membership mode.",
        description=u"""
        If True, membership in every group is restricted to the members of
        immediate parent groups.  If False, any object can be added to any
        group.
        """)


class IApplicationObjectContainer(ILocation, ITraversable):
    """A collection of application objects."""

    def __getitem__(name):
        """Return the contained object that has the given name."""

    def new(__name__=None, **kw):
        """Create and return a new contained object.

        If __name__ is None, a name is chosen for the object.
        Otherwise, __name__ is a unicode or seven bit safe string.
        The rest of the keyword arguments are passed to the object's
        constructor.

        If the given name is already taken, raises a KeyError.

        The contained object will be an ILocation, and will have this
        container as its __parent__, and the name as its __name__.
        """

    def __delitem__(name):
        """Remove the contained object that has the given name.

        Raises a KeyError if there is no such object.
        """

    def keys():
        """Return a list of the names of contained objects."""

    def itervalues():
        """Iterate over all contained objects."""


class IAuthenticator(Interface):

    def __call__(context, username, password):
        """Authenticate a user given a username and password.

        Returns an authentication token (IPerson object) if successful.
        Raises AuthenticationError if not.
        """


class IDynamicSchemaField(Interface):
    """A display-agnostic field definition.

    Stores custom form fields where browser and ReSTive views can access them.
    """

    def __getitem__(key):
        """Get a custom field by name."""

    def __setitem__(key, value):
        """Set a custom field."""

    def __eq__(other):
        """Equality test for custom fields.

        Only compares name and label.
        """


class IDynamicSchema(Interface):
    """General informational attributes for person and address objects"""

    fields = List(
        title=u"Dict of field data",
        value_type=Object(title=u"A dynamic schema field",
                          schema=IDynamicSchemaField))

    def hasField(name):
        """Test for the existence of a field."""

    def getField(name):
        """Return field value."""

    def setField(name, value):
        """Set field value."""

    def delField(name):
        """Remove a field."""

    def addField(name, label, type, value=None, vocabulary=[]):
        """Add a field to the fields dict."""

    def cloneEmpty():
        """Create a copy of this facet and its fields."""

    def __getitem__(key):
        """Return a field from the fields list based on its name."""


class IDynamicSchemaService(ILocation):
    """Service for creating dynamic schema definitions

    This should be subclassed with DynamicFacetService and
    DynamicRelationshipService
    """

    default_id = TextLine(
        title=u"Schema id of the default schema")

    def getDefault():
        """Return the default schema for the school"""

    def keys():
        """Return a sequence of all stored schema ids."""

    def __getitem__(schema_id):
        """Return a new empty DynamicSchema of a given id."""

    def __setitem__(schema_id, dynamicfacet):
        """Store a given DynamicFacet as a schema with a given id."""

    def __delitem__(schema_id):
        """Remove a stored schema with a given id."""


class IDynamicFacetSchemaService(IDynamicSchemaService):
    """Dynamic service for Facets"""


class IDynamicFacet(IDynamicSchema, IFacet):
    """Dynamic schema for generating custom facets"""


class IPersonInfoFacet(IFacet):
    """Some attributes for a person object"""

    first_name = TextLine(
        title=u"First name")

    last_name = TextLine(
        title=u"Last name")

    date_of_birth = Date(
        title=u"Date of birth")

    comment = Bytes(
        title=u"A free form text comment")

    photo = Bytes(
        title=u"Photo (JPEG)")


class INote(ILocation, IRelatable):
    """An abitrary notation on an IApplicationObject."""

    title = TextLine(
        title=u"The title of the note.")

    body = Text(
        title=u"The body of the note.")

    owner = Object(
        title=u"The object that created this note.",
        schema=IApplicationObject)

    created = Datetime(
        title=u"The time the note was created.")


class IResidence(ILocation, IRelatable, IFaceted):
    """The base of a physical address.

    Participates in URIOccupies as occupiedBy.
    """

    country = BytesLine(
        title=u"ISO Country code")


class IAddressFacet(IFacet):
    """Default address attributes

    The default info facet hopefully will cover most use cases.  It is based on
    a draft of the Address Data Interchange Specification (ADIS) version 04-1.
    See http://www.upu.int/document/2004/an/cep_gan-3/d010.pdf for more info.

    The examples show how the standard might map to a locale's terms.

    Note: this is not a comprehensive implementation of the standard, but
    enough to build relationships on.  The full standard should be implemented
    later.
    """

    postcode = TextLine(
        title=u"Postal service sorting code (Ex. Zip in the US, DX in the UK)")

    district = TextLine(
        title=u"District, Ex. US State")

    town = TextLine(
        title=u"Town, Ex. US City")

    streetNr = TextLine(
        title=u"Street number")

    thoroughfareName = TextLine(
        title=u"Street name")
