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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Person browser views.
"""
import urllib

from zope.authentication.interfaces import IAuthentication
from zope.interface import Interface
from zope.publisher.interfaces import NotFound
from zope.schema import Password
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import IIterableSource
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.proxy import sameProxiedObjects
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canAccess
from zope.app.form.browser.source import SourceMultiCheckBoxWidget as SourceMultiCheckBoxWidget_
from zope.app.form.browser.interfaces import ITerms
from zope.app.dependable.interfaces import IDependable
from zope.publisher.browser import BrowserView
from zope.viewlet.interfaces import IViewletManager
from zope.component import getUtility
from zope.interface import implements
from zope.browserpage import ViewPageTemplateFile
from zope.viewlet.viewlet import ViewletBase
from zope.component import queryAdapter
from zope.component import adapts
from zope.catalog.interfaces import ICatalog
from zope.intid.interfaces import IIntIds
from zope.traversing.browser.absoluteurl import absoluteURL
from z3c.form import form, field, button, widget, term, validator
from z3c.form.browser.radio import RadioWidget
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator

import schooltool.skin.flourish.page
import schooltool.skin.flourish.form
from schooltool.group.interfaces import IGroupContainer
from schooltool.common import SchoolToolMessage as _
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.catalog import buildQueryString
from schooltool.person.interfaces import IPasswordWriter
from schooltool.person.interfaces import IPerson, IPersonFactory
from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.interfaces import IPersonContainer, IPersonContained
from schooltool import table
from schooltool.skin import flourish
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.table.column import IndexedLocaleAwareGetterColumn
from schooltool.table.table import url_cell_formatter


def SourceMultiCheckBoxWidget(field, request):
    source = field.value_type.source
    return SourceMultiCheckBoxWidget_(field, source, request)


class PersonPhotoView(BrowserView):
    """View that returns photo of a Person."""

    __used_for__ = IPerson

    def __call__(self):
        photo = self.context.photo
        if not photo:
            raise NotFound(self.context, u'photo', self.request)
        self.request.response.setHeader('Content-Type', "image/jpeg")
        return photo


class CalendarPeriodsWidgetTerms(term.BoolTerms):

    trueLabel = _('Show periods')
    falseLabel =  _('Show hours')


class CalendarPublicWidgetTerms(term.BoolTerms):

    trueLabel = _(u'the public')

    @property
    def falseLabel(self):
        person = self.context.__parent__
        return _('${person_full_name} and school administration',
                 mapping={'person_full_name': person.title})


class CalendarPeriodsRadioWidget(RadioWidget):

    @property
    def terms(self):
        return CalendarPeriodsWidgetTerms(self.context, self.request,
                                          self.form, self.field, self)


class CalendarPublicRadioWidget(RadioWidget):

    @property
    def terms(self):
        return CalendarPublicWidgetTerms(self.context, self.request,
                                         self.form, self.field, self)


def calendar_public_widget_label(adapter):
    person = adapter.context.__parent__
    return _("${person_full_name}'s calendar is visible to...",
             mapping={'person_full_name': person.title})


CalendarPublicWidgetLabel = widget.ComputedWidgetAttribute(
    calendar_public_widget_label,
    field=IPersonPreferences['cal_public'],
    widget=CalendarPublicRadioWidget)


def CalendarPeriodsWidgetFactory(field, request):
    return widget.FieldWidget(field, CalendarPeriodsRadioWidget(request))


def CalendarPublicWidgetFactory(field, request):
    return widget.FieldWidget(field, CalendarPublicRadioWidget(request))


class PersonPreferencesView(form.EditForm):
    """View used for editing person preferences."""

    fields = field.Fields(IPersonPreferences)
    fields['cal_periods'].widgetFactory = CalendarPeriodsWidgetFactory
    fields['cal_public'].widgetFactory = CalendarPublicWidgetFactory
    template = ViewPageTemplateFile('person_preferences.pt')

    @property
    def label(self):
        person = self.context.__parent__
        return _(u'Change preferences for ${person_full_name}',
                 mapping={'person_full_name': person.title})

    @button.buttonAndHandler(_("Apply"))
    def handle_edit_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)
        self.redirectToPerson()

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.redirectToPerson()

    def updateActions(self):
        super(PersonPreferencesView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def redirectToPerson(self):
        url = absoluteURL(self.context.__parent__, self.request)
        self.request.response.redirect(url)


class FlourishPasswordChangedView(flourish.form.DialogForm):

    dialog_submit_actions = ('ok',)
    label = None

    def initDialog(self):
        super(FlourishPasswordChangedView, self).initDialog()
        self.ajax_settings['dialog']['dialogClass'] = 'explicit-close-dialog'
        self.ajax_settings['dialog']['closeOnEscape'] = False

    @button.buttonAndHandler(_('ok-button', 'OK'), name='ok')
    def handle_submit_(self, action):
        app = ISchoolToolApplication(None)
        persons = app['persons']
        username = self.request.get('username', '')
        person = persons.get(username, None)
        if person is not None:
            url = absoluteURL(person, self.request)
        else:
            url = absoluteURL(app, self.request)
        self.request.response.redirect(url)
        self.ajax_settings['dialog'] = 'close'

    def updateActions(self):
        super(FlourishPasswordChangedView, self).updateActions()
        self.actions['ok'].addClass('button-ok')


class FlourishPersonPreferencesView(flourish.form.DialogForm,
                                    PersonPreferencesView):
    """View used for editing person preferences."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.handler(PersonPreferencesView.buttons['apply'])
    def handleAdd(self, action):
        self.handleApply.func(self, action)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'
        # Also I assume the preferences don't change the parent
        # view content, so let's not reload it now.
        self.reload_parent = False

    def initDialog(self):
        super(FlourishPersonPreferencesView, self).initDialog()
        self.ajax_settings['dialog']['width'] = '306'
        self.ajax_settings['dialog']['dialogClass'] = 'narrow-dialog'


class FlourishPersonPreferencesLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        person = self.context
        title = _(u'Change preferences for ${person_full_name}',
                  mapping={'person_full_name': person.title})
        return translate(title, context=self.request)

    @property
    def enabled(self):
        prefs = IPersonPreferences(self.context)
        if not flourish.canEdit(prefs):
            return False
        return super(FlourishPersonPreferencesLink, self).enabled


class FlourishPersonDeleteView(flourish.form.DialogForm, form.EditForm):
    """View used for editing person preferences."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        url = '%s/delete.html?delete.%s&CONFIRM' % (
            absoluteURL(self.context.__parent__, self.request),
            self.context.username)
        self.request.response.redirect(url)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishPersonDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishPersonDeleteLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        person = self.context
        title = _(u'Delete ${person_full_name}',
                  mapping={'person_full_name': person.title})
        return translate(title, context=self.request)

    def render(self, *args, **kw):
        dep = IDependable(removeSecurityProxy(self.context), None)
        if (dep is not None and dep.dependents()):
            return ''
        return flourish.page.ModalFormLinkViewlet.render(self, *args, **kw)


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

    current = Password(
        title=_('Current password'),
        required=True)

    password = Password(
        title=_("New password"),
        required=True)

    verify_password = Password(
        title=_("Verify new password"),
        required=True)


class PersonPasswordEditView(form.Form):

    label = _("Edit password")
    template = ViewPageTemplateFile('password_form.pt')

    @property
    def fields(self):
        fields = field.Fields(IPasswordEditForm, ignoreContext=True)
        person = IPerson(self.request.principal)
        if person.username is not self.context.username:
            # Editing someone else's password
            fields = fields.omit('current')
        return fields

    @button.buttonAndHandler(_("Apply"))
    def handle_edit_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        writer = IPasswordWriter(self.context)
        writer.setPassword(data['password'])
        person = IPerson(self.request.principal)
        self.status = _('Password changed successfully')
        app = ISchoolToolApplication(None)
        url = '%s/password_changed.html?username=%s'
        url = url % (absoluteURL(app, self.request), self.context.username)
        self.dialog_show = True
        self.dialog_title = translate(self.status, context=self.request)
        self.dialog_url = url
        if person.username is self.context.username:
            auth = getUtility(IAuthentication)
            auth.setCredentials(self.request,
                                person.username,
                                data['password'])

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        # redirect to parent
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(PersonPasswordEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishPersonPasswordEditView(flourish.page.Page,
                                     PersonPasswordEditView):

    label = None
    legend = _('Change password')
    formErrorsMessage = _('Please correct the marked fields below.')

    def update(self):
        PersonPasswordEditView.update(self)


class WrongCurrentPassword(ValidationError):
    __doc__ = _('Wrong password supplied')


class PasswordsDontMatch(ValidationError):
    __doc__ = _('Supplied new passwords are not identical')


class CurrentPasswordValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        super(CurrentPasswordValidator, self).validate(value)
        if value is not None and not self.context.checkPassword(value):
            raise WrongCurrentPassword(value)


validator.WidgetValidatorDiscriminators(CurrentPasswordValidator,
                                        field=IPasswordEditForm['current'])


class PasswordsMatchValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the validation error next to the widget!
        super(PasswordsMatchValidator, self).validate(value)
        name = self.view.widgets['verify_password'].name
        verify = self.request.get(name)
        if value is not None and value not in (verify,):
            raise PasswordsDontMatch(value)


validator.WidgetValidatorDiscriminators(PasswordsMatchValidator,
                                        field=IPasswordEditForm['password'])


class IPersonInfoManager(IViewletManager):
    """Provides a viewlet hook for the information on a Person's page."""


class PasswordEditMenuItem(ViewletBase):
    """Viewlet that is visible if user can change the password of the context."""

    def render(self):
        if checkPermission('schooltool.edit', IPasswordWriter(self.context)):
            return super(PasswordEditMenuItem, self).render()


class FlourishPasswordLinkViewlet(flourish.page.LinkViewlet):

    def render(self):
        if checkPermission('schooltool.edit', IPasswordWriter(self.context)):
            return super(FlourishPasswordLinkViewlet, self).render()


class PersonFilterWidget(table.catalog.IndexedFilterWidget):
    """A filter widget for persons.

    Filters the list of available persons by title or groups they belong to.
    """

    template = ViewPageTemplateFile('person_filter.pt')

    def groupContainer(self):
        # XXX must know which group container to pick
        app = ISchoolToolApplication(None)
        return IGroupContainer(app, {})

    search_title_id = 'SEARCH_TITLE'
    search_group_id = 'SEARCH_GROUP'

    @property
    def parameters(self):
        return (self.search_title_id, self.search_group_id)

    def groups(self):
        groups = []
        container = self.groupContainer()
        collator = ICollator(self.request.locale)
        group_items = sorted(container.items(),
                             cmp=collator.cmp,
                             key=lambda (gid, g): g.title)
        for id, group in group_items:
            if len(group.members) > 0:
                groups.append({'id': id,
                               'title': "%s (%s)" % (group.title, len(group.members))})
        return groups

    @property
    def source(self):
        return self.context

    def filter(self, items):
        if 'CLEAR_SEARCH' in self.request:
            for parameter in self.parameters:
                self.request.form[parameter] = ''
            return items

        if self.search_group_id in self.request:
            group = self.groupContainer().get(self.request[self.search_group_id])
            if group:
                int_ids = getUtility(IIntIds)
                keys = set([int_ids.queryId(person)
                            for person in group.members])
                items = [item for item in items
                         if item['id'] in keys]

        if self.search_title_id in self.request:
            searchstr = self.request[self.search_title_id]
            query = buildQueryString(searchstr)
            if query:
                catalog = ICatalog(self.source)
                result = catalog['text'].apply(query)
                items = [item for item in items
                         if item['id'] in result]

        return items

    def active(self):
        for parameter in self.parameters:
            if parameter in self.request:
                return True
        return False

    def quote(self, param):
        return urllib.quote(unicode(param).encode('UTF-8'))

    def extra_url(self):
        url = ""
        for parameter in self.parameters:
            if parameter in self.request:
                url += '&%s=%s' % (parameter, self.quote(self.request.get(parameter)))
        return url


class PersonTableFilter(table.ajax.IndexedTableFilter,
                        PersonFilterWidget):

    template = ViewPageTemplateFile('f_person_table_filter.pt')
    title = _('First name, last name or username')

    @property
    def search_title_id(self):
        return self.manager.html_id+"-title"

    @property
    def search_group_id(self):
        return self.manager.html_id+"-group"

    @property
    def parameters(self):
        return (self.search_title_id, self.search_group_id)

    groupContainer = PersonFilterWidget.groupContainer
    groups = PersonFilterWidget.groups
    active = PersonFilterWidget.active
    extra_url = PersonFilterWidget.extra_url

    def filter(self, results):
        if self.ignoreRequest:
            return results
        return PersonFilterWidget.filter(self, results)


def person_table_columns():
    """Columns for the old person table.

    Functional tests expect the first column to be first name."""
    first_name = IndexedLocaleAwareGetterColumn(
        index='first_name',
        name='first_name',
        cell_formatter=url_cell_formatter,
        title=_(u'First Name'),
        getter=lambda i, f: i.first_name,
        subsort=True)
    last_name = IndexedLocaleAwareGetterColumn(
        index='last_name',
        name='last_name',
        cell_formatter=url_cell_formatter,
        title=_(u'Last Name'),
        getter=lambda i, f: i.last_name,
        subsort=True)
    return [first_name, last_name]


class PersonTable(table.ajax.IndexedTable):

    @property
    def source(self):
        return ISchoolToolApplication(None)['persons']

    def columns(self):
        return person_table_columns()

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()


class PersonTableFormatter(table.catalog.IndexedTableFormatter):
    """Person container specific table formatter."""

    def columns(self):
        return person_table_columns()

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()


class PersonView(BrowserView):
    """A Person info view."""

    __used_for__ = IPersonContained

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)


class HomeView(PersonView):
    """A Person's homepage."""

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class IPreferencesMenuViewlet(Interface):
    """Marker interface so we could use custom crowd for Preferences menu item"""


class PreferencesActionMenuViewlet(object):
    implements(IPreferencesMenuViewlet)


class PreferencesMenuViewletCrowd(Crowd):
    adapts(IPreferencesMenuViewlet)

    def contains(self, principal):
        """Returns true if you have the permission to see the calendar."""
        crowd = queryAdapter(IPersonPreferences(self.context.context),
                             ICrowd,
                             name="schooltool.view")
        return crowd.contains(principal)


class PersonAddPersonViewlet(object):

    @property
    def container(self):
        return IPersonContainer(self.context)

    @property
    def visible(self):
        if not checkPermission("schooltool.edit", self.container):
            return False
        authenticated = IPerson(self.request.principal, None)
        target = IPerson(self.context, None)
        if sameProxiedObjects(authenticated, target):
            return False
        return True


class FlourishPersonFilterWidget(PersonFilterWidget):

    template = ViewPageTemplateFile('f_person_filter.pt')

    def filter(self, items):
        if 'CLEAR_SEARCH' in self.request:
            for parameter in self.parameters:
                self.request.form[parameter] = ''
            return items

        if 'SEARCH_GROUP' in self.request:
            group = self.groupContainer().get(self.request['SEARCH_GROUP'])
            if group:
                int_ids = getUtility(IIntIds)
                keys = set([int_ids.queryId(person)
                            for person in group.members])
                items = [item for item in items
                         if item['id'] in keys]

        if 'SEARCH_TITLE' in self.request:
            search_title = self.request['SEARCH_TITLE']
            query = buildQueryString(search_title)
            if query:
                catalog = ICatalog(self.source)
                result = catalog['text'].apply(query)
                items = [item for item in items
                         if item['id'] in result]

        return items
