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

$Id: app.py 4627 2005-08-09 14:45:22Z srichter $
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
from zope.app.publisher.browser import BrowserView

from schooltool import SchoolToolMessageID as _
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.browser.app import ContainerView, ContainerDeleteView
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonPreferences, IPersonDetails
from schooltool.person.interfaces import IPersonContainer, IPersonContained

from schooltool.person.person import Person

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
        self.details = IPersonDetails(self.context)

    def isTeacher(self):

        if len(getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)) > 0:
            return True
        else:
            return False

    def isLearner(self):
        for obj in self.context.groups:
            if ISection.providedBy(obj):
                return True

        return False

    def instructorOf(self):
        return getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)

    def memberOf(self):
        """Seperate out generic groups from sections."""

        return [group for group in self.context.groups if not
                ISection.providedBy(group)]

    def learnerOf(self):
        results = []
        sections = getSchoolToolApplication()['sections'].values()
        for section in sections:
            if self.context in section.members:
                results.append({'section': section, 'group': None})
            # XXX isTransitiveMember works in the test fixture but not in the
            # application, working around it for the time being.
            for group in self.memberOf():
                if group in section.members:
                    results.append({'section': section,
                                    'group': group})

        return results


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
        return getSchoolToolApplication()['groups'].values()

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
