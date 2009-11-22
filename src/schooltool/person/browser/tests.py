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
Tests for Person views.
"""
import unittest

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import setup
from zope.traversing.interfaces import IContainmentRoot
from zope.component import provideAdapter

from schooltool.group.interfaces import IGroupContainer
from schooltool.app.browser.testing import setUp, tearDown
from schooltool.testing import setup as sbsetup

def doctest_PersonContainerView():
    r"""Test for PersonContainerView

    Let's create some persons to delete from a person container:

        >>> from schooltool.person.browser.person import \
        ...     PersonContainerView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')

        >>> request = TestRequest()
        >>> view = PersonContainerView(personContainer, request)

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


def doctest_PersonPhotoView():
    r"""Test for PersonPhotoView

    We will need a person that has a photo:

        >>> from schooltool.person.person import Person
        >>> person = Person()
        >>> person.photo = "I am a photo!"

    We can now create a view:

        >>> from schooltool.person.browser.person import PersonPhotoView
        >>> request = TestRequest()
        >>> view = PersonPhotoView(person, request)

    The view returns the photo and sets the appropriate Content-Type header:

        >>> view()
        'I am a photo!'
        >>> request.response.getHeader("Content-Type")
        'image/jpeg'

    However, if a person has no photo, the view raises a NotFound error.

        >>> person.photo = None
        >>> view()                                  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        NotFound: Object: <...Person object at ...>, name: u'photo'

    """


def doctest_PersonEditView():
    r"""Test for PersonEditView

    PersonEditView is a view on IPerson.

        >>> from schooltool.person.browser.person import PersonEditView
        >>> from schooltool.person.person import Person
        >>> person = Person()

    Let's try creating one

        >>> request = TestRequest()
        >>> view = PersonEditView(person, request)

    You can change person's title and photo

        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.title': u'newTitle',
        ...                             'field.photo': 'PHOTO'})
        >>> view = PersonEditView(person, request)

        >>> view.update()
        >>> view.message
        >>> person.title
        u'newTitle'
        >>> person.photo
        'PHOTO'

    You can clear the person's photo:
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.title':u'newTitle',
        ...                             'field.clear_photo':'on'})
        >>> view = PersonEditView(person, request)

        >>> view.update()
        >>> view.message
        >>> person.title
        u'newTitle'
        >>> print person.photo
        None

    You can set a person's password

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.title': person.title,
        ...                             'field.new_password': 'bar',
        ...                             'field.verify_password': 'bar'})
        >>> view = PersonEditView(person, request)

        >>> view.update()
        >>> view.message
        u'Password was successfully changed!'
        >>> person.checkPassword('bar')
        True

    Unless new password and confirm password do not match

        >>> person.setPassword('lala')
        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.title': person.title,
        ...                             'field.new_password': 'bara',
        ...                             'field.verify_password': 'bar'})
        >>> view = PersonEditView(person, request)

        >>> view.update()
        >>> view.error
        u'Passwords do not match.'

    If the form contains errors, it is redisplayed

        >>> request = TestRequest(form={'UPDATE_SUBMIT': True,
        ...                             'field.title': '',
        ...                             'field.new_password': 'xyzzy',
        ...                             'field.verify_password': 'xyzzy'})
        >>> view = PersonEditView(person, request)

        >>> view.update()
        >>> person.title
        u'newTitle'

        >>> bool(view.title_widget.error())
        True

    We can cancel an action if we want to:

        >>> directlyProvides(person, IContainmentRoot)
        >>> request = TestRequest()
        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = PersonEditView(person, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    """


def doctest_PersonAddView():
    r"""Test for PersonAddView

    Make sure we have the PersonFactory utility available:

        >>> from zope.component import provideUtility
        >>> from schooltool.person.utility import PersonFactoryUtility
        >>> from schooltool.person.interfaces import IPersonFactory
        >>> provideUtility(PersonFactoryUtility(), IPersonFactory)

    We need some setup to make traversal work in a unit test.

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self): return "http://localhost/frogpond/persons"
        ...
        >>> from schooltool.person.interfaces import IPersonContainer
        >>> from zope.traversing.browser.interfaces import IAbsoluteURL
        >>> provideAdapter(FakeURL, (IPersonContainer,), IAbsoluteURL)

    Let's create a PersonContainer

        >>> app = sbsetup.setUpSchoolToolSite()
        >>> pc = app['persons']

        >>> from zope.component import provideAdapter
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(lambda context: app,
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

    And a group container:

        >>> from schooltool.group.group import GroupContainer
        >>> gc = GroupContainer()
        >>> provideAdapter(lambda context: gc,
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

    Now let's create a PersonAddView for the container

        >>> from schooltool.person.browser.person import PersonAddView
        >>> view = PersonAddView(pc, TestRequest())
        >>> view.update()

    Let's try to add a user:

        >>> request = TestRequest(form={'field.title': u'John Doe',
        ...                             'field.username': u'jdoe',
        ...                             'field.password': u'secret',
        ...                             'field.verify_password': u'secret',
        ...                             'field.photo': u'',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        ''
        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> 'jdoe' in pc
        True
        >>> person = pc['jdoe']
        >>> person.title
        u'John Doe'
        >>> person.username
        u'jdoe'
        >>> person.checkPassword('secret')
        True
        >>> person.photo is None
        True

    If we try to add a user with the same login, we get a nice error message:

        >>> request = TestRequest(form={'field.title': u'Another John Doe',
        ...                             'field.username': u'jdoe',
        ...                             'field.password': u'pass',
        ...                             'field.verify_password': u'pass',
        ...                             'field.photo': None,
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.error
        u'This username is already used!'

    Let's try to add user with different password and verify_password fields:

        >>> request = TestRequest(form={'field.title': u'Coo Guy',
        ...                             'field.username': u'coo',
        ...                             'field.password': u'secret',
        ...                             'field.verify_password': u'plain',
        ...                             'field.photo': None,
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        u'An error occurred.'
        >>> view.error
        u'Passwords do not match!'
        >>> 'coo' in pc
        False

    We can select groups that the user should be in.  First, let's create a
    group:

        >>> from schooltool.group.group import Group
        >>> pov = IGroupContainer(app)['pov'] = Group('PoV')

    Now, let's create and render a view:

        >>> request = TestRequest(form={'field.title': u'Gintas',
        ...                             'field.username': u'gintas',
        ...                             'field.password': u'denied',
        ...                             'field.verify_password': u'denied',
        ...                             'field.photo': ':)',
        ...                             'group.pov': 'on',
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        ''
        >>> print view.errors
        ()
        >>> print view.error
        None

        >>> pc['gintas'].photo
        ':)'

    Now the person belongs to the group that we have selected:

        >>> list(pc['gintas'].groups) == [pov]
        True

    We can cancel an action if we want to:

        >>> directlyProvides(pc, IContainmentRoot)
        >>> request = TestRequest()
        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = PersonAddView(pc, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons'

    """


def doctest_PersonPreferencesView():
    """

        >>> from schooltool.person.browser.person import PersonPreferencesView
        >>> from schooltool.person.person import Person
        >>> from schooltool.person.preference import PersonPreferences
        >>> from zope.traversing.interfaces import IContainmentRoot

        >>> person = Person()
        >>> directlyProvides(person, IContainmentRoot)
        >>> prefs = PersonPreferences()
        >>> prefs.__parent__ = person
        >>> request = TestRequest()

        >>> view = PersonPreferencesView(prefs, request)
        >>> view.update()

    Cancel a change: (TODO: set view.message)

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> view = PersonPreferencesView(prefs, request)
        >>> view.update()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    Let's see if posting works properly:

        >>> request = TestRequest(form={'UPDATE_SUBMIT': 'Update',
        ...                             'field.cal_periods': 'off',
        ...                             'field.cal_public': 'on'})
        >>> view = PersonPreferencesView(prefs, request)

        >>> view.update()

        >>> print prefs.cal_public, prefs.cal_periods
        True False
    """


def doctest_PersonCSVImporter():
    r"""Tests for PersonCSVImporter.

    Make sure we have the PersonFactory utility available:

        >>> from zope.component import provideUtility
        >>> from schooltool.person.utility import PersonFactoryUtility
        >>> from schooltool.person.interfaces import IPersonFactory
        >>> provideUtility(PersonFactoryUtility(), IPersonFactory)

    Create a person container and an importer


        >>> from schooltool.person.browser.csvimport import \
        ...     PersonCSVImporter
        >>> from schooltool.person.person import PersonContainer
        >>> container = PersonContainer()
        >>> importer = PersonCSVImporter(container, None)

    Import a user and verify that it worked

        >>> importer.createAndAdd([u'joe', u'Joe Smith'], False)
        >>> [p for p in container]
        [u'joe']

    Import a user with a password and verify it

        >>> importer.createAndAdd([u'jdoe', u'John Doe', u'monkey'], False)
        >>> container['jdoe'].checkPassword('monkey')
        True

    Some basic data validation exists.  Note that the errors are cumulative
    between calls on an instance.

        >>> importer.createAndAdd([], False)
        >>> importer.errors.fields
        [u'Insufficient data provided.']
        >>> importer.createAndAdd([u'', u'Jim Smith'], False)
        >>> importer.errors.fields
        [u'Insufficient data provided.', u'username may not be empty']
        >>> importer.createAndAdd([u'user', u''], False)
        >>> importer.errors.fields
        [u'Insufficient data provided.', u'username may not be empty', u'fullname may not be empty']

    Let's clear the errors and review the contents of the container

        >>> importer.errors.fields = []
        >>> [p for p in container]
        [u'jdoe', u'joe']

    Now we'll try to add another 'jdoe' username.  In this case the error
    message contains a translated variable, so we need zope.i18n.translate to
    properly demonstrate it.

        >>> from zope.i18n import translate
        >>> importer.createAndAdd([u'jdoe', u'Jim Doe'], False)
        >>> [translate(error) for error in importer.errors.fields]
        [u'Duplicate username: jdoe, Jim Doe']
        >>> importer.errors.fields = []
        >>> importer.createAndAdd([u'@@index.html', u'Jim Doe'], False)
        >>> [translate(error) for error in importer.errors.fields]
        [u"Names cannot begin with '+' or '@' or contain '/'"]

    """


def doctest_PersonFilterWidget():
    """Doctest for PersonFilterWidget.

    For this test we will need a catalog with an index for person
    titles:

        >>> from zope.app.catalog.interfaces import ICatalog
        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}
        >>> title_index = IndexStub()
        >>> username_index = IndexStub()

        >>> class CatalogStub(dict):
        ...     def __init__(self):
        ...         self['title'] = title_index
        ...         self['__name__'] = username_index
        >>> catalog = CatalogStub()

   Some persons:

        >>> class PersonStub(object):
        ...     def __init__(self, title, groups, person_id):
        ...         self.id = person_id
        ...         self.title = title
        ...         self.__name__ = title
        ...         for group in groups:
        ...             group.add(self)
        ...     def __repr__(self):
        ...         return '<ItemStub %s>' % self.title

   Some groups:

        >>> class GroupStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.members = []
        ...     def add(self, member):
        ...         self.members.append(member)
        >>> a = GroupStub('a')
        >>> b = GroupStub('b')
        >>> c = GroupStub('c')

   Container with some persons in it:

        >>> class ContainerStub(dict):
        ...     def __init__(self):
        ...         persons = [('a1234','alpha', [a]),
        ...                    ('a1235','beta', [b, c]),
        ...                    ('a1236','lambda', [b])]
        ...         for id, (username, title, groups) in enumerate(persons):
        ...             self[username] = PersonStub(title, groups, id)
        ...             title_index.documents_to_values[id] = title
        ...             username_index.documents_to_values[id] = username
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return catalog

    Let's create the PersonFilterWidget:

        >>> from zope.publisher.browser import TestRequest
        >>> from schooltool.person.browser.person import PersonFilterWidget
        >>> container = ContainerStub()
        >>> request = TestRequest()
        >>> widget = PersonFilterWidget(container, request)

    The state of the widget (whether it will filter the data or not)
    is determined by checking whether there is at least one query
    parameter in the request:

        >>> widget.active()
        False

        >>> request.form = {'SEARCH_TITLE': 'lamb'}
        >>> widget.active()
        True

        >>> request.form = {'SEARCH_GROUP': 'lamb'}
        >>> widget.active()
        True

    The information that we got from the request can be appended to
    the url:

        >>> widget.extra_url()
        '&SEARCH_GROUP=lamb'

        >>> request.form = {'SEARCH_TITLE': 'lamb', 'SEARCH_GROUP': 'a'}
        >>> widget.extra_url()
        '&SEARCH_TITLE=lamb&SEARCH_GROUP=a'

    Filtering is done by skipping any entry that doesn't contain the
    query string in it's title, or are not in the target group:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from zope.component import adapts
        >>> from zope.interface import implements, Interface
        >>> class StubApplication(dict):
        ...     implements(ISchoolToolApplication)
        ...     adapts(Interface)
        ...     def __init__(self, context):
        ...         self['groups'] = {'a': a, 'b': b, 'c': c}
        >>> from zope.component import provideAdapter
        >>> provideAdapter(StubApplication)
        >>> from schooltool.group.interfaces import IGroupContainer
        >>> provideAdapter(lambda app: app['groups'],
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> items = [{'id': 0},
        ...          {'id': 1},
        ...          {'id': 2}]

        >>> request.form = {'SEARCH_TITLE': 'lamb'}
        >>> widget.filter(items)
        [{'id': 2}]

        >>> from zope.component import provideUtility
        >>> from zope.app.intid.interfaces import IIntIds
        >>> class IntIdsStub(object):
        ...     def queryId(self, obj):
        ...         return obj.id
        >>> provideUtility(IntIdsStub(), IIntIds)

        >>> request.form = {'SEARCH_GROUP': 'b'}
        >>> widget.filter(items)
        [{'id': 1}, {'id': 2}]

        >>> request.form = {'SEARCH_GROUP': 'b',
        ...                 'SEARCH_TITLE': 'bet'}
        >>> widget.filter(items)
        [{'id': 1}]

   The search is case insensitive:

        >>> request.form = {'SEARCH_TITLE': 'AlphA'}
        >>> widget.filter(items)
        [{'id': 0}]

   The search also searches through usernames:

        >>> request.form = {'SEARCH_TITLE': '1234'}
        >>> widget.filter(items)
        [{'id': 0}]

    If clear search button is clicked, the form attribute is cleared,
    and all items are displayed:

        >>> request.form['CLEAR_SEARCH'] = 'Yes'

        >>> widget.filter(items)
        [{'id': 0}, {'id': 1}, {'id': 2}]
        >>> request.form['SEARCH_TITLE']
        ''

        >>> request.form['SEARCH_GROUP']
        ''

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
