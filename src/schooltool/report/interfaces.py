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
Email interfaces

"""

from zope.container.constraints import contains, containers
from zope.location.interfaces import IContained
from zope.container.interfaces import IReadContainer, IWriteContainer
from zope.interface import Interface
from zope.location.interfaces import ILocation
from zope.schema import Bool, Datetime, Dict
from zope.schema import TextLine, List, Text, Int, Password

from schooltool.common import SchoolToolMessage as _


class IReportRequest(Interface):
    """An adapter to register report requests"""

    title = TextLine(
        title=u"Title",
        required=True,
        )

    url = TextLine(
        title=u"URL",
        required=True,
        )


class IReportReference(Interface):
    """An adapter to register report references"""

    title = TextLine(
        title=u"Title",
        required=True,
        )

    description = TextLine(
        title=u"Description",
        required=True,
        )

    category = TextLine(
        title=u"Category",
        required=True,
        )

    category_key = TextLine(
        title=u"Category key",
        required=True,
        )

    url = TextLine(
        title=u"URL",
        required=True,
        )

