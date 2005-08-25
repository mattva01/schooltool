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

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.app.publisher.browser import BrowserView

from schooltool import SchoolToolMessageID as _
from schooltool.batching import Batch
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.browser.app import ContainerView, BaseAddView, BaseEditView
from schooltool.person.interfaces import IPerson
from schooltool.resource.interfaces import IResource

from schooltool.group.interfaces import IGroupMember
from schooltool.group.interfaces import IGroupContainer, IGroupContained


class GroupContainerView(ContainerView):
    """A Group Container view."""

    __used_for__ = IGroupContainer

    index_title = _("Group index")
    add_title = _("Add a new group")
    add_url = "+/addSchoolToolGroup.html"


class GroupListView(BrowserView):
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    def getCurrentGroups(self):
        """Return a list of groups the current user is a member of."""
        return self.context.groups

    def getPotentialGroups(self):
        """Return a list of groups the current user is not a member of."""
        groups = getSchoolToolApplication()['groups']
        return [group for group in groups.values()
                if checkPermission('schooltool.manageMembership', group)
                and group not in self.context.groups]

    def update(self):
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'ADD_GROUPS' in self.request:
            context_groups = removeSecurityProxy(self.context.groups)
            for group in self.getPotentialGroups():
                # add() could throw an exception, but at the moment the
                # constraints are never violated, so we ignore the problem.
                if 'add_group.' + group.__name__ in self.request:
                    group = removeSecurityProxy(group)
                    context_groups.add(group)
        elif 'REMOVE_GROUPS' in self.request:
            context_groups = removeSecurityProxy(self.context.groups)
            for group in self.getCurrentGroups():
                # add() could throw an exception, but at the moment the
                # constraints are never violated, so we ignore the problem.
                if 'remove_group.' + group.__name__ in self.request:
                    group = removeSecurityProxy(group)
                    context_groups.remove(group)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)

        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.getPotentialGroups()
                       if searchstr in item.title.lower()]
        else:
            self.request.form['SEARCH'] = ''
            results = self.getPotentialGroups()

        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(results, start, size, sort_by='title')


class GroupView(BrowserView):
    """A Group info view."""

    __used_for__ = IGroupContained

    def getPersons(self):
        return filter(IPerson.providedBy, self.context.members)

    def getResources(self):
        return filter(IResource.providedBy, self.context.members)


class MemberViewPersons(BrowserView):
    """View class for adding / removing members to / from a group."""

    __used_for__ = IGroupContained

    def getMembers(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getPotentialMembers(self):
        """Return a list of all possible members."""
        container = getSchoolToolApplication()['persons']
        return [m for m in container.values() if m not in self.context.members]

    def searchPotentialMembers(self, s):
        """Return a list of possible members with a `s` in their title."""
        potentials = self.getPotentialMembers()
        return [m for m in potentials if s.lower() in m.title.lower()]

    def updateBatch(self, lst):
        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(lst, start, size, sort_by='title')

    def update(self):
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'DONE' in self.request:
            self.request.response.redirect(context_url)
        elif 'ADD_MEMBERS' in self.request:
            context_members = removeSecurityProxy(self.context.members)
            for member in self.getPotentialMembers():
                # add() could throw an exception, but at the moment the
                # constraints are never violated, so we ignore the problem.
                if 'ADD_MEMBER.' + member.__name__ in self.request:
                    member = removeSecurityProxy(member)
                    context_members.add(member)
        elif 'REMOVE_MEMBERS' in self.request:
            context_members = removeSecurityProxy(self.context.members)
            for member in self.getMembers():
                # remove() could throw an exception, but at the moment the
                # constraints are never violated, so we ignore the problem.
                if 'REMOVE_MEMBER.' + member.__name__ in self.request:
                    member = removeSecurityProxy(member)
                    context_members.remove(member)

        results = self.getPotentialMembers()
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            results = self.searchPotentialMembers(self.request.get('SEARCH'))
        else:
            self.request.form['SEARCH'] = ''

        self.updateBatch(results)


class GroupAddView(BaseAddView):
    """A view for adding a group."""


class GroupEditView(BaseEditView):
    """A view for editing group info."""

    __used_for__ = IGroupContained


