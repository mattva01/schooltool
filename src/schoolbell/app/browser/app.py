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

from zope.interface import Interface
from zope.schema import Password, getFieldNamesInOrder
from zope.app import zapi
from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget, WidgetsError
from zope.publisher.interfaces import NotFound
from zope.app.publisher.browser import BrowserView
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import IGroupMember, IGroupContained


class ContainerView(BrowserView):
    """A base view for all containers.

    Subclasses must provide the following attributes that are used in the
    page template:

        `index_title` -- Title of the index page.
        `add_title` -- Title for the adding link.
        `add_url` -- URL of the adding link.

    """

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


class PersonView(BrowserView):
    """A Person info view."""

    def canEdit(self):
        return True # TODO: implement permission checking

    canChangePassword = canEdit # TODO: implement permission checking
    canViewCalendar = canEdit # TODO: implement permission checking
    canChooseCalendars = canEdit # TODO: implement permission checking


class PersonPhotoView(BrowserView):
    """View that returns photo of a Person."""

    def __call__(self):
        photo = self.context.photo
        if not photo:
            raise NotFound(self.context, u'photo', self.request)
        self.request.response.setHeader('Content-Type', "image/jpeg")
        return photo


class GroupListView(BrowserView):
    """View for adding / removing parent groups."""

    __used_for__ = IGroupMember

    def getGroupList(self):
        """Return a sorted list of all groups in the system."""
        groups = self.context.__parent__.__parent__['groups'] # XXX Ugly.
        items = [(group.title, group) for group in groups.values()]
        items.sort()
        return [row[-1] for row in items]

    def update(self):
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'APPLY' in self.request:
            context_groups = removeSecurityProxy(self.context.groups)
            for group in self.getGroupList():
                want = bool('group.' + group.__name__ in self.request)
                have = bool(group in context_groups)
                # add() and remove() could throw an exception, but at the
                # moment the constraints are never violated, so we ignore
                # the problem.
                if want != have:
                    group = removeSecurityProxy(group)
                    if want:
                        context_groups.add(group)
                    else:
                        context_groups.remove(group)
            self.request.response.redirect(context_url)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)


class GroupView(BrowserView):
    """A Group info view."""

    __used_for__ = IGroupContained

    def canEdit(self):
        return True # TODO: implement permission checking


class MemberViewBase(BrowserView):
    """A base view class for adding / removing members from a group.

    Subclasses must override container_name.
    """

    __used_for__ = IGroupContained

    container_name = None

    def getMemberList(self):
        """Return a sorted list of all possible members."""
        # XXX Ugly.  Maybe we could use adaptation here.
        member = self.context.__parent__.__parent__[self.container_name]
        items = [(member.title, member) for member in member.values()]
        items.sort()
        return [row[-1] for row in items]

    def update(self):
        # XXX This method is rather similar to GroupListView.update().
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'APPLY' in self.request:
            context_members = removeSecurityProxy(self.context.members)
            for member in self.getMemberList():
                want = bool('member.' + member.__name__ in self.request)
                have = bool(member in context_members)
                # add() and remove() could throw an exception, but at the
                # moment the constraints are never violated, so we ignore
                # the problem.
                if want != have:
                    member = removeSecurityProxy(member)
                    if want:
                        context_members.add(member)
                    else:
                        context_members.remove(member)
            self.request.response.redirect(context_url)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)


class MemberViewPersons(MemberViewBase):
    """A view for adding / removing group members that are persons."""

    container_name = 'persons'


class MemberViewResources(MemberViewBase):
    """A view for adding / removing group members that are resources."""

    container_name = 'resources'


class ResourceView(BrowserView):
    """A Resource info view."""

    def canEdit(self):
        return True # TODO: implement permission checking

    def getParentGroups(self):
        pass


class IPasswordChangeForm(Interface):
    """Schema for a password change form."""

    old_password = Password(title=u"Old password")
    new_password = Password(title=u"New password")
    verify_password = Password(title=u"Verify password")


class PersonChangePasswordView(BrowserView):
    """A view for changing password."""

    error = None
    message = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.fieldNames = ['new_password', 'verify_password']

        if not self.isZopeManager():
            self.fieldNames = ['old_password'] + self.fieldNames

        setUpWidgets(self, IPasswordChangeForm, IInputWidget,
                     names=self.fieldNames)

    def isZopeManager(self):
        return checkPermission("zope.ManageContent", self.context)

    def widgets(self):
        return [getattr(self, name + '_widget') for name in self.fieldNames]

    def update(self):
        if 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, IPasswordChangeForm,
                                      names=self.fieldNames)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            if data['new_password'] != data['verify_password']:
                self.error = _("Passwords do not match.")
                return

            if (not self.isZopeManager() and
                not self.context.checkPassword(data['old_password'])):
                self.error = _("Wrong password!")
                return

            self.context.setPassword(data['new_password'])
            self.message = _("Password was successfully changed!")

        if 'UPDATE_DISABLE' in self.request:
            if not self.isZopeManager():
                self.error = _("You are not a manager!")
                return

            self.context.setPassword(None)
