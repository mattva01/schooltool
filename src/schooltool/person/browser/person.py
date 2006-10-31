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
from zope.security.management import checkPermission
from zope.viewlet.viewlet import ViewletBase

from schooltool import SchoolToolMessage as _
from schooltool.skin.form import BasicForm
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.app import ContainerView, ContainerDeleteView
from schooltool.person.interfaces import IPasswordWriter
from schooltool.person.interfaces import IPerson, IPersonFactory
from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.interfaces import IPersonContainer, IPersonContained
from schooltool.person.person import Person
from schooltool.widget.password import PasswordConfirmationWidget
from schooltool.traverser.traverser import AdapterTraverserPlugin
from schooltool.person.interfaces import IPasswordWriter
from schooltool.skin.table import FilterWidget


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
        return iter(ISchoolToolApplication(None)['groups'].values())

    def __len__(self):
        return len(ISchoolToolApplication(None)['groups'].values())


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
        return ISchoolToolApplication(None)['groups'][token]


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
        writer = IPasswordWriter(self.context)
        writer.setPassword(data['password'])
        self.status = _('Changed password')

    @form.action(_("Cancel"))
    def handle_cancel_action(self, action, data):
        # redirect to parent
        url = zapi.absoluteURL(self.context, self.request)
        self.request.response.redirect(url)
        return ''


class IPersonInfoManager(IViewletManager):
    """Provides a viewlet hook for the information on a Person's page."""


class PasswordEditMenuItem(ViewletBase):
    """Viewlet that is visible if user can change the password of the context."""

    def render(self):
        if checkPermission('schooltool.edit', IPasswordWriter(self.context)):
            return super(PasswordEditMenuItem, self).render()


class PersonFilterWidget(FilterWidget):
    """A filter widget for persons.

    Filters the list of available persons by title or groups they belong to.
    """

    template = ViewPageTemplateFile('person_filter.pt')
    parameters = ['SEARCH_TITLE', 'SEARCH_GROUP']

    def groups(self):
        groups = []
        from schooltool.app.app import getSchoolToolApplication
        for id, group in ISchoolToolApplication(None)['groups'].items():
            if len(group.members) > 0:
                groups.append({'id': id,
                               'title': "%s (%s)" % (group.title, len(group.members))})
        return groups

    def filter(self, list):
        if 'CLEAR_SEARCH' in self.request:
            for parameter in self.parameters:
                self.request.form[parameter] = ''
            return list

        results = list

        if 'SEARCH_TITLE' in self.request:
            searchstr = self.request['SEARCH_TITLE'].lower()
            results = [item for item in results
                       if searchstr in item.title.lower()]

        if 'SEARCH_GROUP' in self.request:
            from schooltool.app.app import getSchoolToolApplication
            group = ISchoolToolApplication(None)['groups'].get(self.request['SEARCH_GROUP'])
            if not group:
                return results

            results = [item for item in results
                       if group in item.groups]

        return results

    def active(self):
        for parameter in self.parameters:
            if parameter in self.request:
                return True
        return False

    def extra_url(self):
        url = ""
        for parameter in self.parameters:
            if parameter in self.request:
                url += '&%s=%s' % (parameter, self.request.get(parameter))
        return url
