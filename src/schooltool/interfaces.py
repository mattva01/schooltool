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
SchoolTool application interfaces

$Id$
"""

from zope.interface import Attribute

from schooltool import SchoolToolMessageID as _
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import IGroup

class ISchoolToolApplication(ISchoolBellApplication):
    """The main SchoolTool application object"""


class ICourse(IGroup):
    """Courses are groups of Sections."""


class ISection(IGroup):
    """Sections are groups of users in a particular meeting of a Course."""

    teachers = Attribute(
               """XXX A list of Person objects in the role of instructor""")

    students = Attribute(
               """XXX A list of Person objects in the role of learner""")

    schedule = Attribute("""
                   a representation of the calendar events and recurrences \
                   that make up this section's meetings """)

    courses = Attribute(
               """XXX A list of courses this section is a member of.""")
