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
Lyceum person browser views.

$Id$
"""
from zope.app import zapi
from zope.app.container.interfaces import INameChooser
from zope.app.form.browser.interfaces import ITerms
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getUtility
from zope.exceptions.interfaces import UserError
from zope.formlib import form
from zope.interface import implements
from zope.publisher.browser import BrowserView
from zope.schema import Password
from zope.schema import TextLine
from zope.schema.interfaces import ITitledTokenizedTerm

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPersonFactory
from schooltool.skin.form import BasicForm
from schooltool.skin.form import EditForm
from schooltool.widget.password import PasswordConfirmationWidget

from lyceum.person.interfaces import ILyceumPerson
from lyceum import LyceumMessage as _


class PersonView(BrowserView):

    template = ViewPageTemplateFile('templates/person_view.pt')

    def __call__(self):
        return self.template()


class IPersonAddForm(ILyceumPerson):

    password = Password(
        title=_("Password"),
        required=False)

    username = TextLine(
        title=_("Username"),
        description=_("Username"),
        required=True)


class PersonAddFormAdapter(object):
    implements(IPersonAddForm)
    adapts(ILyceumPerson)

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


class PersonAddView(BasicForm):
    """Person add form for lyceum persons."""

    template = ViewPageTemplateFile('templates/person_add.pt')

    form_fields = form.Fields(IPersonAddForm, render_context=False)
    form_fields['password'].custom_widget = PasswordConfirmationWidget

    @form.action(_("Apply"))
    def handle_apply_action(self, action, data):
        if data['username'] in self.context:
            self.status = _("This username is already used!")
            return None

        try:
            INameChooser(self.context).checkName(data['username'], None)
        except UserError:
            self.status = _("Names cannot begin with '+' or '@' or contain '/'")
            return None

        person = self._factory(data['username'], data['first_name'],
                               data['last_name'])

        form.applyChanges(person, self.form_fields, data, self.adapters)
        self.addPerson(person)

        # Add the persons to his class
        if person.gradeclass is not None:
            groups = ISchoolToolApplication(None)['groups']
            person.groups.add(groups[person.gradeclass])

        url = zapi.absoluteURL(person, self.request)
        self.request.response.redirect(url)
        return ''

    @form.action(_("Cancel"))
    def handle_cancel_action(self, action, data):
        # XXX validation upon cancellation doesn't make any sense
        # how to make this work properly?
        return self._redirect()

    def _redirect(self):
        url = zapi.absoluteURL(self.context, self.request)
        self.request.response.redirect(url)
        return ''

    @property
    def _factory(self):
        return getUtility(IPersonFactory)

    def addPerson(self, person):
        """Add `person` to the container.

        Uses the username of `person` as the object ID (__name__).
        """
        name = person.username
        self.context[name] = person
        return person


class PersonEditView(EditForm):
    """Edit form for lyceum person."""

    template = ViewPageTemplateFile('templates/person_edit.pt')

    @form.action(_('Apply'), name='apply')
    def handle_apply(self, action, data):
        self.edit_action(action, data)

    @form.action(_('Cancel'), name='cancel')
    def handle_cancel(self, action, data):
        self.cancel_action(action, data)

    def title(self):
        return _(u'Change information for ${fullname}',
                 mapping={'fullname': self.fullname()})

    form_fields = form.Fields(ILyceumPerson)

    def fullname(self):
        return self.context.title


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
        groups = ISchoolToolApplication(None)['groups']
        self.title = groups[value].title
        self.token = value
        self.value = value


class GroupTerms(TermsBase):
    """Displaying groups."""

    factory = GroupTerm
