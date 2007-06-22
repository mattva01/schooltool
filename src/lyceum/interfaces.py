#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Interfaces for Lyceum specific code.

$Id$

"""
from zope.interface import Interface
from zope.interface import Attribute
from zope.schema import TextLine
from zope.schema.interfaces import IIterableSource

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.calendar.interfaces import ICalendar

from lyceum import LyceumMessage as _


class ILyceumPersonSource(IIterableSource):
    """Marker interface for sources that list lyceum persons."""


# XXX should be in skin or common, or more properly - core
class IGroupSource(IIterableSource):
    """Marker interface for sources that list schooltool groups."""


class ISchoolToolLyceumApplication(ISchoolToolApplication):
    """Marker interface for lyceum specific school."""


class IGroupTimetableCalendar(ICalendar):

    title = TextLine(title=_(u"Title of the calendar"))


class IStudent(Interface):

    advisor = Attribute("""Advisor of a student.""")


class IAdvisor(Interface):

    students = Attribute("""Students being advised by the advisor.""")

    def addStudent(student):
        """Add a student to the advised students list."""

    def removeStudent(student):
        """Remove this student from the advised students list."""
