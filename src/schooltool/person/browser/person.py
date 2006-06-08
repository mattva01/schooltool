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
from zope.schema import Password, TextLine, Bytes, Bool, List, Choice
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import IIterableSource
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.app.form.browser.source import SourceMultiCheckBoxWidget as SourceMultiCheckBoxWidget_
from zope.app.form.browser.interfaces import ITerms
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.publisher.browser import BrowserView
from zope.viewlet.interfaces import IViewletManager
from zope.formlib import form
from zope.component import getUtility
from zope.interface import implements
from zope.app.pagetemplate import ViewPageTemplateFile
from schooltool import SchoolToolMessage as _
from schooltool.skin.form import BasicForm
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.browser.app import ContainerView, ContainerDeleteView
from schooltool.person.interfaces import IPerson, IPersonFactory
from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.interfaces import IPersonContainer, IPersonContained
from schooltool.person.person import Person
from schooltool.widget.password import PasswordConfirmationWidget
from schooltool.traverser.traverser import AdapterTraverserPlugin

def SourceMultiCheckBoxWidget(field, request):
    source = field.value_type.source
    return SourceMultiCheckBoxWidget_(field, source, request)


class PersonContainerDeleteView(ContainerDeleteView):
    """A view for deleting users from PersonContainer."""

    def isDeletingHimself(self):
        person = IPerson(self.request.principal, None)
        return person in self.itemsToDelete

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
        self.person = self.context.__parent__
        initial = {}
        for field in self.schema:
            initial[field] = getattr(context, field)
        setUpWidgets(self, self.schema, IInputWidget, initial=initial)

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.person, self.request)
            self.request.response.redirect(url)
        elif 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, self.schema)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            for field in self.schema:
                if field in data: # skip non-fields
                    setattr(self.context, field, data[field])


PreferencesTraverserPlugin = AdapterTraverserPlugin(
    'preferences', IPersonPreferences)


# Should this be moved to a interface.py file ?
class IGroupsSource(IIterableSource):
    pass

class GroupsSource(object):
    implements(IGroupsSource)

    def __iter__(self):
        return iter(getSchoolToolApplication()['groups'].values())

    def __len__(self):
        return len(getSchoolToolApplication()['groups'].values())

class GroupsTerm(object):
    implements(ITitledTokenizedTerm)

    def __init__(self, title, token, value):
        self.title = title
        self.token = token
        self.value = value

class GroupsTerms(object):
    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getTerm(self, value):
        return GroupsTerm(value.title, value.__name__, value)

    def getValue(self, token):
        return getSchoolToolApplication()['groups'][token]

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

    photo = Bytes(
        title=_("Photo"),
        required=False,
        description=_("""Photo (in JPEG format)"""))

    groups = List(
        title=_("Groups"),
        required=False,
        description=_("Add the person to the selected groups."),
        value_type=Choice(source=GroupsSource()))

def setUpPersonAddCustomWidgets(form_fields):
    form_fields['password'].custom_widget = PasswordConfirmationWidget
    form_fields['groups'].custom_widget = SourceMultiCheckBoxWidget

class PersonAddView(BasicForm):
    """A view for adding a person."""

    template = ViewPageTemplateFile('person_add.pt')

    form_fields = form.Fields(IPersonAddForm, render_context=False)
    setUpPersonAddCustomWidgets(form_fields)

    def title(self):
        return _("Add person")

    @form.action(_("Apply"))
    def handle_apply_action(self, action, data):
        if data['username'] in self.context:
            self.status = _("This username is already used!")
            return None
        person = self.createPerson(data['title'],
                                   data['username'],
                                   data['password'],
                                   data['photo'])
        self.addPersonToGroups(person, data['groups'])
        self.initPerson(person, data)
        self.addPerson(person)
        return self._redirect()

    @form.action(_("Cancel"))
    def handle_cancel_action(self, action, data):
        # XXX validation upon cancellation doesn't make any sense
        # how to make this work properly?
        return self._redirect()

    def initPerson(self, person, data):
        """Override this in subclasses to do further initialization.
        """
        pass

    def _redirect(self):
        url = zapi.absoluteURL(self.context, self.request)
        self.request.response.redirect(url)
        return ''

    def _factory(self, username, title):
        return getUtility(IPersonFactory)(username, title)

    def createPerson(self, title, username, password, photo):
        person = self._factory(username=username, title=title)
        person.setPassword(password)
        person.photo = photo
        return person

    def addPersonToGroups(self, person, groups):
        for group in groups:
            person.groups.add(group)

    def addPerson(self, person):
        """Add `person` to the container.

        Uses the username of `person` as the object ID (__name__).
        """
        name = person.username
        self.context[name] = person
        return person

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
