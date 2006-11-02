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
group views.

$Id$
"""
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.publisher.browser import BrowserView

from schooltool import SchoolToolMessage as _
from schooltool.batching import Batch
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.app import ContainerView, BaseAddView, BaseEditView
from schooltool.person.interfaces import IPerson
from schooltool.resource.interfaces import IResource
from schooltool.course.interfaces import ISection

from schooltool.group.interfaces import IGroupMember, IGroup
from schooltool.group.interfaces import IGroupContainer, IGroupContained
from schooltool.app.browser.app import RelationshipViewBase


class GroupContainerView(ContainerView):
    """A Group Container view."""

    __used_for__ = IGroupContainer

    index_title = _("Group index")
    add_title = _("Add a new group")
    add_url = "+/addSchoolToolGroup.html"


class GroupListView(RelationshipViewBase):
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    @property
    def title(self):
        return _("Groups of ${person}", mapping={'person': self.context.title})
    current_title = _("Current Groups")
    available_title = _("Available Groups")

    def getSelectedItems(self):
        """Return a list of groups the current user is a member of."""
        return self.context.groups

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['groups']

    def getAvailableItems(self):
        """Return a list of groups the current user is not a member of."""
        groups = self.getAvailableItemsContainer()
        return [group for group in groups.values()
                if checkPermission('schooltool.edit', group)
                   and group not in self.context.groups]

    def getCollection(self):
        return self.context.groups


class GroupView(BrowserView):
    """A Group info view."""

    __used_for__ = IGroupContained

    def getPersons(self):
        return filter(IPerson.providedBy, self.context.members)

    def getResources(self):
        return filter(IResource.providedBy, self.context.members)


class MemberViewPersons(RelationshipViewBase):
    """View class for adding / removing members to / from a group."""

    __used_for__ = IGroupContained

    @property
    def title(self):
        return _("Members of ${group}", mapping={'group': self.context.title})
    current_title = _("Current Members")
    available_title = _("Add Members")

    def getSelectedItems(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getAvailableItems(self):
        """Return a list of all possible members."""
        container = self.getAvailableItemsContainer()
        return [m for m in container.values()
                if m not in self.getCollection()]

    def getCollection(self):
        return self.context.members


class GroupAddView(BaseAddView):
    """A view for adding a group."""


class GroupEditView(BaseEditView):
    """A view for editing group info."""

    __used_for__ = IGroupContained


class GroupsViewlet(BrowserView):
    """A viewlet showing the groups a person is in."""

    def memberOf(self):
        """Seperate out generic groups from sections."""
        return [group for group in self.context.groups if
                IGroup.providedBy(group)]
