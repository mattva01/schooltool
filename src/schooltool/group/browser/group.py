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
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.browser.app import ContainerView, BaseAddView, BaseEditView
from schooltool.person.interfaces import IPerson
from schooltool.resource.interfaces import IResource
from schooltool.course.interfaces import ISection

from schooltool.group.interfaces import IGroupMember
from schooltool.group.interfaces import IGroupContainer, IGroupContained


class GroupContainerView(ContainerView):
    """A Group Container view."""

    __used_for__ = IGroupContainer

    index_title = _("Group index")
    add_title = _("Add a new group")
    add_url = "+/addSchoolToolGroup.html"


class RelationshipViewBase(BrowserView):
    """A base class for views that add/remove members from a relationship."""

    def add(self, item):
        """Add an item to the list of selected items."""
        # Only those who can edit this section will see the view so it
        # is safe to remove the security proxy here
        collection = removeSecurityProxy(self.getCollection())
        collection.add(item)

    def remove(self, item):
        """Remove an item from selected items."""
        # Only those who can edit this section will see the view so it
        # is safe to remove the security proxy here
        collection = removeSecurityProxy(self.getCollection())
        collection.remove(item)

    def getCollection(self):
        """Return the backend storage for related objects."""
        raise NotImplementedError("Subclasses should override this method.")

    def getSelectedItems(self):
        """Return a sequence of items that are already selected."""
        return self.getCollection()

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        raise NotImplementedError("Subclasses should override this method.")

    def updateBatch(self, lst):
        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(lst, start, size, sort_by='title')

    def update(self):
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'ADD_ITEMS' in self.request:
            for item in self.getAvailableItems():
                if 'add_item.' + item.__name__ in self.request:
                    self.add(removeSecurityProxy(item))
        elif 'REMOVE_ITEMS' in self.request:
            for item in self.getSelectedItems():
                if 'remove_item.' + item.__name__ in self.request:
                    self.remove(removeSecurityProxy(item))
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)

        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.getAvailableItems()
                       if searchstr in item.title.lower()]
        else:
            self.request.form['SEARCH'] = ''
            results = self.getAvailableItems()

        self.updateBatch(results)


class GroupListView(RelationshipViewBase):
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    def getSelectedItems(self):
        """Return a list of groups the current user is a member of."""
        return self.context.groups

    def getAvailableItems(self):
        """Return a list of groups the current user is not a member of."""
        groups = getSchoolToolApplication()['groups']
        return [group for group in groups.values()
                if checkPermission('schooltool.manageMembership', group)
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

    def getSelectedItems(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getAvailableItems(self):
        """Return a list of all possible members."""
        container = getSchoolToolApplication()['persons']
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
        return [group for group in self.context.groups if not
                ISection.providedBy(group)]
