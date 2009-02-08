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

$Id$
"""
import zope.interface
from zope.app.container.interfaces import INameChooser
from zope.app.form.browser.interfaces import ITerms
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getUtility
from zope.exceptions.interfaces import UserError
from z3c.form import form, field, button, validator
from zope.interface import implements
from zope.publisher.browser import BrowserView
from zope.schema import Password, TextLine, Choice
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form.validator import SimpleFieldValidator

from schooltool.group.interfaces import IGroupContainer
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPersonFactory

from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.common import SchoolToolMessage as _


class PersonView(BrowserView):

    template = ViewPageTemplateFile('templates/person_view.pt')

    def __call__(self):
        return self.template()


class IPersonAddForm(IBasicPerson):

    group = Choice(
        title=_(u"Group"),
        source="schooltool.basicperson.group_source",
        required=False)

    advisor = Choice(
        title=_(u"Advisor"),
        source="schooltool.basicperson.advisor_source",
        required=False)

    username = TextLine(
        title=_("Username"),
        description=_("Username"),
        required=True)

    password = Password(
        title=_("Password"),
        required=False)

    confirm = Password(
        title=_("Confirm"),
        required=False)


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


# XXX: I don't know why ValidationError returns a docstring instead
# of the actual error message it gets instantiated with, so I had to
# subclass to get useful error messages.
class UsernameValidationError(zope.schema.ValidationError):
    """Validation error related to a username."""
    def doc(self):
        return str(self)


class UsernameValidator(SimpleFieldValidator):

    def validate(self, username):
        if username in self.context:
            raise UsernameValidationError(_("This username is already in use!"))
        try:
            INameChooser(self.context).checkName(username, None)
        except UserError:
            raise UsernameValidationError(_("Names cannot begin with '+' or '@' or contain '/'"))

validator.WidgetValidatorDiscriminators(UsernameValidator,
                                        field=IPersonAddForm['username'])


class PersonAddView(form.AddForm):
    """Person add form for basic persons."""
    label = _("Add new person")
    template = ViewPageTemplateFile('templates/person_add.pt')

    fields = field.Fields(IPersonAddForm)

    def updateActions(self):
        super(PersonAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        if data['password'] != data['confirm']:
            self.status = _(u"Passwords do not match")
            return
        obj = self.createAndAdd(data)
        if obj is not None:
            # mark only as finished if we get the new object
            self._finishedAdd = True

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

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class PersonEditView(form.EditForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/person_add.pt')

    fields = field.Fields(IBasicPerson)

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

