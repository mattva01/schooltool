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
Basic person browser views.
"""
from zope.interface import Interface, implements
from zope.container.interfaces import INameChooser
from zope.app.form.browser.interfaces import ITerms
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getUtility, queryMultiAdapter, getMultiAdapter
from zope.i18n import translate
from z3c.form import form, field, button, validator
from z3c.form.interfaces import DISPLAY_MODE
from zope.interface import invariant, Invalid
from zope.schema import Password, TextLine, Choice, List, Object
from zope.schema import ValidationError
from zope.schema.interfaces import ITitledTokenizedTerm, IField
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.viewlet.viewlet import ViewletBase
from zope.security.checker import canAccess

import z3c.form.interfaces
from z3c.form.validator import SimpleFieldValidator
from zc.table import table

import schooltool.skin.flourish.page
import schooltool.skin.flourish.containers
import schooltool.skin.flourish.breadcrumbs
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.browser.app import FlourishRelationshipViewBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.common.inlinept import InheritTemplate
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.group.interfaces import IGroupContainer
from schooltool.person.interfaces import IPerson, IPersonFactory
from schooltool.person.browser.person import PersonTableFormatter
from schooltool.schoolyear.interfaces import ISchoolYearContainer, ISchoolYear
from schooltool.skin.containers import TableContainerView
from schooltool.skin import flourish
from schooltool.skin.flourish.interfaces import IViewletManager
from schooltool.skin.flourish.form import FormViewlet
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManager
from schooltool.skin.flourish.content import ContentProvider
from schooltool.table.interfaces import ITableFormatter
from schooltool.table.table import DependableCheckboxColumn
from schooltool.table.catalog import IndexedLocaleAwareGetterColumn
from schooltool.table.interfaces import IIndexedColumn
from schooltool.report.browser.report import RequestReportDownloadDialog

from schooltool.common import SchoolToolMessage as _



class BasicPersonContainerView(TableContainerView):
    """A Person Container view."""
    template = ViewPageTemplateFile("templates/container.pt")
    delete_template = ViewPageTemplateFile("templates/person_container_delete.pt")

    index_title = _("Person index")

    def isDeletingHimself(self):
        person = IBasicPerson(self.request.principal, None)
        return person in self.itemsToDelete

    @property
    def schoolyears(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        return syc


class DeletePersonCheckboxColumn(DependableCheckboxColumn):

    def __init__(self, *args, **kw):
        kw = dict(kw)
        self.disable_items = kw.pop('disable_items', None)
        super(DeletePersonCheckboxColumn, self).__init__(*args, **kw)

    def hasDependents(self, item):
        if self.disable_items and item.__name__ in self.disable_items:
            return True
        return DependableCheckboxColumn.hasDependents(self, item)


class FlourishBasicPersonContainerView(flourish.containers.TableContainerView):
    """A Person Container view."""

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/manage'


class PersonContainerLinks(flourish.page.RefineLinksViewlet):
    """Person container links viewlet."""


class PersonLinks(flourish.page.RefineLinksViewlet):
    """Person links viewlet."""

    @property
    def title(self):
        return "%s %s" % (self.context.first_name, self.context.last_name)


class PersonImportLinks(flourish.page.RefineLinksViewlet):
    """Person container import links viewlet."""


class PersonSettingsLinks(flourish.page.RefineLinksViewlet):
    """Person settings links viewlet."""


class PersonActionsLinks(flourish.page.RefineLinksViewlet):
    """Person actions links viewlet."""


class IPersonAddForm(IBasicPerson):

    group = Choice(
        title=_(u"Group"),
        description=_(u"You can select one group membership now.  Manage multiple memberships after account creation."),
        source="schooltool.basicperson.group_vocabulary",
        required=False)

    advisor = Choice(
        title=_(u"Advisor"),
        source="schooltool.basicperson.advisor_vocabulary",
        required=False)

    username = TextLine(
        title=_("Username"),
        description=_(u"Cannot begin with '+' or '@,' contain non-ascii characters or '/.'"),
        required=True)

    password = Password(
        title=_("Password"),
        description=_(u"Users cannot log in until a password is assigned."),
        required=False)

    confirm = Password(
        title=_("Confirm password"),
        required=False)

    @invariant
    def isPasswordConfirmed(person):
        if person.password != person.confirm:
            raise Invalid(_(u"Passwords do not match"))


class PersonAddFormAdapter(object):
    implements(IPersonAddForm)
    adapts(IBasicPerson)

    def __init__(self, context):
        self.__dict__['context'] = context

    password = None

    def __setattr__(self, name, value):
        if name == 'password':
            self.context.setPassword(value)
        else:
            setattr(self.context, name, value)

    def __getattr__(self, name):
        return getattr(self.context, name)


class UsernameAlreadyUsed(ValidationError):
    __doc__ = _("This username is already in use")


class UsernameBadName(ValidationError):
    __doc__ = _("Names cannot begin with '+' or '@' or contain '/'")


class UsernameNonASCII(ValidationError):
    __doc__ = _("Usernames cannot contain non-ascii characters")


class UsernameValidator(SimpleFieldValidator):

    def validate(self, username):
        super(UsernameValidator, self).validate(username)
        if username is not None:
            if username in self.context:
                raise UsernameAlreadyUsed(username)
            try:
                INameChooser(self.context).checkName(username, None)
            except ValueError:
                raise UsernameBadName(username)
        # XXX: this has to be fixed
        # XXX: SchoolTool should handle UTF-8
        try:
            username.encode('ascii')
        except UnicodeEncodeError:
            raise UsernameNonASCII(username)


validator.WidgetValidatorDiscriminators(UsernameValidator,
                                        field=IPersonAddForm['username'])


class PasswordsDontMatch(ValidationError):
    __doc__ = _(u"Passwords do not match")


class PasswordValidator(SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the password error next to the widget!
        super(PasswordValidator, self).validate(value)
        confirm_widget = self.view.widgets['confirm']
        confirm_value = self.request.get(confirm_widget.name)
        if value is not None and value != confirm_value:
            raise PasswordsDontMatch()


validator.WidgetValidatorDiscriminators(PasswordValidator,
                                        field=IPersonAddForm['password'])


class PersonForm(object):

    formErrorsMessage = _('Please correct the marked fields below.')

    def generateExtraFields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        if IBasicPerson.providedBy(self.context):
            limit_keys = [group.__name__ for group in self.context.groups]
        else:
            limit_keys = []
        for field_desc in field_descriptions.filter_keys(limit_keys):
            fields += field_desc.makeField()
        return fields


class PersonView(PersonForm, form.DisplayForm):

    template = ViewPageTemplateFile('templates/person_view.pt')

    @property
    def label(self):
        return self.context.title

    def update(self):
        self.fields = field.Fields(IBasicPerson)
        self.fields += self.generateExtraFields()
        super(PersonView, self).update()

    def __call__(self):
        self.update()
        return self.render()


class FlourishPersonView(flourish.page.Page):
    """Person index.html view."""


class FlourishPersonInfo(flourish.page.Content):
    body_template = ViewPageTemplateFile('templates/f_person_view_details.pt')

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class PersonAddFormBase(PersonForm, form.AddForm):
    """Person add form for basic persons."""

    def update(self):
        self.fields = field.Fields(IPersonAddForm)
        self.fields += self.generateExtraFields()
        super(PersonAddFormBase, self).update()

    def updateActions(self):
        super(PersonAddFormBase, self).updateActions()
        self.actions['add'].addClass('button-ok')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        super(PersonAddFormBase, self).handleAdd.func(self, action)

    def create(self, data):
        person = self._factory(data['username'], data['first_name'],
                               data['last_name'])
        data.pop('confirm')
        group = data.pop('group')
        advisor = data.pop('advisor')
        form.applyChanges(self, person, data)
        if group is not None:
            person.groups.add(group)
        if advisor is not None:
            person.advisors.add(advisor)
        self._person = person
        return person

    def nextURL(self):
        return absoluteURL(self._person, self.request)

    @property
    def _factory(self):
        return getUtility(IPersonFactory)

    def add(self, person):
        """Add `person` to the container.

        Uses the username of `person` as the object ID (__name__).
        """
        name = person.username
        self.context[name] = person
        return person


class PersonAddView(PersonAddFormBase):
    """Person add form for basic persons."""
    label = _("Add new person")
    template = ViewPageTemplateFile('templates/person_add.pt')

    def updateActions(self):
        super(PersonAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        super(PersonAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class ITempPersonList(Interface):
    usernames = List(
        title=_('Usernames'),
        value_type=TextLine(
            title=_('Username'),
            required=False),
        required=False,
        )


class TempPersonList(object):
    implements(ITempPersonList)

    def __init__(self):
        self.usernames = []


class MultiplePersonAddView(form.Form):
    template = ViewPageTemplateFile('templates/person_add_multiple.pt')
    label = _("Add multiple persons")
    fields = field.Fields(ITempPersonList)
    addform = None
    temp_content = None

    def __init__(self, *args, **kw):
        self.temp_content = TempPersonList()
        super(MultiplePersonAddView, self).__init__(*args, **kw)

    def getContent(self):
        return self.temp_content

    def buildAddForm(self):
        self.addform = PersonAddSubForm(self.context, self.request, self)
        n = len(self.widgets['usernames'].value)
        self.addform.prefix = 'addform_%d.' % n

    def updateWidgets(self):
        super(MultiplePersonAddView, self).updateWidgets()
        self.widgets['usernames'].mode = z3c.form.interfaces.HIDDEN_MODE
        self.buildAddForm()

    def update(self):
        super(MultiplePersonAddView, self).update()
        data, errors = self.extractData(setErrors=False)
        form.applyChanges(self, self.getContent(), data)
        self.addform.update()

    def appendAdded(self, username):
        usernames = self.widgets['usernames'].value
        usernames.append(username)
        self.widgets['usernames'].value = usernames
        content = self.getContent()
        content.usernames = usernames

    def render(self):
        if self.addform._finishedAdd:
            self.appendAdded(self.addform._person.__name__)
            # And build a fresh add form.
            self.buildAddForm()
            self.addform.update()
        return super(MultiplePersonAddView, self).render()

    @property
    def addedPersons(self):
        app_persons = ISchoolToolApplication(None)['persons']
        content = self.getContent()
        if not content.usernames:
            return []
        return [app_persons[username]
                for username in content.usernames
                if username in app_persons]

    def updateActions(self):
        super(MultiplePersonAddView, self).updateActions()
        self.actions['done'].addClass('button-neutral')

    @button.buttonAndHandler(_("Done"))
    def handle_done_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class FlourishMultiplePersonAddView(MultiplePersonAddView):
    template = InheritTemplate(flourish.page.Page.template)

    def buildAddForm(self):
        self.addform = FlourishPersonAddSubForm(
            self.context, self.request, self)
        n = len(self.widgets['usernames'].value)
        self.addform.prefix = 'addform_%d.' % n


class PersonAddSubForm(PersonAddFormBase):
    template = ViewPageTemplateFile('templates/person_add_subform.pt')

    def __init__(self, context, request, parentForm):
        self.parentForm = parentForm
        super(PersonAddSubForm, self).__init__(context, request)

    def update(self):
        super(PersonAddSubForm, self).update()
        for action in self.parentForm.actions.executedActions:
            handler = queryMultiAdapter(
                (self, self.request, self.getContent(), action),
                interface=z3c.form.interfaces.IActionHandler)
            if handler is not None:
                handler()


class FlourishPersonAddSubForm(PersonAddSubForm):
    template = ViewPageTemplateFile('templates/f_person_add_subform.pt')


class PersonEditView(PersonForm, form.EditForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/person_add.pt')

    def update(self):
        self.fields = field.Fields(IBasicPerson)
        self.fields += self.generateExtraFields()
        super(PersonEditView, self).update()

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(PersonEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def label(self):
        return _(u'Change information for ${fullname}',
                 mapping={'fullname': self.context.title})


class FlourishPersonEditView(flourish.page.Page, PersonEditView):

    label = None

    def update(self):
        self.buildFieldsetGroups()
        PersonEditView.update(self)

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handleApply(self, action):
        super(FlourishPersonEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return url

    def makeRows(self, fields, cols=1):
        rows = []
        while fields:
            rows.append(fields[:cols])
            fields = fields[cols:]
        return rows

    def makeFieldSet(self, fieldset_id, legend, fields, cols=1):
        result = {
            'id': fieldset_id,
            'legend': legend,
            }
        result['rows'] = self.makeRows(fields, cols)
        return result

    def buildFieldsetGroups(self):
        self.fieldset_groups = {
            'full_name': (
                _('Full Name'),
                ['prefix', 'first_name', 'middle_name', 'last_name',
                 'suffix', 'preferred_name']),
            'details': (
                _('Details'), ['gender', 'birth_date']),
            'demographics': (
                _('Demographics'), list(self.getDemoFields())),
            }
        self.fieldset_order = (
            'full_name', 'details', 'demographics')

    def fieldsets(self):
        result = []
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result

    def getDemoFields(self):
        fields = field.Fields()
        dfs = IDemographicsFields(ISchoolToolApplication(None))
        keys = []
        for field_desc in dfs.filter_keys(keys):
            fields += field_desc.makeField()
        return fields


class PersonTerm(object):
    """A term for displaying a person."""
    implements(ITitledTokenizedTerm)

    def __init__(self, value):
        self.title = value.title
        self.token = value.__name__
        self.value = value


class TermsBase(object):
    """Base terms implementation."""

    implements(ITerms)

    def factory(self, value):
        raise NotImplementedError(
            "Term Factory must be provided by inheriting classes.")

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getTerm(self, value):
        if value not in self.context:
            raise LookupError(value)
        return self.factory(value)

    def getValue(self, token):
        if token not in self.context:
            raise LookupError(token)
        return token


class PersonTerms(TermsBase):
    """Displaying persons."""
    factory = PersonTerm

    def getValue(self, token):
        if token not in self.context:
            raise LookupError(token)
        app = ISchoolToolApplication(None)
        return app['persons'][token]


class GroupTerm(object):
    """A term for displaying a group."""
    implements(ITitledTokenizedTerm)

    def __init__(self, value):
        self.title = value.title
        self.token = value.__name__
        self.value = value


class GroupTerms(TermsBase):
    """Displaying groups."""

    factory = GroupTerm


class PersonAdvisorView(RelationshipViewBase):
    """View class for adding/removing advisors to/from a person."""

    __used_for__ = IBasicPerson

    current_title = _("Current Advisors")
    available_title = _("Add Advisors")

    @property
    def title(self):
        return _("Advisors of ${person}",
            mapping={'person': self.context.title})

    def getSelectedItems(self):
        """Return a list of current advisors."""
        return self.context.advisors

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.advisors


class FlourishPersonAdvisorView(FlourishRelationshipViewBase):

    current_title = _('Current advisors')
    available_title = _('Available advisors')

    def getSelectedItems(self):
        return self.context.advisors

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.advisors


class PersonAdviseeView(RelationshipViewBase):
    """View class for adding/removing advisees to/from a person."""

    __used_for__ = IBasicPerson

    current_title = _("Current Advisees")
    available_title = _("Add Advisees")

    @property
    def title(self):
        return _("Advisees of ${person}",
            mapping={'person': self.context.title})

    def getSelectedItems(self):
        """Return a list of current advisees."""
        return self.context.advisees

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.advisees


class FlourishPersonAdviseeView(FlourishRelationshipViewBase):

    current_title = _("Current advisees")
    available_title = _("Available advisees")

    def getSelectedItems(self):
        return self.context.advisees

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.advisees


class IFlourishPersonInfoManager(IViewletManager):
    pass


class FlourishPersonInfoManager(ViewletManager):
    pass


class FlourishAdvisoryViewlet(Viewlet):
    """A viewlet showing the advisors/advisees of a person."""

    template = ViewPageTemplateFile('templates/f_advisoryViewlet.pt')
    body_template = None

    def getTable(self, items):
        persons = ISchoolToolApplication(None)['persons']
        result = getMultiAdapter((persons, self.request), ITableFormatter)
        result.setUp(table_formatter=table.StandaloneFullFormatter, items=items)
        return result

    @property
    def advisors_table(self):
        return self.getTable(list(self.context.advisors))

    @property
    def advisees_table(self):
        return self.getTable(list(self.context.advisees))

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishGeneralViewlet(FormViewlet):
    """A viewlet showing the core attributes of a person."""

    template = ViewPageTemplateFile('templates/f_generalViewlet.pt')
    body_template = None
    mode = DISPLAY_MODE

    def getFields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        limit_keys = [group.__name__ for group in self.context.groups]
        for field_desc in field_descriptions.filter_keys(limit_keys):
            fields += field_desc.makeField()
        return fields

    @property
    def filtered_widgets(self):
        result = [widget for widget in self.widgets.values()
                  if widget.value]
        return result

    @property
    def heading(self):
        attrs = ['prefix', 'first_name', 'middle_name', 'last_name', 'suffix']
        values = []
        for attr in attrs:
            value = getattr(self.context, attr)
            if value:
                values.append(value)
        return ' '.join(values)

    def makeRow(self, attr, value):
        if value is None:
            value = u''
        return {
            'label': attr,
            'value': unicode(value),
            }

    @property
    def table(self):
        rows = []
        fields = field.Fields(IBasicPerson)
        fields += field.Fields(IPerson).select('username')
        for attr in fields:
            value = getattr(self.context, attr)
            if value:
                label = fields[attr].field.title
                if attr == 'gender':
                    vocabulary = IBasicPerson[attr].vocabulary
                    message = vocabulary.getTermByToken(value).title
                    value = translate(message, context=self.request)
                rows.append(self.makeRow(label, value))
        return rows

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    def update(self):
        self.fields = self.getFields()
        super(FlourishGeneralViewlet, self).update()


###############  Base class of all group-aware add views ################
class PersonAddViewBase(PersonAddFormBase):

    id = 'person-form'
    template = ViewPageTemplateFile('templates/person_form.pt')

    def makeRows(self, fields, cols=1):
        rows = []
        while fields:
            rows.append(fields[:cols])
            fields = fields[cols:]
        return rows

    def makeFieldSet(self, fieldset_id, legend, fields, cols=1):
        result = {
            'id': fieldset_id,
            'legend': legend,
            }
        result['rows'] = self.makeRows(fields, cols)
        return result

    def fieldsets(self):
        result = []
        sources = [
            (self.base_id, self.base_legend, list(self.getBaseFields())),
            (self.demo_id, self.demo_legend, list(self.getDemoFields())),
            ]
        for fieldset_id, legend, fields in sources:
            result.append(self.makeFieldSet(fieldset_id, legend, fields, 2))
        return result

    def getDemoFields(self):
        fields = field.Fields()
        dfs = IDemographicsFields(ISchoolToolApplication(None))
        keys = self.group_id and [self.group_id] or []
        for field_desc in dfs.filter_keys(keys):
            fields += field_desc.makeField()
        return fields

    def getBaseFields(self):
        return field.Fields(IPersonAddForm).omit('group')

    def updateActions(self):
        super(PersonAddViewBase, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'))
    def handleAdd(self, action):
        super(PersonAddViewBase, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def create(self, data):
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        person = self._factory(username, first_name, last_name)
        data.pop('confirm')
        form.applyChanges(self, person, data)
        group = None
        syc = ISchoolYearContainer(ISchoolToolApplication(None))
        active_schoolyear = syc.getActiveSchoolYear()
        if active_schoolyear is not None:
            if self.group_id:
                group = IGroupContainer(active_schoolyear).get(self.group_id)
            else:
                group = data.get('group')
        if group is not None:
            person.groups.add(group)
        self._person = person
        return person

    def update(self):
        self.fields = self.getBaseFields()
        self.fields += self.getDemoFields()
        self.updateWidgets()
        self.updateActions()
        self.actions.execute()

    def updateWidgets(self):
        super(PersonAddViewBase, self).updateWidgets()


class FlourishPersonAddView(PersonAddViewBase):
    template = InheritTemplate(flourish.page.Page.template)
    page_template = InheritTemplate(flourish.page.NoSidebarPage.page_template)

    fieldset_groups = None
    fieldset_order = None

    group_id = None

    def update(self):
        self.buildFieldsetGroups()
        PersonAddViewBase.update(self)
        self.widgets['birth_date'].addClass('birth-date-field')

    def getBaseFields(self):
        if self.group_id:
            return field.Fields(IPersonAddForm).omit('group')
        return field.Fields(IPersonAddForm)

    def buildFieldsetGroups(self):
        relationship_fields = ['advisor']
        if not self.group_id:
            relationship_fields[0:0] = ['group']
        self.fieldset_groups = {
            'full_name': (
                _('Full Name'),
                ['prefix', 'first_name', 'middle_name', 'last_name',
                 'suffix', 'preferred_name']),
            'details': (
                _('Details'), ['gender', 'birth_date']),
            'demographics': (
                _('Demographics'), list(self.getDemoFields())),
            'relationships': (
                _('Relationships'), relationship_fields),
            'user': (
                _('User'), ['username', 'password', 'confirm']),
            }
        self.fieldset_order = (
            'full_name', 'details', 'demographics',
            'relationships', 'user')

    def fieldsets(self):
        result = []
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleSubmit(self, action):
        super(FlourishPersonAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Submit and add'), name='submitadd')
    def handleSubmitAndAdd(self, action):
        super(FlourishPersonAddView, self).handleAdd.func(self, action)
        if self._finishedAdd:
            self.request.response.redirect(self.action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(FlourishPersonAddView, self).updateActions()
        self.actions['submitadd'].addClass('button-neutral')


###############  Group-aware add views ################
class TeacherAddView(PersonAddViewBase):

    group_id = 'teachers'
    base_id = 'base-data'
    base_legend = _('Teacher identification')
    demo_id = 'demo-data'
    demo_legend = _('Teacher demographics')
    label = _('Add new teacher')


class StudentAddView(PersonAddViewBase):

    group_id = 'students'
    base_id = 'base-data'
    base_legend = _('Student identification')
    demo_id = 'demo-data'
    demo_legend = _('Student demographics')
    label = _('Add new student')


class AdministratorAddView(PersonAddViewBase):

    group_id = 'administrators'
    base_id = 'base-data'
    base_legend = _('Administrator identification')
    demo_id = 'demo-data'
    demo_legend = _('Administrator demographics')
    label = _('Add new administrator')


class AddPersonViewlet(object):

    def hasSchoolYear(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        sy = syc.getActiveSchoolYear()
        return sy is not None


class PersonTitle(ContentProvider):
    render = InlineViewPageTemplate('''
        <span tal:replace="view/title"></span>
    '''.strip())

    def title(self):
        person = self.context
        return "%s %s" % (person.first_name, person.last_name)


class BasicPersonTableFormatter(PersonTableFormatter):

    def columns(self):
        cols = list(reversed(PersonTableFormatter.columns(self)))
        username = IndexedLocaleAwareGetterColumn(
            index='__name__',
            name='username',
            title=_(u'Username'),
            getter=lambda i, f: i.__name__,
            subsort=True)
        return cols + [username]

    def render(self):
        columns = [IIndexedColumn(c) for c in self._columns]
        formatter = self._table_formatter(
            self.context, self.request, self._items,
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.cssClasses['table'] = 'persons-table relationships-table'
        return formatter()


class FlourishManagePeopleOverview(flourish.page.Content):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_people_overview.pt')

    built_in_groups = ('administrators', 'clerks', 'manager', 'teachers',
                       'students')

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def has_schoolyear(self):
        return self.schoolyear is not None

    @property
    def groups(self):
        return IGroupContainer(self.schoolyear, None)

    @property
    def persons(self):
        return self.context['persons']

    @property
    def school_name(self):
        preferences = IApplicationPreferences(self.context)
        return preferences.title


class FlourishRequestPersonXMLExportView(RequestReportDownloadDialog):

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/person_export.xml'


def getUserViewlet(context, request, view, manager, name):
    principal = request.principal
    user = IPerson(principal, None)
    if user is None:
        return None
    viewlet = flourish.viewlet.lookupViewlet(
        user, request, view, manager, name=name)
    return viewlet


def getPersonActiveViewlet(person, request, view, manager):
    user = IPerson(request.principal, None)
    if (user is not None and
        user.__name__ == person.__name__):
        return u"home"
    return flourish.page.getParentActiveViewletName(
        person, request, view, manager)
