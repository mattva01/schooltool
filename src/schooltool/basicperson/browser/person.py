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
from zope.component import adapter
from zope.component import adapts
from zope.component import getUtility
from zope.exceptions.interfaces import UserError
from z3c.form import form, field, button, validator
from zope.interface import implementer
from zope.interface import implements
from zope.publisher.browser import BrowserView
from zope.schema import Password
from zope.schema import TextLine
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form.validator import SimpleFieldValidator

from schooltool.group.interfaces import IGroupContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPersonContainer
from schooltool.person.interfaces import IPersonFactory

from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IBasicPerson, IStudent
from schooltool.common import SchoolToolMessage as _


class PersonView(BrowserView):

    template = ViewPageTemplateFile('templates/person_view.pt')

    @property
    def demographics(self):
        from schooltool.basicperson.interfaces import IDemographics
        return IDemographics(self.context)

    def __call__(self):
        return self.template()


class IPersonAddForm(IBasicPerson):

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

class PersonForm(object):

    def generateExtraFields(self):
        field_descriptions = IDemographicsFields(ISchoolToolApplication(None))
        fields = field.Fields()
        for field_desc in field_descriptions.values():
            fields += field_desc.makeField()
        return fields


class PersonAddView(form.AddForm, PersonForm):
    """Person add form for basic persons."""
    label = _("Add new person")
    template = ViewPageTemplateFile('templates/person_add.pt')

    def update(self):
        self.fields = field.Fields(IPersonAddForm) + field.Fields(IStudent)
        self.fields += self.generateExtraFields()
        super(PersonAddView, self).update()

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
        form.applyChanges(self, person, data)
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
        # Add the persons to his class
        if person.gradeclass is not None:
            groups = IGroupContainer(ISchoolToolApplication(None))
            person.groups.add(groups[person.gradeclass])
        return person

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class PersonEditView(form.EditForm, PersonForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/person_add.pt')

    def update(self):
        self.fields = field.Fields(IBasicPerson) + field.Fields(IStudent)
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
        groups = IGroupContainer(ISchoolToolApplication(None))
        self.title = groups[value].title
        self.token = value
        self.value = value


class GroupTerms(TermsBase):
    """Displaying groups."""

    factory = GroupTerm
