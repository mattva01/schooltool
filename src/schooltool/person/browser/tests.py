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

$Id: test_app.py 4637 2005-08-09 17:29:12Z srichter $
"""
import unittest

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import setup, ztapi
from zope.app.traversing.interfaces import IContainmentRoot

from schoolbell.app.browser.tests.setup import setUp, tearDown
from schooltool.testing import setup as sbsetup

def doctest_PersonContainerDeleteView():
    r"""Test for PersonContainerDeleteView

    Let's create some persons to delete from a person container:

        >>> from schooltool.person.browser.person import \
        ...     PersonContainerDeleteView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> from schooltool.person.interfaces import IPerson
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')
        >>> request = TestRequest()
        >>> view = PersonContainerDeleteView(personContainer, request)

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


def doctest_PersonView():
    r"""Test for PersonView

    Let's create a view for a person:

        >>> from schooltool.person.browser.person import PersonView
        >>> from schooltool.person.person import Person
        >>> from schooltool.person.details import getPersonDetails
        >>> from schooltool.person.interfaces import IPersonDetails
        >>> from schooltool.person.interfaces import IPerson
        >>> setup.setUpAnnotations()
        >>> ztapi.provideAdapter(IPerson, IPersonDetails, getPersonDetails)
        >>> person = Person()
        >>> request = TestRequest()
        >>> view = PersonView(person, request)

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
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1'

    """


def doctest_PersonAddView():
    r"""Test for PersonAddView

    We need some setup to make traversal work in a unit test.

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self): return "http://localhost/frogpond/persons"
        ...
        >>> from schooltool.person.interfaces import IPersonContainer
        >>> from zope.app.traversing.browser.interfaces import IAbsoluteURL
        >>> ztapi.browserViewProviding(IPersonContainer, FakeURL, \
        ...                            providing=IAbsoluteURL)

    Let's create a PersonContainer

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> app = sbsetup.setupSchoolBellSite()
        >>> pc = app['persons']

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
        u'An error occured.'
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
        u'An error occured.'
        >>> view.error
        u'Passwords do not match!'
        >>> 'coo' in pc
        False

    We can select groups that the user should be in.  First, let's create a
    group:

        >>> from schooltool.group.group import Group
        >>> pov = app['groups']['pov'] = Group('PoV')

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
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/persons'

    """

def doctest_PersonPreferencesView():
    """

        >>> from schooltool.person.browser.person import \\
        ...     PersonPreferencesView
        >>> from schooltool.person.person import Person
        >>> from schooltool.person.preference import getPersonPreferences
        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.person.interfaces import IPersonPreferences

        >>> setup.setUpAnnotations()

        # Usually registered for IHavePreferences
        >>> ztapi.provideAdapter(IPerson, IPersonPreferences,
        ...                      getPersonPreferences)

        >>> person = Person()
        >>> request = TestRequest()

        >>> view = PersonPreferencesView(person, request)

    Cancel a change TODO: set view.message

        >>> request = TestRequest(form={'CANCEL': 'Cancel'})
        >>> view = PersonPreferencesView(person, request)

    Let's see if posting works properly:

        >>> request = TestRequest(form={'UPDATE_SUBMIT': 'Update',
        ...                             'field.timezone': 'Europe/Vilnius',
        ...                             'field.timeformat': '%H:%M',
        ...                             'field.dateformat': '%d %B, %Y',
        ...                             'field.weekstart': '6',
        ...                             'field.cal_periods': True})
        >>> view = PersonPreferencesView(person, request)

        >>> view.update()

        >>> prefs = getPersonPreferences(person)
        >>> prefs.timezone, prefs.timeformat, prefs.dateformat, prefs.weekstart
        ('Europe/Vilnius', '%H:%M', '%d %B, %Y', 6)

    """


def doctest_PersonDetailsView():
    """

        >>> from schooltool.person.browser.person import PersonDetailsView
        >>> from schooltool.person.person import Person
        >>> from schooltool.person.details import getPersonDetails
        >>> from schooltool.person.interfaces import IPersonDetails
        >>> from schooltool.person.interfaces import IPerson

        >>> setup.setUpAnnotations()
        >>> ztapi.provideAdapter(IPerson, IPersonDetails, \
                                 getPersonDetails)

        >>> person = Person()
        >>> request = TestRequest()

        >>> view = PersonDetailsView(person, request)

    Cancel a change TODO: set view.message

        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = PersonDetailsView(person, request)

    """


def doctest_PersonCSVImporter():
    r"""Tests for PersonCSVImporter.

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

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
