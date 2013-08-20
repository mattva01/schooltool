#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
School year implementation
"""
from zope.interface import Interface
from zope.schema import Date, TextLine
from zope.location.interfaces import ILocation
from zope.container.interfaces import IWriteContainer
from zope.container.interfaces import IReadContainer
from zope.container.interfaces import IContainer
from zope.container import constraints

from schooltool.term.interfaces import ITermContainer
from schooltool.common import SchoolToolMessage as _


class IWriteSchoolYear(IWriteContainer):
    """An interface for the write aspects of a container."""


class IReadSchoolYear(IReadContainer, ILocation):

    title = TextLine(
        title=_("Title"))

    first = Date(
        title=_(u"The first day of the period of time covered."))

    last = Date(
        title=_(u"The last day of the period covered."))


class ISchoolYear(IWriteSchoolYear, IReadSchoolYear, ITermContainer):
    """School year"""


class ISchoolYearContainer(IContainer, ILocation):
    """Container for school years"""
    constraints.contains(ISchoolYear)

    def validateForOverlap(schoolyear):
        """Validate school year for overlap with other school years."""

    def getActiveSchoolYear():
        """Return the active schoolyear."""


class ISubscriber(Interface):
    """An event handler implements this"""

    def __call__():
        """Perform the action."""


class TermOverlapError(Exception):

    def __init__(self, term, overlapping_terms):
        self.term = term
        self.overlapping_terms = overlapping_terms

    def __repr__(self):
        return "Date range you have selected overlaps with term(s) (%s)" % (
            ", ".join(sorted(term.title
                             for term in self.overlapping_terms)))

    __str__ = __repr__


class TermOverflowError(Exception):

    def __init__(self, schoolyear, overflowing_terms):
        self.schoolyear = schoolyear
        self.overflowing_terms = overflowing_terms

    def __repr__(self):
        return "Date range you are trying to set is too small to contain following term(s) (%s)" % (
            ", ".join(sorted(term.title
                             for term in self.overflowing_terms)))

    __str__ = __repr__


class SchoolYearOverlapError(Exception):

    def __init__(self, schoolyear, overlapping_schoolyears):
        self.schoolyear = schoolyear
        self.overlapping_schoolyears = overlapping_schoolyears

    def __repr__(self):
        if self.schoolyear is not None:
            title = "SchoolYear '%s'" % self.schoolyear.title
        else:
            title = "DateRange"

        return  "%s overlaps with SchoolYear(s) (%s)" % (
                title,
                ", ".join(sorted(schoolyear.title
                                 for schoolyear in self.overlapping_schoolyears)))

    __str__ = __repr__
