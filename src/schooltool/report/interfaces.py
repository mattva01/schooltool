#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Report interfaces

"""

from zope.container.constraints import contains, containers
from zope.location.interfaces import IContained
from zope.container.interfaces import IReadContainer, IWriteContainer
from zope.interface import Interface
from zope.location.interfaces import ILocation
from zope.schema import Bool, Datetime, Dict
from zope.schema import TextLine, List, Text, Int, Password
from zope.viewlet.interfaces import IViewletManager

from schooltool.common import SchoolToolMessage as _


class IReportLinkViewletManager(IViewletManager):
   """The manager for report links."""


class IRegisteredReportsUtility(Interface):

    reports_by_group = Dict(
        title=u"Reports by group",
        description=u"Maps report group names to lists of report descriptions")


class IReportLinksURL(Interface):

    def actualContext():
        """Returns the actual object the report links are for."""

    def __unicode__():
        """Returns the URL as a unicode string."""

    def __str__():
        """Returns an ASCII string with all unicode characters url quoted."""

    def __repr__():
        """Get a string representation """

    def __call__():
        """Returns an ASCII string with all unicode characters url quoted."""

