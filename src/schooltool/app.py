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
SchoolTool application

$Id$

"""

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app import zapi
from zope.app.component.hooks import getSite
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.container.btree import BTreeContainer
from zope.app.container.contained import Contained
from zope.app.container.sample import SampleContainer
from zope.app.site.servicecontainer import SiteManagerContainer
from zope.app.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.app.security.interfaces import IUnauthenticatedGroup

from schoolbell.relationship import RelationshipProperty
from schoolbell.relationship.relationship import BoundRelationshipProperty
from schoolbell.app.interfaces import IHaveNotes, IApplicationPreferences
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIGroup, URIMember
from schoolbell.app.overlay import choose_color, DEFAULT_COLORS
from schoolbell.app.overlay import OverlaidCalendarsProperty
from schoolbell.app.overlay import BoundOverlaidCalendarsProperty
from schoolbell.app.overlay import CalendarOverlayInfo
from schoolbell.app import app as sb

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import IPersonContainer, IGroupContainer
from schooltool.interfaces import IResourceContainer
from schooltool.interfaces import IPerson, IGroup, IResource, ICourse
from schooltool.interfaces import ISectionContained, ISectionContainer
from schooltool.interfaces import ICourseContainer, ICourseContained
from schooltool.interfaces import IPersonPreferences
from schooltool.interfaces import ICalendarAndTTOverlayInfo
from schooltool.relationships import URIInstruction, URISection, URIInstructor
from schooltool.relationships import URICourseSections, URICourse
from schooltool.relationships import URISectionOfCourse
from schooltool.timetable import TermContainer, TimetableSchemaContainer
from schooltool.timetable import TimetabledMixin


class SchoolToolApplication(Persistent, SampleContainer, SiteManagerContainer,
                            TimetabledMixin):
    """The main SchoolTool application object."""

    implements(ISchoolToolApplication, IAttributeAnnotatable)

    def __init__(self):
        SampleContainer.__init__(self)
        TimetabledMixin.__init__(self)
        self['persons'] = PersonContainer()
        self['groups'] = GroupContainer()
        self['resources'] = ResourceContainer()
        self['terms'] = TermContainer()
        self['courses'] = CourseContainer()
        self['sections'] = SectionContainer()
        self['ttschemas'] = TimetableSchemaContainer()
        # Local import to avoid recursive imports
        import schooltool.level.level
        self['levels'] = schooltool.level.level.LevelContainer()

        self.calendar = Calendar(self)

        # Set up initial groups
        self['groups']['manager'] = Group(u'Manager', u'Manager Group.')

    def _newContainerData(self):
        return PersistentDict()

    def title(self):
        """This is required for the site calendar views to work."""
        return IApplicationPreferences(self).title


class OverlaidCalendarsAndTTProperty(object):
    """Property for `overlaid_calendars` in SchoolTool.

    Stores the list of overlaid calendars in relationships.

    Example:

        >>> class SomeClass(object): # must be a new-style class
        ...     calendars = OverlaidCalendarsAndTTProperty()

        >>> someinstance = SomeClass()
        >>> someinstance.calendars
        <schooltool.app.BoundOverlaidCalendarsAndTTProperty object at 0x...>

    """

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return BoundOverlaidCalendarsAndTTProperty(instance)


class BoundOverlaidCalendarsAndTTProperty(BoundOverlaidCalendarsProperty):
    """Bound property for `overlaid_calendars` in SchoolTool.

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schoolbell.relationship.tests import SomeObject
        >>> from schoolbell.relationship import getRelatedObjects
        >>> setUp()

    Given a relatable object, and a relatable calendar

        >>> a = SomeObject('a')
        >>> cal = SomeObject('cal')

    we can create a BoundOverlaidCalendarsProperty

        >>> overlaid_calendars = BoundOverlaidCalendarsAndTTProperty(a)

    The `add` method establishes a URICalendarSubscriber relationship

        >>> overlaid_calendars.add(cal, show=False, show_timetables=False,
        ...                        color1="red", color2="green")

        >>> from schoolbell.app.overlay import URICalendarProvider
        >>> from schoolbell.app.overlay import URICalendarSubscriber
        >>> getRelatedObjects(a, URICalendarProvider)
        [cal]
        >>> getRelatedObjects(cal, URICalendarSubscriber)
        [a]

    You can extract these when iterating

        >>> for item in overlaid_calendars:
        ...     print item.calendar, item.show, item.show_timetables
        ...     print item.color1, item.color2
        cal False False
        red green

    We're done.

        >>> tearDown()

    """

    def add(self, calendar, show=True, show_timetables=True,
            color1=None, color2=None):
        if not color1 or not color2:
            used_colors = [(item.color1, item.color2) for item in self]
            color1, color2 = choose_color(DEFAULT_COLORS, used_colors)
        info = CalendarAndTTOverlayInfo(calendar, show, show_timetables,
                                        color1, color2)
        info.__parent__ = self.this
        BoundRelationshipProperty.add(self, calendar, info)


class CalendarAndTTOverlayInfo(CalendarOverlayInfo):
    """Tests for CalendarAndTTOverlayInfo.

    CalendarAndTTOverlayInfo is much like the ordinary CalendarOverlayInfo
    object, with one difference: it has an extra attribute `show_timetables`.

        >>> calendar = object()
        >>> item = CalendarAndTTOverlayInfo(calendar, True, False,
        ...                                 'red', 'yellow')

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(ICalendarAndTTOverlayInfo, item)
        True

        >>> item.show
        True
        >>> item.show_timetables
        False

    The `show_timetables` attribute is changeable:

        >>> item.show_timetables = True

    """

    implements(ICalendarAndTTOverlayInfo)

    def __init__(self, calendar, show, show_timetables, color1, color2):
        self._calendar = calendar
        self.show = show
        self.show_timetables = show_timetables
        self.color1 = color1
        self.color2 = color2


class Person(sb.Person, TimetabledMixin):

    implements(IPerson)

    overlaid_calendars = OverlaidCalendarsAndTTProperty()

    def __init__(self, *args, **kw):
        sb.Person.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class Group(sb.Group, TimetabledMixin):

    implements(IGroup)

    def __init__(self, *args, **kw):
        sb.Group.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class Resource(sb.Resource, TimetabledMixin):

    implements(IResource)

    def __init__(self, *args, **kw):
        sb.Resource.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class CourseContainer(BTreeContainer):
    """Container of Courses."""

    implements(ICourseContainer, IAttributeAnnotatable)

    def __conform__(self, protocol):
        if protocol is sb.ISchoolBellApplication:
            return self.__parent__


class Course(Persistent, Contained, TimetabledMixin):

    implements(ICourseContained, IHaveNotes, IAttributeAnnotatable)

    sections = RelationshipProperty(URICourseSections, URICourse,
                                    URISectionOfCourse)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description

    # XXX not sure this is needed anymore, and it should be SchoolTool anyway
    def __conform__(self, protocol):
        if protocol is sb.ISchoolBellApplication:
            return self.__parent__.__parent__


class Section(Persistent, Contained, TimetabledMixin):

    implements(ISectionContained, IHaveNotes, IAttributeAnnotatable)

    def _getLabel(self):
        instructors = " ".join([i.title for i in self.instructors])
        courses = " ".join([c.title for c in self.courses])
        msg = _('${instructors} -- ${courses}')
        msg.mapping = {'instructors': instructors, 'courses': courses}
        return msg

    label = property(_getLabel)

    def _getSize(self):
        size = 0
        for member in self.members:
            if IPerson.providedBy(member):
                size = size + 1
            if IGroup.providedBy(member):
                size = size + len(member.members)

        return size

    size = property(_getSize)

    _location = None

    def _setLocation(self, location):
        if location is not None:
            if not IResource.providedBy(location) or not location.isLocation:
                raise TypeError("Locations must be location resources.")
        self._location = location

    location = property(lambda self: self._location, _setLocation)

    instructors = RelationshipProperty(URIInstruction, URISection,
                                       URIInstructor)

    courses = RelationshipProperty(URICourseSections, URISectionOfCourse,
                                   URICourse)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)


    def __init__(self, title="Section", description=None, schedule=None,
                 courses=None, location=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)
        self.location = location
        TimetabledMixin.__init__(self)

    def __conform__(self, protocol):
        if protocol is sb.ISchoolBellApplication:
            return self.__parent__.__parent__


class SectionContainer(BTreeContainer):
    """Container of Sections."""

    implements(ISectionContainer, IAttributeAnnotatable)

    def __conform__(self, protocol):
        if protocol is sb.ISchoolBellApplication:
            return self.__parent__


class PersonContainer(sb.PersonContainer):
    """A container for SchoolTool persons"""

    implements(IPersonContainer)


class GroupContainer(sb.GroupContainer):
    """A container for groups, sections and courses."""

    implements(IGroupContainer)


class ResourceContainer(sb.ResourceContainer):
    """A container for SchoolTool resources."""

    implements(IResourceContainer)


class PersonPreferences(sb.PersonPreferences):

    implements(IPersonPreferences)

    cal_periods = True


def getPersonPreferences(person):
    """Adapt an IAnnotatable object to IPersonPreferences."""
    prefs = sb.getPersonPreferences(person)
    if IPersonPreferences.providedBy(prefs):
        # A SchoolTool preferences object was found
        return prefs
    else:
        # A SchoolBell preferences object was found.
        # We need to replace it with a SchoolTool-specific one.
        st_prefs = PersonPreferences()
        st_prefs.__parent__ = person
        for field in sb.IPersonPreferences:
            value = getattr(prefs, field)
            setattr(st_prefs, field, value)
        annotations = IAnnotations(person)
        annotations[sb.PERSON_PREFERENCES_KEY] = st_prefs
        return st_prefs


class ApplicationPreferences(sb.ApplicationPreferences):
    """Object for storing any application-wide preferences we have."""

    title = 'SchoolTool'


def getSchoolToolApplication():
    """Return the nearest ISchoolToolApplication"""
    candidate = getSite()
    if ISchoolToolApplication.providedBy(candidate):
        return candidate
    else:
        raise ValueError("can't get a SchoolToolApplication")


def getApplicationPreferences(app):
    """Adapt a SchoolToolApplication to IApplicationPreferences."""

    annotations = IAnnotations(app)
    key = 'schooltool.app.ApplicationPreferences'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = ApplicationPreferences()
        annotations[key].__parent__ = app
        return annotations[key]


def applicationCalendarPermissionsSubscriber(event):
    """Set the default permissions for schooltool.

    By default view and viewCalendar are granted for unauthenticated users to
    the top level application so that everyone can see the front page and the
    the sitewide calendar without logging in.

    Because permissions are applied recursively, we must restrict access
    explicitly to the areas of the site that should not be public.

    By default we restrict:
        school/persons
        school/groups
        school/resources
        school/sections
        school/courses

    """
    if not IObjectAddedEvent.providedBy(event):
        # TODO: Do we need to do this in python if the subscriber is set in
        # zcml?
        return

    if ISchoolToolApplication.providedBy(event.object):
        unauthenticated = zapi.queryUtility(IUnauthenticatedGroup)

        app_perms = IPrincipalPermissionManager(event.object)
        app_perms.grantPermissionToPrincipal('schoolbell.view',
                                          unauthenticated.id)
        app_perms.grantPermissionToPrincipal('schoolbell.viewCalendar',
                                          unauthenticated.id)

        for container in ['persons', 'groups', 'resources', 'sections',
                          'courses']:
            container_perms = IPrincipalPermissionManager(event.object[container])
            container_perms.denyPermissionToPrincipal('schoolbell.view',
                                              unauthenticated.id)
            container_perms.denyPermissionToPrincipal('schoolbell.viewCalendar',
                                              unauthenticated.id)
