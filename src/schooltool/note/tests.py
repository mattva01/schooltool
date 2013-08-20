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
Unit tests for schooltool.note
"""
import unittest
import doctest

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import TestRequest
from zope.component import provideAdapter

from zope.app.testing import setup

from schooltool.app.browser.testing import setUp, tearDown


def doctest_getNotes():
    r"""Test for schooltool.note.note.getNotes.

    We need to set up Zope 3 annotations

        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

    We need to have an annotatable object

        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> class SomeAnnotatable(object):
        ...     implements(IAttributeAnnotatable)

        >>> obj = SomeAnnotatable()

    Now we can check that a new Notes object is created automatically

        >>> from schooltool.note.note import getNotes
        >>> notes = getNotes(obj)

        >>> from schooltool.note.interfaces import INotes
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(INotes, notes)
        True

    If you do it more than once, you will get the same Notes object

        >>> notes is getNotes(obj)
        True

    """

def doctest_browser_NoteAddView():
    r"""Test for NoteAddView

    We need some setup to make traversal work in a unit test.

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self):
        ...         return "http://127.0.0.1/frogpond/persons/milton"
        >>> from schooltool.note.interfaces import IHaveNotes, INotes
        >>> from zope.traversing.browser.interfaces import IAbsoluteURL
        >>> provideAdapter(FakeURL,
        ...                provides=IAbsoluteURL,
        ...                adapts=(IHaveNotes, IBrowserRequest))

    Let's create an owner for our note.  We need an id for our person to test
    the AddView later on:

        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> class Owner(object):
        ...     implements(IAttributeAnnotatable, IHaveNotes)
        ...     id = None

        >>> owner = Owner()
        >>> owner.id = 'someone'

    Now let's create a NoteAddView for the owner

        >>> from schooltool.note.browser import NoteAddView
        >>> view = NoteAddView(owner, TestRequest())
        >>> view.update()

    We need to set up an adapter for notes

        >>> setup.setUpAnnotations()
        >>> from schooltool.note.note import getNotes
        >>> provideAdapter(getNotes, adapts=[IHaveNotes], provides=INotes)

    Let's try to add a note:

        >>> request = TestRequest(form={'field.title': u'Red Stapler',
        ...                             'field.body': u"He won't give it back",
        ...                             'field.privacy': u"public",
        ...                             'UPDATE_SUBMIT': 'Add'})
        >>> request.setPrincipal(owner)
        >>> view = NoteAddView(owner, request)
        >>> view.update()
        ''
        >>> print view.errors
        ()
        >>> print view.error
        None
        >>> notes = INotes(owner)
        >>> print [note.title for note in notes.__iter__()]
        [u'Red Stapler']

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS|
                             doctest.REPORT_NDIFF),
        doctest.DocTestSuite('schooltool.note.note'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
