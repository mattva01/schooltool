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
from zope.app.component.hooks import getSite
from zope.app.container.btree import BTreeContainer
from zope.app.container.contained import Contained
from zope.app.container.sample import SampleContainer
from zope.app.site.servicecontainer import SiteManagerContainer
from zope.app.annotation.interfaces import IAttributeAnnotatable, IAnnotations

from schoolbell.relationship import RelationshipProperty
from schoolbell.app.interfaces import IHaveNotes
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIGroup, URIMember
from schoolbell.app import app as sb

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import IPersonContainer, IGroupContainer
from schooltool.interfaces import IResourceContainer
from schooltool.interfaces import IPerson, IGroup, IResource, ICourse
from schooltool.interfaces import ISectionContained, ISectionContainer
from schooltool.interfaces import ICourseContainer, ICourseContained
from schooltool.interfaces import IPersonPreferences
from schooltool.relationships import URIInstruction, URISection, URIInstructor
from schooltool.relationships import URICourseSections, URICourse
from schooltool.relationships import URISectionOfCourse
from schooltool.timetable import TermContainer, TimetableSchemaContainer
from schooltool.timetable import TimetabledMixin


class SchoolToolApplication(Persistent, SampleContainer, SiteManagerContainer):
    """The main SchoolTool application object"""

    implements(ISchoolToolApplication, IAttributeAnnotatable)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = PersonContainer()
        self['groups'] = GroupContainer()
        self['resources'] = ResourceContainer()
        self['terms'] = TermContainer()
        self['courses'] = CourseContainer()
        self['sections'] = SectionContainer()
        self['ttschemas'] = TimetableSchemaContainer()

    def _newContainerData(self):
        return PersistentDict()


class Group(sb.Group, TimetabledMixin):

    implements(IGroup)

    def __init__(self, *args, **kw):
        sb.Group.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class Person(sb.Person, TimetabledMixin):

    implements(IPerson)

    def __init__(self, *args, **kw):
        sb.Person.__init__(self, *args, **kw)
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
        msg = _('${instructors} section of ${courses}')
        msg.mapping = {'instructors': instructors, 'courses': courses}
        return msg

    label = property(_getLabel)

    instructors = RelationshipProperty(URIInstruction, URISection,
                                       URIInstructor)

    courses = RelationshipProperty(URICourseSections, URISectionOfCourse,
                                   URICourse)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    def __init__(self, title="Section", description=None, schedule=None,
                 courses=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)
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


def getSchoolToolApplication():
    """Return the nearest ISchoolBellApplication"""
    candidate = getSite()
    if ISchoolToolApplication.providedBy(candidate):
        return candidate
    else:
        raise ValueError("can't get a SchoolToolApplication")
