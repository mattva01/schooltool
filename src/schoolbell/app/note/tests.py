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
Unit tests for schoolbell.app.note

$Id$
"""
import unittest

from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.testing import doctest

from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.tests import setup, ztapi

from schoolbell.app.browser.tests.setup import setUp, tearDown


def doctest_getNotes():
    r"""Test for schoolbell.app.annotatable.getNotes.

    We need to set up Zope 3 annotations

        >>> from zope.app.tests import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

    We need to have an annotatable object

        >>> from zope.interface import implements
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> class SomeAnnotatable(object):
        ...     implements(IAttributeAnnotatable)

        >>> obj = SomeAnnotatable()

    Now we can check that a new Notes object is created automatically

        >>> from schoolbell.app.note.note import getNotes
        >>> notes = getNotes(obj)

        >>> from schoolbell.app.note.interfaces import INotes
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
        ...         return "http://localhost/frogpond/persons/milton"
        >>> from schoolbell.app.note.interfaces import IHaveNotes, INotes
        >>> from zope.app.traversing.browser.interfaces import IAbsoluteURL
        >>> ztapi.browserViewProviding(IHaveNotes, FakeURL, \
        ...                            providing=IAbsoluteURL)

    Let's create an owner for our note.  We need an id for our person to test
    the AddView later on:

        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> class Owner(object):
        ...     implements(IAttributeAnnotatable, IHaveNotes)
        ...     id = None
        
        >>> owner = Owner()
        >>> owner.id = 'someone'

    Now let's create a NoteAddView for the owner

        >>> from schoolbell.app.note.browser import NoteAddView
        >>> view = NoteAddView(owner, TestRequest())
        >>> view.update()

    We need to set up an adapter for notes

        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> setup.setUpAnnotations()
        >>> from schoolbell.app.note.note import getNotes
        >>> ztapi.provideAdapter(IHaveNotes, INotes, getNotes)

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


def doctest_rest_views():
    r"""Tests for NotesView.

    First we need a bit of standard set up:

        >>> from zope.app.testing import ztapi
        >>> from zope.publisher.browser import TestRequest
        >>> from StringIO import StringIO

        >>> from schoolbell.app.note.rest import NotesViewFactory
        >>> from schoolbell.app.note.rest import NotesTraverser
        >>> from schoolbell.app.note.rest import NotesView

        >>> from schoolbell.app.note.note import getNotes
        >>> from schoolbell.app.note.interfaces import INotes
        >>> from schoolbell.app.note.interfaces import IHaveNotes
        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> setup.setUpAnnotations()
        >>> setup.placefulSetUp()
        >>> ztapi.provideAdapter(IHaveNotes, INotes, getNotes)

    We need an object that implements IHaveNotes.

        >>> from schoolbell.app.app import Person
        >>> person = Person()

    We also need a principal in the request:

        >>> request = TestRequest()
        >>> person.id = 'someone'
        >>> request.setPrincipal(person)

    And a little more set up:

        >>> traverser = NotesTraverser(person, request)
        >>> adapter = traverser.publishTraverse(request, 'notes')

    We'll work on the person object, for now it has no notes:

        >>> view = NotesView(adapter, request)
        >>> view.GET()
        u'<notes xmlns:xlink="http://www.w3.org/1999/xlink">\n\n\n</notes>\n'

    Now we can create a note to add:

        >>> body = '''<?xml version="1.0"?>
        ... <notes xmlns="http://schooltool.org/ns/model/0.1">
        ...   <note title="A Note" privacy="public"
        ...         body="This is a sample note."/>
        ... </notes>'''

    Let's go ahead and add the note:

        >>> request._body_instream = StringIO(body)
        >>> view = NotesView(adapter, request)
        >>> view.POST()
        ''

    And view it:

        >>> view = NotesView(adapter, request)
        >>> print view.GET()
        <notes xmlns:xlink="http://www.w3.org/1999/xlink">
        ...
            <note body="This is a sample note." privacy="public"
                  title="A Note"/>
        ...
        </notes>
        ...

    Note that we specified that the note would be 'public', so anyone can see
    it, so let's create a private one:

        >>> body = '''<?xml version="1.0"?>
        ... <notes xmlns="http://schooltool.org/ns/model/0.1">
        ...   <note title="A Secret Note" privacy="private"
        ...         body="Something I don't want anyone to know."/>
        ... </notes>'''
        >>> request._body_instream = StringIO(body)
        >>> view = NotesView(adapter, request)
        >>> view.POST()
        ''

    We can see the note (along with the previous note):

        >>> print view.GET()
        <notes xmlns:xlink="http://www.w3.org/1999/xlink">
        ...
            <note body="This is a sample note." privacy="public"
                  title="A Note"/>
        ...
            <note body="Something I don't want anyone to know."
                  privacy="private" title="A Secret Note"/>
        ...
        </notes>
        ...

    But everyone else will only see the public note:

        >>> person2 = Person()
        >>> person2.id = 'someone-else'
        >>> request.setPrincipal(person2)
        >>> view = NotesView(adapter, request)
        >>> print view.GET()
        <notes xmlns:xlink="http://www.w3.org/1999/xlink">
        ...
            <note body="This is a sample note." privacy="public"
                  title="A Note"/>
        ...
        </notes>
        ...

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS|
                             doctest.REPORT_NDIFF),
        doctest.DocTestSuite('schoolbell.app.note.rest'),
        doctest.DocTestSuite('schoolbell.app.note.note'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
