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
from zope.component import adapts
from zope.schema import Password, TextLine, Bytes, Bool, getFieldNamesInOrder
from zope.schema import Choice
from zope.schema.interfaces import ValidationError
from zope.app import zapi
from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.app.form.browser.add import AddView
from zope.app.form.browser.editview import EditView
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.publisher.interfaces import NotFound
from zope.app.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.app.security.interfaces import IAuthentication
from zope.app.security.interfaces import IAuthenticatedGroup
from zope.app.security.interfaces import IUnauthenticatedGroup
from zope.app.security.settings import Allow
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.security import checkPermission
from zope.security.interfaces import IParticipation
from zope.security.management import getSecurityPolicy

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import IGroupMember, IPerson, IResource
from schoolbell.app.interfaces import IPersonPreferences, IPersonDetails
from schoolbell.app.interfaces import IPersonContainer, IPersonContained
from schoolbell.app.interfaces import IGroupContainer, IGroupContained
from schoolbell.app.interfaces import IResourceContainer, IResourceContained
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import IApplicationPreferences
from schoolbell.app.interfaces import vocabulary
from schoolbell.app.app import Person
from schoolbell.app.app import getSchoolBellApplication
from schoolbell.app.browser.cal import CalendarOwnerTraverser

from schoolbell.batching import Batch

from pytz import common_timezones


class SchoolBellApplicationTraverser(CalendarOwnerTraverser):
    """Traverser for a SchoolBellApplication."""

    adapts(ISchoolBellApplication)

    def publishTraverse(self, request, name):
        if name in ('persons', 'resources', 'groups'):
            return self.context[name]

        return CalendarOwnerTraverser.publishTraverse(self, request, name)


class ContainerView(BrowserView):
    """A base view for all containers.

    Subclasses must provide the following attributes that are used in the
    page template:

        `index_title` -- Title of the index page.
        `add_title` -- Title for the adding link.
        `add_url` -- URL of the adding link.

    """

    def update(self):
        if 'SEARCH' in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.context.values()
                       if searchstr in item.title.lower()]
        else:
            results = self.context.values()

        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(results, start, size, sort_by='title')


class PersonContainerView(ContainerView):
    """A Person Container view."""

    __used_for__ = IPersonContainer

    index_title = _("Person index")
    add_title = _("Add a new person")
    add_url = "add.html"


class GroupContainerView(ContainerView):
    """A Group Container view."""

    __used_for__ = IGroupContainer

    index_title = _("Group index")
    add_title = _("Add a new group")
    add_url = "+/addSchoolBellGroup.html"


class ResourceContainerView(ContainerView):
    """A Resource Container view."""

    __used_for__ = IResourceContainer

    index_title = _("Resource index")
    add_title = _("Add a new resource")
    add_url = "+/addSchoolBellResource.html"


class ContainerDeleteView(BrowserView):
    """A view for deleting items from container."""

    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)

    def update(self):
        if 'UPDATE_SUBMIT' in self.request:
            for key in self.listIdsForDeletion():
                del self.context[key]
            self.request.response.redirect(self.nextURL())
        elif 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return zapi.absoluteURL(self.context, self.request)


class PersonContainerDeleteView(ContainerDeleteView):
    """A view for deleting users from PersonContainer."""

    def isDeletingHimself(self):
        person = IPerson(self.request.principal, None)
        return person in self.itemsToDelete


class PersonView(BrowserView):
    """A Person info view."""

    __used_for__ = IPersonContained

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.details = IPersonDetails(self.context)


class PersonPhotoView(BrowserView):
    """View that returns photo of a Person."""

    __used_for__ = IPerson

    def __call__(self):
        photo = self.context.photo
        if not photo:
            raise NotFound(self.context, u'photo', self.request)
        self.request.response.setHeader('Content-Type', "image/jpeg")
        return photo


class GroupListView(BrowserView):
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    def getCurrentGroups(self):
        """Return a list of groups the current user is a member of."""
        return self.context.groups

    def getPotentialGroups(self):
        """Return a list of groups the current user is not a member of."""
        groups = ISchoolBellApplication(self.context)['groups']
        return [group for group in groups.values()
                if checkPermission('schoolbell.manageMembership', group)
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

        if 'SEARCH' in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.getPotentialGroups()
                       if searchstr in item.title.lower()]
        else:
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
    """A base view class for adding / removing members from a group.

    Subclasses must override container_name.
    """

    __used_for__ = IGroupContained

    container_name = 'persons'

    def getMembers(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getPotentialMembers(self):
        """Return a list of all possible members."""
        container = ISchoolBellApplication(self.context)[self.container_name]
        return [m for m in container.values() if m not in self.context.members]

    def searchPotentialMembers(self, s):
        potentials = self.getPotentialMembers()
        return [m for m in potentials if s.lower() in m.title.lower()]

    def updateBatch(self, lst):
        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(lst, start, size)

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
        if 'SEARCH' in self.request:
            results = self.searchPotentialMembers(self.request.get('SEARCH'))

        self.updateBatch(results)


class ResourceView(BrowserView):
    """A Resource info view."""

    __used_for__ = IResourceContained


class IPersonEditForm(Interface):
    """Schema for a person's edit form."""

    title = TextLine(
        title=_("Full name"),
        description=_("Name that should be displayed"))

    photo = Bytes(
        title=_("New photo"),
        required=False,
        description=_(
            """A small picture (about 48x48 pixels in JPEG format)"""))

    clear_photo = Bool(
        title=_("Clear photo"),
        required=False,
        description=_("""Check this to clear the photo"""))

    new_password = Password(
        title=_("New password"),
        required=False)

    verify_password = Password(
        title=_("Verify password"),
        required=False)


class PersonEditView(BrowserView):
    """A view for editing a person."""

    __used_for__ = IPersonContained

    error = None
    message = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        setUpWidgets(self, IPersonEditForm, IInputWidget,
                     initial={'title': self.context.title,
                              'photo': self.context.photo})

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

                self.context.setPassword(data['new_password'])
                self.message = _("Password was successfully changed!")

            self.context.title = data['title']
            if data.get('photo'):
                self.context.photo = data['photo']

            if data.get('clear_photo'):
                self.context.photo = None
                # Uncheck the checkbox before rendering the form
                self.clear_photo_widget.setRenderedValue(False)

        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)


class PersonPreferencesView(BrowserView):
    """View used for editing person preferences."""

    __used_for__ = IPersonPreferences

    # TODO: these aren't used yet but should be
    error = None
    message = None

    schema = IPersonPreferences

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        prefs = self.schema(self.context)
        initial = {}
        for field in self.schema:
            initial[field] = getattr(prefs, field)

        setUpWidgets(self, self.schema, IInputWidget, initial=initial)

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        elif 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, self.schema)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            prefs = self.schema(self.context)
            for field in self.schema:
                if field in data: # skip non-fields
                    setattr(prefs, field, data[field])


class PersonDetailsView(BrowserView):
    """View used for editing person preferences."""

    __used_for__ = IPersonDetails

    error = None
    message = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        details = IPersonDetails(self.context)
        initial = {'nickname': details.nickname,
                   'primary_email': details.primary_email,
                   'secondary_email': details.secondary_email,
                   'primary_phone': details.primary_phone,
                   'secondary_phone': details.secondary_phone,
                   'mailing_address': details.mailing_address,
                   'home_page': details.home_page}

        setUpWidgets(self, IPersonDetails, IInputWidget,
                     initial=initial)



    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

        if 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, IPersonDetails)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            details = IPersonDetails(self.context)
            details.nickname = data['nickname']
            details.primary_email = data['primary_email']
            details.secondary_email = data['secondary_email']
            details.primary_phone = data['primary_phone']
            details.secondary_phone = data['secondary_phone']
            details.mailing_address = data['mailing_address']
            details.home_page = data['home_page']


class IPersonAddForm(Interface):
    """Schema for person adding form."""

    title = TextLine(
        title=_("Full name"),
        description=_("Name that should be displayed"))

    username = TextLine(
        title=_("Username"),
        description=_("Username"))

    password = Password(
        title=_("Password"),
        required=False)

    verify_password = Password(
        title=_("Verify password"),
        required=False)

    photo = Bytes(
        title=_("Photo"),
        required=False,
        description=_("""Photo (in JPEG format)"""))


class PersonAddView(AddView):
    """A view for adding a person."""

    __used_for__ = IPersonContainer

    # Form error message for the page template
    error = None

    # Override some fields of AddView
    schema = IPersonAddForm
    _factory = Person
    _arguments = ['title', 'username', 'password', 'photo']
    _keyword_arguments = []
    _set_before_add = [] # getFieldNamesInOrder(schema)
    _set_after_add = []

    def createAndAdd(self, data):
        """Create a Person from form data and add it to the container."""
        if data['password'] != data['verify_password']:
            self.error = _("Passwords do not match!")
            raise WidgetsError([ValidationError(self.error)])
        elif data['username'] in self.context:
            self.error = _('This username is already used!')
            raise WidgetsError([ValidationError(self.error)])
        return AddView.createAndAdd(self, data)

    def getAllGroups(self):
        """Return a list of all groups in the system."""
        return ISchoolBellApplication(self.context)['groups'].values()

    def create(self, title, username, password, photo):
        person = self._factory(username=username, title=title)
        person.setPassword(password)
        person.photo = photo
        return person

    def add(self, person):
        """Add `person` to the container.

        Uses the username of `person` as the object ID (__name__).
        """
        person_groups = removeSecurityProxy(person.groups)
        for group in self.getAllGroups():
            if 'group.' + group.__name__ in self.request:
                person.groups.add(removeSecurityProxy(group))
        name = person.username
        self.context[name] = person
        return person

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

        return AddView.update(self)

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

    __used_for__ = IGroupContained


class ResourceEditView(BaseEditView):
    """A view for editing resource info."""

    __used_for__ = IResourceContained


class LoginView(BrowserView):
    """A login view"""

    error = None

    def __call__(self):
        self.update()
        return self.index()

    def update(self):
        if ('LOGIN' in self.request and 'username' in self.request and
            'password' in self.request):
            auth = zapi.getUtility(IAuthentication)
            try:
                auth.setCredentials(self.request, self.request['username'],
                                    self.request['password'])
            except ValueError:
                self.error = _("Username or password is incorrect")
            else:
                principal = auth.authenticate(self.request)
                person = IPerson(principal, None)
                if 'nexturl' in self.request:
                    nexturl = self.request['nexturl']
                elif person is not None:
                    nexturl = zapi.absoluteURL(person.calendar, self.request)
                else:
                    nexturl = zapi.absoluteURL(self.context, self.request)
                self.request.response.redirect(nexturl)


class LogoutView(BrowserView):
    """Clears the authentication creds from the session"""

    def __call__(self):
        auth = zapi.getUtility(IAuthentication)
        auth.clearCredentials(self.request)
        url = zapi.absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class ACLViewBase(object):
    """A base view for both browser and restive access control views."""

    permissions = [
        ('schoolbell.view', _('View')),
        ('schoolbell.edit', _('Edit')),
        ('schoolbell.create', _('Create new objects')),
        ('schoolbell.viewCalendar', _('View calendar')),
        ('schoolbell.addEvent', _('Add events')),
        ('schoolbell.modifyEvent', _('Modify/delete events')),
        ('schoolbell.controlAccess', _('Control access')),
        ('schoolbell.manageMembership', _('Manage membership')),
        ]

    def getPersons(self):
        app = getSchoolBellApplication()
        map = IPrincipalPermissionManager(self.context)
        auth = zapi.getUtility(IAuthentication)
        result = []
        for person in app['persons'].values():
            pid = auth.person_prefix + person.__name__
            result.append({'title': person.title, 'id': pid,
                           'perms': self.permsForPrincipal(pid)})
        return result
    persons = property(getPersons)

    def permsForPrincipal(self, principalid):
        """Return a list of permissions allowed for principal"""
        return [perm
                for perm, title in self.permissions
                if hasPermission(perm, self.context, principalid)]

    def getGroups(self):
        app = getSchoolBellApplication()
        auth = zapi.getUtility(IAuthentication)
        map = IPrincipalPermissionManager(self.context)
        result = []
        all = zapi.queryUtility(IAuthenticatedGroup)
        if all is not None:
            result.append({'title': _('Authenticated users'),
                           'id': all.id,
                           'perms': self.permsForPrincipal(all.id)})
        unauth = zapi.queryUtility(IUnauthenticatedGroup)
        if unauth is not None:
            result.append({'title': _('Unauthenticated users'),
                           'id': unauth.id,
                           'perms': self.permsForPrincipal(unauth.id)})
        for group in app['groups'].values():
            pid = auth.group_prefix + group.__name__
            result.append({'title': group.title,
                           'id': pid,
                           'perms': self.permsForPrincipal(pid)})
        return result
    groups = property(getGroups)


class ACLView(BrowserView, ACLViewBase):
    """A view for editing SchoolBell-relevant local grants"""

    def update(self):
        if 'UPDATE_SUBMIT' in self.request or 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

        if 'UPDATE_SUBMIT' in self.request:
            map = IPrincipalPermissionManager(self.context)
            # this view is protected by schooltool.controlAccess
            map = removeSecurityProxy(map)

            def permChecked(perm, principalid):
                """Test if a checkbox for (perm, principalid) is checked."""
                if principalid in self.request:
                    return (perm in self.request[principalid] or
                            perm == self.request[principalid])
                return False

            for info in self.persons + self.groups:
                principalid = info['id']
                if 'marker-' + principalid not in self.request:
                    continue # skip this principal
                for perm, permtitle in self.permissions:
                    parent = self.context.__parent__
                    checked_in_request = permChecked(perm, principalid)
                    grant_in_parent = hasPermission(perm, parent, principalid)
                    if checked_in_request and not grant_in_parent:
                        map.grantPermissionToPrincipal(perm, principalid)
                    elif not checked_in_request and grant_in_parent:
                        map.denyPermissionToPrincipal(perm, principalid)
                    else:
                        map.unsetPermissionForPrincipal(perm, principalid)

    def __call__(self):
        self.update()
        return self.index()


class ApplicationPreferencesView(BrowserView):
    """View used for editing application preferences."""

    __used_for__ = IApplicationPreferences

    error = None
    message = None

    schema = IApplicationPreferences

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        app = getSchoolBellApplication()
        prefs = self.schema(app)
        initial = {}
        for field in self.schema:
            initial[field] = getattr(prefs, field)

        setUpWidgets(self, self.schema, IInputWidget, initial=initial)

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        elif 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, self.schema)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            app = getSchoolBellApplication()
            prefs = self.schema(app)
            for field in self.schema:
                if field in data: # skip non-fields
                    setattr(prefs, field, data[field])


class ProbeParticipation:
    """A stub participation for use in hasPermission."""
    implements(IParticipation)
    def __init__(self, principal):
        self.principal = principal
        self.interaction = None


def hasPermission(permission, object, principalid):
    """Test if the principal has access according to the security policy."""
    principal = zapi.getUtility(IAuthentication).getPrincipal(principalid)
    participation = ProbeParticipation(principal)
    interaction = getSecurityPolicy()(participation)
    return interaction.checkPermission(permission, object)
