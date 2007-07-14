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
Course and Section related interfaces

$Id$
"""
import zope.interface
import zope.schema
from zope.app import container
from zope.interface import Interface

from schooltool.group.interfaces import IBaseGroup as IGroup
from schooltool import SchoolToolMessage as _


class ICourse(zope.interface.Interface):
    """Courses are similar to groups, membership is restricted to Sections."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the course."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the course."))

    sections = zope.interface.Attribute(
        """The Sections that implement this course material,
           see schooltool.relationship.interfaces.IRelationshipProperty.""")


class ICourseContainer(container.interfaces.IContainer):
    """Container of Courses."""

    container.constraints.contains(ICourse)


class ICourseContained(ICourse, container.interfaces.IContained):
    """Courses contained in an ICourseContainer."""

    container.constraints.containers(ICourseContainer)


class ISection(IGroup):
    """Sections are groups of users in a particular meeting of a Course."""

    label = zope.schema.TextLine(
        title=_("Label"),
        required=False,
        description=_(
            """An identifier for a section, made up of instructor
            names, courses, and meeting time."""))

    title = zope.schema.TextLine(
        title=_("Title"),
        required=True,
        description=_("Title for the section."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the section."))

    instructors = zope.interface.Attribute(
        """A list of Person objects in the role of instructor""")

    members = zope.interface.Attribute(
        """Students listed in the role of member""")

    courses = zope.interface.Attribute(
        """A list of courses this section is a member of.""")

    size = zope.interface.Attribute(
        """The number of member students in the section.""")


class ISectionContainer(container.interfaces.IContainer):
    """A container for Sections."""

    container.constraints.contains(ISection)


class ISectionContained(ISection, container.interfaces.IContained):
    """Sections in a SectionContainer."""

    container.constraints.containers(ISectionContainer)


class ILearner(Interface):

    def sections():
        """List of all the sections this learner belongs to."""
