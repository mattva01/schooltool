#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Unit tests for basic person views.
"""
import unittest
import doctest

from z3c.form.testing import TestRequest
from zope.app.testing import setup
from zope.app.testing.setup import setUpAnnotations
from zope.component import provideAdapter
from zope.interface import directlyProvides
from zope.interface import implements
from zope.schema.vocabulary import getVocabularyRegistry
from zope.traversing.interfaces import IContainmentRoot

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.group.interfaces import IGroupContainer
from schooltool.relationship.tests import setUpRelationships


def doctest_PersonContainerView():
    r"""Test for PersonContainerView

    Let's create some persons to delete from a person container:

        >>> from schooltool.basicperson.browser.person import \
        ...     BasicPersonContainerView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')

        >>> request = TestRequest()
        >>> view = BasicPersonContainerView(personContainer, request)

    Our user is not trying to delete anything yet:

        >>> view.isDeletingHimself()
        False

    Lets log in:

        >>> from schooltool.app.security import Principal
        >>> principal = Principal('pete', 'Pete Parrot', personContainer['pete'])
        >>> request.setPrincipal(principal)

    Even if he is trying to delete someone who is not pete:

        >>> request.form = {'delete.frog': 'on',
        ...                 'delete.toad': 'on'}
        >>> view.isDeletingHimself()
        False

    But if he will try deleting himself - the method should return true:

        >>> request.form = {'delete.pete': 'on',
        ...                 'delete.toad': 'on'}
        >>> view.isDeletingHimself()
        True

    """


def doctest_PersonAddFormAdapter():
    """Tests for PersonAddFormAdapter

    PersonAddFormAdapter just wraps a person object but hides
    setPassword method unde a write only password property:

        >>> class PersonStub(object):
        ...     def setPassword(self, new_password):
        ...         print "Setting password to:", new_password

        >>> person = PersonStub()
        >>> person.name = "John"
        >>> person.last_name = "Johnson"

        >>> from schooltool.basicperson.browser.person import PersonAddFormAdapter
        >>> pa = PersonAddFormAdapter(person)
        >>> pa.password = "FooBar3"
        Setting password to: FooBar3

        >>> pa.password is None
        True

        >>> pa.name
        'John'

        >>> pa.surname = "Peterson"
        >>> person.surname
        'Peterson'

    """


class AppStub(dict):
    implements(ISchoolToolApplication)


def doctest_PersonAddView():
    r"""Test for PersonAddView

    Make sure we have the PersonFactory utility available:

        >>> from zope.component import provideUtility
        >>> from schooltool.basicperson.person import PersonFactoryUtility
        >>> from schooltool.person.interfaces import IPersonFactory
        >>> provideUtility(PersonFactoryUtility(), IPersonFactory)

    We need some setup to make traversal work in a unit test.

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self): return "http://127.0.0.1/frogpond/persons"
        ...
        >>> from schooltool.person.interfaces import IPersonContainer
        >>> from zope.traversing.browser.interfaces import IAbsoluteURL
        >>> provideAdapter(FakeURL, (IPersonContainer, TestRequest), IAbsoluteURL)

        >>> app = AppStub()
        >>> from zope.component import provideAdapter
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(lambda context: app,
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

    Let's create a PersonContainer

        >>> from schooltool.person.person import PersonContainer
        >>> pc = PersonContainer()

    And a group container:

        >>> from schooltool.group.group import GroupContainer
        >>> gc = GroupContainer()
        >>> provideAdapter(lambda context: gc,
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> from schooltool.basicperson.interfaces import IDemographicsFields
        >>> from schooltool.basicperson.demographics import DemographicsFields
        >>> df = DemographicsFields()
        >>> provideAdapter(lambda context: df,
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IDemographicsFields)

    Now let's create a PersonAddView for the container

        >>> from schooltool.basicperson.browser.person import PersonAddFormAdapter
        >>> provideAdapter(PersonAddFormAdapter)
        >>> from schooltool.basicperson.browser.person import UsernameValidator
        >>> provideAdapter(UsernameValidator)
        >>> from schooltool.basicperson.browser.person import PasswordValidator
        >>> provideAdapter(PasswordValidator)

        >>> from schooltool.basicperson.browser.person import PersonAddView
        >>> view = PersonAddView(pc, TestRequest())
        >>> view.update()

    Let's try to add a user:

        >>> request = TestRequest(form={'form.widgets.first_name': u'John',
        ...                             'form.widgets.last_name': u'Doe',
        ...                             'form.widgets.username': u'jdoe',
        ...                             'form.widgets.password': u'secret',
        ...                             'form.widgets.confirm': u'secret',
        ...                             'form.buttons.add': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        >>> view.widgets.errors
        ()
        >>> 'jdoe' in pc
        True
        >>> person = pc['jdoe']
        >>> person.title
        u'John Doe'
        >>> person.username
        u'jdoe'
        >>> person.checkPassword('secret')
        True

    If we try to add a user with the same login, we get a nice error message:

        >>> request = TestRequest(form={'form.widgets.first_name': u'Another John',
        ...                             'form.widgets.last_name': u'Doe',
        ...                             'form.widgets.username': u'jdoe',
        ...                             'form.widgets.password': u'pass',
        ...                             'form.widgets.confirm': u'pass',
        ...                             'form.buttons.add': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        >>> for error in view.widgets.errors: print error.message
        This username is already in use

    Let's try to add user with different password and confirm password fields:

        >>> request = TestRequest(form={'form.widgets.first_name': u'Coo',
        ...                             'form.widgets.last_name': u'Guy',
        ...                             'form.widgets.username': u'coo',
        ...                             'form.widgets.password': u'secret',
        ...                             'form.widgets.confirm': u'plain',
        ...                             'form.buttons.add': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        >>> for error in view.widgets.errors: print error.message
        Passwords do not match
        >>> 'coo' in pc
        False

    We can select groups that the user should be in.  First, let's create a
    group:

        >>> from schooltool.group.group import Group
        >>> pov = IGroupContainer(app)['pov'] = Group('PoV')

    Now, let's create and render a view:

        >>> request = TestRequest(form={'form.widgets.first_name': u'Gintas',
        ...                             'form.widgets.last_name': u'Mil',
        ...                             'form.widgets.username': u'gintas',
        ...                             'form.widgets.password': u'denied',
        ...                             'form.widgets.confirm': u'denied',
        ...                             'form.widgets.group': ['pov'],
        ...                             'form.buttons.add': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        >>> view.widgets.errors
        ()

    Now the person belongs to the group that we have selected:

        >>> list(pc['gintas'].groups) == [pov]
        True

    We can cancel an action if we want to:

        >>> request = TestRequest(form={'form.buttons.cancel': 'Cancel'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/frogpond/persons'

    """


def doctest_PersonTerm():
    """Tests for PersonTerm.

    Person term is a title tokenized term that uses the title of a
    person as the title to be displayed:

        >>> class PersonStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.__name__ = title.lower()

        >>> john = PersonStub('John')

        >>> from schooltool.basicperson.browser.person import PersonTerm
        >>> term = PersonTerm(john)
        >>> term.title
        'John'
        >>> term.token
        'john'
        >>> term.value
        <...test_person.PersonStub object at ...>

    """


def doctest_TermsBase():
    """Tests for TermsBase.

    Let's construct the TermsBase:

        >>> class TermStub(object):
        ...     def __init__(self, value):
        ...         self.value = value
        ...     def __repr__(self):
        ...         return "<TermStub %s>" % self.value

        >>> from schooltool.basicperson.browser.person import TermsBase
        >>> source = ["john"]
        >>> terms = TermsBase(source, None)

    If no term factory is set - NotImplementedError is raised:

        >>> terms.getTerm("john")
        Traceback (most recent call last):
        ...
        NotImplementedError: Term Factory must be provided by inheriting classes.

    If term factory is present it is used to construct the term from
    the given value:

        >>> terms.factory = TermStub

        >>> terms.getTerm("john")
        <TermStub john>

    If there is no such value in the source - we get a lookup error:

        >>> terms.getTerm("peter")
        Traceback (most recent call last):
        ...
        LookupError: peter

    """


def doctest_GroupTerm():
    """Tests for GroupTerm.

    Group term is a title tokenized term that uses the title of a
    group as the title to be displayed:

        >>> class GroupStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.__name__ = title

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> class STAppStub(dict):
        ...     implements(ISchoolToolApplication)
        ...     def __init__(self, context):
        ...         self['groups'] = {'teachers': GroupStub('Teachers')}

        >>> provideAdapter(STAppStub, adapts=[None])
        >>> from schooltool.group.interfaces import IGroupContainer
        >>> provideAdapter(lambda app: app['groups'], adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> from schooltool.basicperson.browser.person import GroupTerm
        >>> term = GroupTerm(GroupStub("teachers"))
        >>> term.title
        'teachers'
        >>> term.token
        'teachers'
        >>> term.value
        <schooltool.basicperson.browser.tests.test_person.GroupStub object at ...>

    """


def setUp(test):
    setup.placelessSetUp()
    from z3c.form import testing
    testing.setupFormDefaults()
    vr = getVocabularyRegistry()
    from schooltool.basicperson.vocabularies import groupVocabularyFactory
    from schooltool.basicperson.vocabularies import advisorVocabularyFactory
    vr.register('schooltool.basicperson.group_vocabulary',
                groupVocabularyFactory())
    vr.register('schooltool.basicperson.advisor_vocabulary',
                advisorVocabularyFactory())
    setUpRelationships()
    setUpAnnotations()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
