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
Tests for schollbell.rest.notes

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app.testing import setup
from zope.app.testing import ztapi
from zope.publisher.browser import TestRequest
from StringIO import StringIO

def doctest_Notes():
    r"""Tests for NotesView.

    First we need a bit of standard set up:

        >>> from schoolbell.app.rest.notes import NotesViewFactory
        >>> from schoolbell.app.rest.notes import NotesTraverser
        >>> from schoolbell.app.rest.notes import NotesView

        >>> from schoolbell.app.notes import getNotes
        >>> from schoolbell.app.interfaces import INotes
        >>> from schoolbell.app.interfaces import IHaveNotes
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
        >>> view.PUT()
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
        >>> view.PUT()
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
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.rest.notes'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
