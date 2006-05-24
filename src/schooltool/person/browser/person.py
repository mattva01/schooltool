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
Person browser views.

$Id$
"""
from zope.interface import Interface
from zope.publisher.interfaces import NotFound
from zope.schema import Password, TextLine, Bytes, Bool
from zope.schema.interfaces import ValidationError
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.publisher.browser import BrowserView
from zope.viewlet.interfaces import IViewletManager
from zope.formlib import form
from zope.component import getUtility

from schooltool import SchoolToolMessage as _
from schooltool.skin.form import BasicForm
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.browser.app import ContainerView, ContainerDeleteView
from schooltool.person.interfaces import IPerson, IPersonFactory
from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.interfaces import IPersonContainer, IPersonContained
from schooltool.person.person import Person
from schooltool.widget.password import PasswordConfirmationWidget

class PersonContainerView(ContainerView):
    """A Person Container view."""

    __used_for__ = IPersonContainer

    index_title = _("Person index")
    add_title = _("Add a new person")
    add_url = "add.html"


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

class PersonPhotoView(BrowserView):
    """View that returns photo of a Person."""

    __used_for__ = IPerson

    def __call__(self):
        photo = self.context.photo
        if not photo:
            raise NotFound(self.context, u'photo', self.request)
        self.request.response.setHeader('Content-Type', "image/jpeg")
        return photo


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
        return getSchoolToolApplication()['groups'].values()

    def create(self, title, username, password, photo):
        person = self._factory(username=username, title=title)
        person.setPassword(password)
        person.photo = photo
        return person

    def _factory(self, username, title):
        return getUtility(IPersonFactory)(username, title)
        
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

class IPasswordEditForm(Interface):
    """Schema for a person's edit form."""

    password = Password(
        title=_("Password"),
        required=False)
    
class PersonPasswordEditView(BasicForm):
    form_fields = form.Fields(IPasswordEditForm, render_context=False)
    form_fields['password'].custom_widget = PasswordConfirmationWidget
    
    def title(self):
        return _("Edit password")

    @form.action(_("Apply"))
    def handle_edit_action(self, action, data):
        if not data['password']:
            self.status = _("No new password was supplied so "
                            "original password is unchanged")
            return
        self.context.setPassword(data['password'])
        self.status = _('Changed password')

    @form.action(_("Cancel"))
    def handle_cancel_action(self, action, data):
        # redirect to parent
        url = zapi.absoluteURL(self.context, self.request)
        self.request.response.redirect(url)
        return ''

class IPersonInfoManager(IViewletManager):
    """Provides a viewlet hook for the information on a Person's page."""
