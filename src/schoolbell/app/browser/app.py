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

from zope.interface import Interface, implements
from zope.schema import Password, TextLine, Bytes, Bool, getFieldNamesInOrder
from zope.schema.interfaces import ValidationError
from zope.app import zapi
from zope.app.form.utility import getWidgetsData, setUpEditWidgets
from zope.app.form.browser.add import AddView
from zope.app.form.browser.editview import EditView
from zope.app.form.interfaces import WidgetsError
from zope.publisher.interfaces import NotFound
from zope.app.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.component import adapts

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import IGroupMember, IGroupContained
from schoolbell.app.interfaces import IPerson, IResource, IPersonContainer
from schoolbell.app.app import Person


def sorted_by_title(objects):
    """Sort a list of objects by title.

    The objects must have a title attribute.

    XXX This can go away now that we can say list/sortby:title in TALES
    """
    objs = [(o.title, o) for o in objects]
    objs.sort()
    return [o for (title, o) in objs]


class ContainerView(BrowserView):
    """A base view for all containers.

    Subclasses must provide the following attributes that are used in the
    page template:

        `index_title` -- Title of the index page.
        `add_title` -- Title for the adding link.
        `add_url` -- URL of the adding link.

    """


class PersonContainerView(ContainerView):
    """A Person Container view."""

    index_title = _("Person index")
    add_title = _("Add a new person")
    add_url = "add.html"


class GroupContainerView(ContainerView):
    """A Group Container view."""

    index_title = _("Group index")
    add_title = _("Add a new group")
    add_url = "+/addSchoolBellGroup.html"


class ResourceContainerView(ContainerView):
    """A Resource Container view."""

    index_title = _("Resource index")
    add_title = _("Add a new resource")
    add_url = "+/addSchoolBellResource.html"


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
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    def getGroupList(self):
        """Return a sorted list of all groups in the system."""
        groups = self.context.__parent__.__parent__['groups'] # XXX ugly
        return groups.values()

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

    def getPersons(self):
        return filter(IPerson.providedBy, self.context.members)

    def getResources(self):
        return filter(IResource.providedBy, self.context.members)


class MemberViewBase(BrowserView):
    """A base view class for adding / removing members from a group.

    Subclasses must override container_name.
    """

    __used_for__ = IGroupContained

    container_name = None

    def getMemberList(self):
        """Return a sorted list of all possible members."""
        # XXX Ugly.  Maybe we could use adaptation here.
        container = self.context.__parent__.__parent__[self.container_name]
        return sorted_by_title(container.values())

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


class IPersonEditForm(Interface):
    """Schema for a person's edit form."""

    title = TextLine(title=u"Full name",
                     description=u"Name that should be displayed")

    photo = Bytes(title=u"New photo",
                  required=False,
                  description=u"""Photo (in JPEG format)""")

    clear_photo = Bool(title=u'Clear photo',
                       required=False,
                       description=u"""Check this to clear the photo""")

    new_password = Password(title=u"New password",
                            required=False)

    verify_password = Password(title=u"Verify password",
                               required=False)


class PersonEditView(BrowserView):
    """A view for editing a person."""

    error = None
    message = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        setUpEditWidgets(self, IPersonEditForm, self.context)

    def update(self):
        if 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, IPersonEditForm)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            # If any of the password fields is set
            if data.get('new_password') or data.get('verify_password'):
                # We compare them
                if data['new_password'] != data['verify_password']:
                    self.error = _("Passwords do not match.")
                    return

                # XXX When we have security in place, this place needs an audit
                self.context.setPassword(data['new_password'])
                self.message = _("Password was successfully changed!")

            self.context.title = data['title']
            if data.get('photo'):
                self.context.photo = data['photo']

            if data.get('clear_photo'):
                self.context.photo = None
                # Uncheck the checkbox before rendering the form
                self.clear_photo_widget.setRenderedValue(False)


class IPersonAddForm(Interface):
    """Schema for person adding form."""

    title = TextLine(title=u"Full name",
        description=u"Name that should be displayed")

    username = TextLine(title=u"Username",
        description=u"Username")

    password = Password(title=u"Password",
        required=False)

    verify_password = Password(title=u"Verify password",
        required=False)

    photo = Bytes(title=u"Photo",
        required=False,
        description=u"""Photo (in JPEG format)""")


marker = object()


class PersonAddAdapter(object):
    """An adapter for the person add form.

    We want to reuse a Zope 3 adding form, but we want to use a slightly
    different schema (IPersonAddForm instead of IPerson), because IPerson
    lacks certain fields (namely `password` and `confirm_password`).  Because
    Zope's AddView adapts the created object to the schema in `createAndAdd`,
    we need this adapter.
    """

    adapts(IPerson)
    implements(IPersonAddForm)

    _password = marker

    def __init__(self, context):
        self.context = context

    def setPassword(self, password):
        # XXX I'd say this is a bit evil, but it will do for now.
        if self._password is marker:
            self._password = password
        elif self._password == password:
            self.context.setPassword(password)
        else:
            raise ValueError("passwords do not match")

    password = property(None, setPassword)
    verify_password = property(None, setPassword)

    def setTitle(self, title):
        self.context.title = title

    title = property(None, setTitle)

    def setUsername(self, username):
        self.context.username = username

    username = property(None, setUsername)

    def setPhoto(self, photo):
        self.context.photo = photo

    photo = property(None, setPhoto)


class PersonAddView(AddView):
    """A view for adding a person."""

    __used_for__ = IPersonContainer

    # Form error message for the page template
    error = None

    # Override some fields of AddView
    schema = IPersonAddForm
    _factory = Person
    _arguments = ()
    _keyword_arguments = ()
    _set_before_add = getFieldNamesInOrder(schema)
    _set_after_add = ()

    def createAndAdd(self, data):
        """Create a Person from form data and add it to the container."""
        if data['password'] != data['verify_password']:
            self.error = u'Passwords do not match!'
            raise WidgetsError([ValidationError('Passwords do not match!')])
        elif data['username'] in self.context:
            self.error = u'This username is already used!'
            raise WidgetsError(
                [ValidationError('This username is already used!')])
        return AddView.createAndAdd(self, data)

    def getGroupList(self):
        """Return a sorted list of all groups in the system."""
        groups = self.context.__parent__['groups']
        return sorted_by_title(groups.values())

    def add(self, person):
        """Add `person` to the container.

        Uses the username of `person` as the object ID (__name__).
        """
        person_groups = removeSecurityProxy(person.groups)
        for group in self.getGroupList():
            if 'group.' + group.__name__ in self.request:
                person.groups.add(removeSecurityProxy(group))
        name = person.username
        self.context[name] = person
        return person

    def nextURL(self):
        """See zope.app.container.interfaces.IAdding"""
        return zapi.absoluteURL(self.context, self.request)


class BaseAddView(AddView):
    """Common functionality for adding groups and resources"""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class GroupAddView(BaseAddView):
    """A view for adding a group."""


class ResourceAddView(BaseAddView):
    """A view for adding a resource."""


class BaseEditView(EditView):
    """An edit view for resources and groups"""

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        else:
            status = EditView.update(self)
            if 'UPDATE_SUBMIT' in self.request and not self.errors:
                url = zapi.absoluteURL(self.context, self.request)
                self.request.response.redirect(url)
            return status


class GroupEditView(BaseEditView):
    """A view for editing group info."""


class ResourceEditView(BaseEditView):
    """A view for editing resource info."""

