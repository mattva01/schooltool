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
Tests for schoolbell note views.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app.testing import setup, ztapi
from zope.publisher.browser import TestRequest

from schoolbell.app.browser.tests.setup import setUp, tearDown


def doctest_NoteAddView():
    r"""Test for NoteAddView

    We need some setup to make traversal work in a unit test.

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self):
        ...         return "http://localhost/frogpond/persons/milton"
        >>> from schoolbell.app.interfaces import IHaveNotes, INotes
        >>> from zope.app.traversing.browser.interfaces import IAbsoluteURL
        >>> ztapi.browserViewProviding(IHaveNotes, FakeURL, \
        ...                            providing=IAbsoluteURL)

    Let's create a Person for our note.  We need an id for our person to test
    the AddView later on:

        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> person.id = 'someone'

    Now let's create a NoteAddView for the person

        >>> from schoolbell.app.browser.notes import NoteAddView
        >>> view = NoteAddView(person, TestRequest())
        >>> view.update()

    We need to set up an adapter for notes

        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> setup.setUpAnnotations()
        >>> from schoolbell.app.interfaces import IHaveNotes, INotes
        >>> from schoolbell.app.notes import getNotes
        >>> ztapi.provideAdapter(IHaveNotes, INotes, getNotes)

    Let's try to add a note:

        >>> request = TestRequest(form={'field.title': u'Red Stapler',
        ...                             'field.body': u"He won't give it back",
        ...                             'field.privacy': u"public",
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> request.setPrincipal(person)
        >>> view = NoteAddView(person, request)
        >>> view.update()
        ''
        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> notes = INotes(person)
        >>> print [note.title for note in notes.__iter__()]
        [u'Red Stapler']

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

