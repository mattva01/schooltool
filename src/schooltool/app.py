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

SchoolTool currently provides a SchoolBell based calendar server that adds
school specific features.  In addition to the basic SchoolBell Person, Groups,
and Resources, SchoolTool adds Course and Sections.

We need some test setup:

    >>> from schoolbell.relationship.tests import setUp, tearDown
    >>> setUp()

    >>> school = SchoolToolApplication()
    >>> school['courses']
    <schooltool.app.CourseContainer object at ...>
    >>> school['sections']
    <schooltool.app.SectionContainer object at ...>

A Course is a simple object with a title and description that can describe a
particular course of study.

    >>> ushistory = Course(title="US History", description="Years 1945 - 2000")
    >>> school['courses']['ushistory'] = ushistory

    >>> ushistory.title
    'US History'

    >>> ushistory.description
    'Years 1945 - 2000'

The educational material covered by a course is taugh to sets of students in
Sections.  Each section is related to the Course with the CourseSections
relationship and the list of sections can be accessed via the Course.sections
RelationshipProperty.

We haven't set up any sections yet so:

    >>> [section.title for section in ushistory.sections]
    []

is empty.  Lets create some sections and add them to US History.

    >>> school['sections']['section1'] = section1 = Section(title="Section 1")
    >>> school['sections']['section2'] = section2 = Section(title="Section 2")
    >>> ushistory.sections.add(section1)
    >>> ushistory.sections.add(section2)
    >>> [section.title for section in ushistory.sections]
    ['Section 1', 'Section 2']

Each section represents a particular set of students meeting with a particular
instructor at a particular time to cover the course material.

    >>> school['persons']['teacher1'] = teacher1 = Person('Teacher1')
    >>> school['persons']['teacher2'] = teacher2 = Person('Teacher2')
    >>> school['persons']['student1'] = student1 = Person('Student1')
    >>> school['persons']['student2'] = student2 = Person('Student2')
    >>> school['persons']['student3'] = student3 = Person('Student3')
    >>> school['persons']['student4'] = student4 = Person('Student4')

The teacher of a section is defined with the Instruction relationship and can
be accessed via the section.instructors RelationshipProperty:

    >>> from schooltool.relationships import Instruction
    >>> [teacher.username for teacher in section1.instructors]
    []
    >>> Instruction(instructor=teacher1, section=section1)
    >>> [teacher.username for teacher in section1.instructors]
    ['Teacher1']

sections can have more than one instructor:

    >>> section1.instructors.add(teacher2)
    >>> [teacher.username for teacher in section1.instructors]
    ['Teacher1', 'Teacher2']

sections students are associated with a section via the Membership
relationship from SchoolBell or via the section.members property.  The section
itself participates in the Membership relationship in the URIGroup role which
is possible because Sections implement the IGroup interface.

    >>> [student.username for student in section1.members]
    []
    >>> from schoolbell.app.membership import Membership
    >>> Membership(group=section1, member=student1)
    >>> Membership(group=section1, member=student2)
    >>> [student.username for student in section1.members]
    ['Student1', 'Student2']

We can use Groups to add multiple students to a section to keep the group of
students together, similar to the "Form" concept used in some US Primary
schools.

    >>> school['groups']['form1'] = form1 = Group(title="Form1")
    >>> form1.members.add(student3)
    >>> form1.members.add(student4)
    >>> section2.members.add(form1)
    >>> [form.title for form in section2.members]
    ['Form1']

See schooltool.browser.app for showing individual members of the form in the
UI.

Sections can be part of more than 1 course and sections have a courses
RelatioshipProperty to list what courses they implement.

    >>> amlit = Course(title="American Literature",
    ...                    description="Taught with US History")
    >>> school['courses']['almit'] = ushistory
    >>> amlit.sections.add(section1)
    >>> [section.title for section in amlit.sections]
    ['Section 1']
    >>> [course.title for course in section1.courses]
    ['US History', 'American Literature']

    >>> tearDown()

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
