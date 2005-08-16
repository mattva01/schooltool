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

import zope.component
import zope.interface
from zope.app import zapi
from zope.app.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.app.container import btree, contained
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.app.security.interfaces import IUnauthenticatedGroup
from zope.app.site.servicecontainer import SiteManagerContainer

from schoolbell.relationship import RelationshipProperty
from schoolbell.relationship.relationship import BoundRelationshipProperty
from schoolbell.app import app as sb
from schoolbell.app.cal import Calendar
from schoolbell.app.group.group import Group
from schoolbell.app.membership import URIMembership, URIGroup, URIMember
from schoolbell.app.overlay import ICalendarOverlayInfo
from schoolbell.app.group.interfaces import IGroup
from schoolbell.app.person.interfaces import IPerson
from schoolbell.app.resource.interfaces import IResource

from schooltool import SchoolToolMessageID as _
from schooltool import interfaces, relationships

###############################################################################
# Import objects here, since they will eventually move here as well.

from schoolbell.app.app import SchoolBellApplication as SchoolToolApplication
from schoolbell.app.app import getApplicationPreferences
from schoolbell.app.app import \
     getSchoolBellApplication as getSchoolToolApplication

###############################################################################


def addManagerGroupToApplication(event):
    event.object['groups']['manager'] = Group(u'Manager', u'Manager Group.')


SHOW_TIMETABLES_KEY = 'schooltool.timetable.showTimetables'

class ShowTimetables(object):
    """Adapter from ICalendarOverlayInfo to IShowTimetables.

        >>> from zope.app.testing import setup
        >>> setup.setUpAnnotations()

        >>> from zope.interface import classImplements
        >>> from schoolbell.app.overlay import CalendarOverlayInfo
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> classImplements(CalendarOverlayInfo, IAttributeAnnotatable)

        >>> calendar = object()
        >>> info = CalendarOverlayInfo(calendar, True, 'red', 'yellow')
        >>> stt = ShowTimetables(info)

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(interfaces.IShowTimetables, stt)
        True

        >>> stt.showTimetables
        True

    The `showTimetables` attribute is changeable:

        >>> stt.showTimetables = False
        >>> stt.showTimetables
        False
    """
    zope.component.adapts(ICalendarOverlayInfo)
    zope.interface.implements(interfaces.IShowTimetables)

    def __init__(self, context):
        self.annotations = IAnnotations(context)

    def getShowTimetables(self):
        return self.annotations.get(SHOW_TIMETABLES_KEY, True)

    def setShowTimetables(self, value):
        self.annotations[SHOW_TIMETABLES_KEY] = value

    showTimetables = property(getShowTimetables, setShowTimetables)


class CourseContainer(btree.BTreeContainer):
    """Container of Courses."""

    zope.interface.implements(interfaces.ICourseContainer,
                              IAttributeAnnotatable)


def addCourseContainerToApplication(event):
    event.object['courses'] = CourseContainer()


class Course(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ICourse,
                              interfaces.IHaveNotes,
                              IAttributeAnnotatable)

    sections = RelationshipProperty(relationships.URICourseSections,
                                    relationships.URICourse,
                                    relationships.URISectionOfCourse)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


class Section(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ISection,
                              interfaces.IHaveNotes, IAttributeAnnotatable)

    def __init__(self, title="Section", description=None, schedule=None,
                 courses=None, location=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)
        self.location = location


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
            if (not IResource.providedBy(location) or not location.isLocation):
                raise TypeError("Locations must be location resources.")
        self._location = location

    location = property(lambda self: self._location, _setLocation)

    instructors = RelationshipProperty(relationships.URIInstruction,
                                       relationships.URISection,
                                       relationships.URIInstructor)

    courses = RelationshipProperty(relationships.URICourseSections,
                                   relationships.URISectionOfCourse,
                                   relationships.URICourse)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)


class SectionContainer(btree.BTreeContainer):
    """Container of Sections."""

    zope.interface.implements(interfaces.ISectionContainer,
                              IAttributeAnnotatable)


def addSectionContainerToApplication(event):
    event.object['sections'] = SectionContainer()


class ApplicationPreferences(sb.ApplicationPreferences):
    """Object for storing any application-wide preferences we have."""

    title = 'SchoolTool'


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

    if interfaces.ISchoolToolApplication.providedBy(event.object):
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
