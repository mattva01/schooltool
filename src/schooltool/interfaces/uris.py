#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
SchoolTool interfaces for URI-related objects.

$Id$
"""

from zope.interface import Interface
from zope.schema import TextLine, Text
from schooltool.interfaces.fields import URIField


#
# URIs
#

class IURIObject(Interface):
    """An opaque identifier of a role or a relationship type.

    Roles and relationships are identified by URIs in XML representation.
    URI objects let the application assign human-readable names to roles
    and relationship types.

    URI objects are equal iff their uri attributes are equal.
    """

    uri = URIField(
        title=u"URI (as a string).")

    name = TextLine(
        title=u"Human-readable name.")

    description = Text(
        title=u"Human-readable description.")


class IURIAPI(Interface):
    """Helper functions for handling URIs.

    URI objects are named utilities implementing the IURIObject
    interface.  The utility names are URI strings.
    """

    def registerURI(uri):
        """Register a URIObject as a named utility"""
