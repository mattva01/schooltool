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
SchoolBell application views.

$Id$
"""

from schoolbell import SchoolBellMessageID as _


class ContainerView(object):
    """A base view for all containers.

    Subclasses must provide the follwing attributes:

        `index_title` -- Title of the index page.
        `add_title` -- Title for the adding link.
        `add_url` -- URL of the adding link.

    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sortedObjects(self):
        """Return a list of contained objects sorted by title."""
        objs = [(o.title, o) for o in self.context.values()]
        objs.sort()
        return [o for title, o in objs]


class PersonContainerView(ContainerView):
    """A Person Container view."""

    index_title = _("Person index")
    add_title = _("Add a new person")
    add_url = "addSchoolBellPerson.html"


class GroupContainerView(ContainerView):
    """A Group Container view."""

    index_title = _("Group index")
    add_title = _("Add a new group")
    add_url = "addSchoolBellGroup.html"


class ResourceContainerView(ContainerView):
    """A Resource Container view."""

    index_title = _("Resource index")
    add_title = _("Add a new resource")
    add_url = "addSchoolBellResource.html"
