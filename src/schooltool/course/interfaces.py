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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Course and Section related interfaces
"""

import zope.schema
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains, containers
from zope.interface import Interface, Attribute

from schooltool.app.interfaces import IRelationshipState
from schooltool.group.interfaces import IBaseGroup as IGroup
from schooltool.common import SchoolToolMessage as _


class ICourse(Interface):
    """Courses are similar to groups, membership is restricted to Sections."""

    __name__ = zope.schema.TextLine(
        title=_("SchoolTool ID"),
        description=_(
            """An internal identifier of this course."""),
        required=True)

    title = zope.schema.TextLine(title=_("Title"))

    description = zope.schema.Text(
        title=_("Description"),
        required=False)

    sections = Attribute(
        """The Sections that implement this course material,
           see schooltool.relationship.interfaces.IRelationshipProperty.""")

    course_id = zope.schema.TextLine(
        title=_("Course ID"),
        description=_(
            """School identifier of this course."""),
        required=False)

    government_id = zope.schema.TextLine(
        title=_("Alternate ID"),
        required=False,
        description=_(
            "Additional identifier for outside tracking or other purposes."))

    credits = zope.schema.Decimal(
        title=_("Credits"),
        required=False)


class ICourseContainer(IContainer):
    """Container of Courses."""

    contains(ICourse)


class ICourseContainerContainer(IContainer):
    """Container of Courses."""

    contains(ICourseContainer)


class ICourseContained(ICourse, IContained):
    """Courses contained in an ICourseContainer."""

    containers(ICourseContainer)


class ISectionBase(IGroup):
    """Sections are groups of users in a particular meeting of a Course."""

    label = zope.schema.TextLine(
        title=_("Label"),
        required=False,
        description=_(
            "An identifier for a section, made up of instructor "
            "names, courses, and meeting time."))

    title = zope.schema.TextLine(
        title=_("Title"),
        required=True)

    description = zope.schema.Text(
        title=_("Description"),
        required=False)

    instructors = Attribute(
        """A list of Person objects in the role of instructor""")

    members = Attribute(
        """Students listed in the role of member""")

    courses = Attribute(
        """A list of courses this section is a member of.""")

    size = Attribute(
        """The number of member students in the section.""")

    previous = Attribute(
        """The previous section.""")

    next = Attribute(
        """The next section.""")

    linked_sections = Attribute(
        """Chain of sections linked by previous/next with this one.""")


class ISection(ISectionBase):

    __name__ = zope.schema.TextLine(
        title=_("SchoolTool ID"),
        description=_(
            """An internal identifier of this section."""),
        required=True)


class ISectionContainer(IContainer):
    """A container for Sections."""

    contains(ISection)


class ISectionContainerContainer(IContainer):
    """A container for Section containers."""

    contains(ISectionContainer)


class ISectionContained(ISection, IContained):
    """Sections in a SectionContainer."""

    containers(ISectionContainer)


class ILearner(Interface):

    def sections():
        """List of all the sections this learner belongs to."""


class IInstructor(Interface):

    def sections():
        """List of all the sections this instructor is teaching to."""


class IStudentRelationshipState(IRelationshipState):

    completed = zope.schema.Bool(
        title=_(u'Completed'), required=True)
