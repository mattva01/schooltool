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
from zope.publisher.interfaces import NotFound
from schoolbell import SchoolBellMessageID as _
from schoolbell.app.browser.skin import ISchoolBellSkin

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


class PersonView(object):
    """A Person info view."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def canEdit(self):
        #XXX Not implemented
        return True

    def canChangePassword(self):
        #XXX Not implemented
        return True

    canViewCalendar = canChangePassword
    canChooseCalendars = canChangePassword

    def timetables(self, empty=False):
        """Return a sorted list of all composite timetables on self.context.

        If `empty` is True, also includes empty timetables in the output.

        The list contains dicts with 'title', 'url' and 'empty' in them.
        """
        #XXX Not implemented
        pass

class PersonPhotoView(object):
    """View that returns photo of a Person."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        photo = self.context.photo
        if not photo:
            raise NotFound(self.context, u'photo', self.request)
        self.request.response.setHeader('Content-Type', "image/jpeg")
        return photo
