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
SchoolTool interfaces for a part of the component architecture.

$Id$
"""

from zope.interface import Interface
from zope.app.location.interfaces import ILocation
from zope.schema import TextLine


class IUtility(ILocation):
    """Utilities do stuff. They are managed by the utility service."""

    title = TextLine(
        title=u"Short descriptive text")


class IUtilityService(ILocation):
    """The utility service manages utilities."""

    def __getitem__(name):
        """Return the named utility."""

    def __setitem__(name, utility):
        """Add a new utility.

        The utility must provide IUtility, and will have the utility service
        set as its __parent__, and the name as its __name__.
        """

    def values():
        """Return a list of utilities."""


class IViewAPI(Interface):
    """View registry.

    The view registry is only used for RESTive views, and is not used very
    extensively.  Whenever an view's _traverse method does not know the
    type of the object it traverses to, it uses getView to select an
    appropriate view.  For example, this is the case for application object
    container views.
    """

    def getView(object):
        """Select a view for an object by its class or its interface.

        Views registered for a class take precedence.

        Returns a View object for obj.
        """

    def registerView(interface, factory):
        """Register a view for an interface."""

    def registerViewForClass(cls, factory):
        """Register a view for a content class."""
