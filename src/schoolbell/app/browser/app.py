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
from schoolbell.app.interfaces import IPersonPreferences
from schoolbell.app.interfaces import IPersonContainer, IPersonContained
from schoolbell.app.interfaces import IGroupContainer, IGroupContained
from schoolbell.app.interfaces import IResourceContainer, IResourceContained
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.app import Person
from schoolbell.app.app import getSchoolBellApplication

from pytz import common_timezones

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


class PersonView(BrowserView):
    """A Person info view."""

    __used_for__ = IPersonContained


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

    def getAllGroups(self):
        """Return a list of groups the current user can add to"""
        groups = ISchoolBellApplication(self.context)['groups']
        return [group for group in groups.values()
                if checkPermission('schoolbell.manageMembership', group)]

    def update(self):
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'UPDATE_SUBMIT' in self.request:
            context_groups = removeSecurityProxy(self.context.groups)
            for group in self.getAllGroups():
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

    def getPotentialMembers(self):
        """Return a list of all possible members."""
        container = ISchoolBellApplication(self.context)[self.container_name]
        return container.values()

    def update(self):
        # This method is rather similar to GroupListView.update().
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'UPDATE_SUBMIT' in self.request:
            context_members = removeSecurityProxy(self.context.members)
            for member in self.getPotentialMembers():
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

    __used_for__ = IResourceContained


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


class IPersonPreferencesForm(Interface):

    timezone = Choice(title=u"Time Zone",
                    description=u"Time Zone used to display your calendar",
                    values=common_timezones)

    timeformat = Choice(title=u"Time Format",
                    description=u"Time Format",
                    values=("HH:MM", "H:MM am/pm"))

    dateformat = Choice(title=u"Date Format",
                    description=u"Date Format",
                    values=("MM/DD/YY", "YYYY-DD-MM", "Day Month, Year"))

    weekstart = Choice(title=u"Week starts on:",
                    description=u"Start display of weeks on Sunday or Monday",
                    values=("Sunday", "Monday"))


class PersonPreferencesView(BrowserView):
    """View used for editing person preferences."""

    __used_for__ = IPersonPreferences

    # TODO: these aren't used yet but should be
    error = None
    message = None

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        prefs = IPersonPreferences(self.context)
        initial = {'timezone': prefs.timezone,
                   'timeformat': prefs.timeformat,
                   'dateformat': prefs.dateformat,
                   'weekstart': prefs.weekstart}

        setUpWidgets(self, IPersonPreferencesForm, IInputWidget,
                     initial=initial)

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

        if 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, IPersonPreferencesForm)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            prefs = IPersonPreferences(self.context)
            prefs.timezone = data['timezone']
            prefs.timeformat = data['timeformat']
            prefs.dateformat = data['dateformat']
            prefs.weekstart = data['weekstart']


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
            self.error = u'Passwords do not match!'
            raise WidgetsError([ValidationError('Passwords do not match!')])
        elif data['username'] in self.context:
            self.error = u'This username is already used!'
            raise WidgetsError(
                [ValidationError('This username is already used!')])
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


class ACLView(BrowserView):
    """A view for editing SchoolBell-relevant local grants"""

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

    def persons(self):
        app = getSchoolBellApplication()
        map = IPrincipalPermissionManager(self.context)
        auth = zapi.getUtility(IAuthentication)
        result = []
        for person in app['persons'].values():
            pid = auth.person_prefix + person.__name__
            result.append({'title': person.title, 'id': pid,
                           'perms': self.permsForPrincipal(pid)})
        return result
    persons = property(persons)

    def permsForPrincipal(self, principalid):
        """Return a list of permissions allowed for principal"""
        return [perm
                for perm, title in self.permissions
                if hasPermission(perm, self.context, principalid)]

    def groups(self):
        app = getSchoolBellApplication()
        auth = zapi.getUtility(IAuthentication)
        map = IPrincipalPermissionManager(self.context)
        result = []
        all = zapi.queryUtility(IAuthenticatedGroup)
        if all is not None:
            result.append({'title': 'Authenticated users', 'id': all.id,
                           'perms': self.permsForPrincipal(all.id)})
        unauth = zapi.queryUtility(IUnauthenticatedGroup)
        if unauth is not None:
            result.append({'title': 'Unauthenticated users', 'id': unauth.id,
                           'perms': self.permsForPrincipal(unauth.id)})
        for group in app['groups'].values():
            pid = auth.group_prefix + group.__name__
            result.append({'title': group.title,
                           'id': pid,
                           'perms': self.permsForPrincipal(pid)})
        return result
    groups = property(groups)

    def update(self):
        if 'UPDATE_SUBMIT' in self.request or 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

        if 'UPDATE_SUBMIT' in self.request:
            map = IPrincipalPermissionManager(self.context)
            # this view is protected by schooltool.controlAccess
            map = removeSecurityProxy(map)
            auth = zapi.getUtility(IAuthentication)

            def permChecked(perm, principalid):
                """Returns if a checkbox for (perm, principalid) is checked"""
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


class ProbeParticipation:
    """A stub participation for use in hasPermission"""
    implements(IParticipation)
    def __init__(self, principal):
        self.principal = principal
        self.interaction = None


def hasPermission(permission, object, principalid):
    """Returns if the principal has access according to the security policy"""

    principal = zapi.getUtility(IAuthentication).getPrincipal(principalid)
    participation = ProbeParticipation(principal)
    interaction = getSecurityPolicy()(participation)
    return interaction.checkPermission(permission, object)
