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

$Id$
"""
import unittest

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import setup, ztapi
from zope.traversing.interfaces import IContainmentRoot

from schooltool.app.browser.testing import setUp, tearDown
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
        ...                             'field.timezone': 'Europe/Vilnius',
        ...                             'field.timeformat': '%H:%M',
        ...                             'field.dateformat': '%d %B, %Y',
        ...                             'field.weekstart': '6',
        ...                             'field.cal_periods': True})
        >>> view = PersonPreferencesView(prefs, request)

        >>> view.update()

        >>> prefs.timezone, prefs.timeformat, prefs.dateformat, prefs.weekstart
        ('Europe/Vilnius', '%H:%M', '%d %B, %Y', 6)

    """


def doctest_PersonCSVImporter():
    r"""Tests for PersonCSVImporter.

    Make sure we have the PersonFactory utility available:
    
        >>> from zope.component import provideUtility
        >>> from schooltool.person.utility import PersonFactory
        >>> from schooltool.person.interfaces import IPersonFactory
        >>> provideUtility(PersonFactory(), IPersonFactory)
        
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
