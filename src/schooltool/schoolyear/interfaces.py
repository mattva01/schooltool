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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
School year implementation
"""
from zope.interface import Interface
from zope.schema import Date, TextLine
from zope.location.interfaces import ILocation
from zope.app.container.interfaces import IContainer
from zope.app.container import constraints

from schooltool.term.interfaces import ITermContainer
from schooltool.common import SchoolToolMessage as _


class ISchoolYear(ITermContainer):
    """School year"""

    title = TextLine(
        title=_("Title"))

    first = Date(
        title=u"The first day of the period of time covered.")

    last = Date(
        title=u"The last day of the period covered.")


class ISchoolYearContainer(IContainer, ILocation):
    """Container for school years"""
    constraints.contains(ISchoolYear)


class ISubscriber(Interface):
    """An event handler implements this"""

    def __call__():
        """Perform the action."""


class TermOverlapError(Exception):

    def __init__(self, term, overlapping_terms):
        self.term = term
        self.overlapping_terms = overlapping_terms

    def __repr__(self):
        return "Term '%s' overlaps with Term(s) (%s)" % (
            self.term.title,
            ", ".join(sorted(term.title
                             for term in self.overlapping_terms)))

    __str__ = __repr__


class SchoolYearOverlapError(Exception):

    def __init__(self, schoolyear, overlapping_schoolyears):
        self.schoolyear = schoolyear
        self.overlapping_schoolyears = overlapping_schoolyears

    def __repr__(self):
        return "SchoolYear '%s' overlaps with SchoolYear(s) (%s)" % (
            self.schoolyear.title,
            ", ".join(sorted(schoolyear.title
                             for schoolyear in self.overlapping_schoolyears)))

    __str__ = __repr__
