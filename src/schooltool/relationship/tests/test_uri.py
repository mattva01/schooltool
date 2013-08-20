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
Unit tests for schooltool.relationship.uri
"""
import unittest
import doctest


def doctest_URIObject():
    """Tests for URIObject.

    URIObject's constructor takes three arguments: URI, name and description

        >>> from schooltool.relationship.uri import URIObject
        >>> uri = URIObject('http://example.com', 'Example', 'An example.')
        >>> uri
        <URIObject Example>
        >>> uri.uri
        'http://example.com'
        >>> uri.name
        'Example'
        >>> uri.description
        'An example.'

    The attributes of an URIObject match those defined by IURIObject

        >>> from zope.interface.verify import verifyObject
        >>> from schooltool.relationship.uri import IURIObject
        >>> verifyObject(IURIObject, uri)
        True

    Description is optional

        >>> uri = URIObject('http://example.com', 'Example')
        >>> uri.description
        ''

    Name is also optional

        >>> uri = URIObject('http://example.com')
        >>> uri.name

    XXX Why does description default to '', while name defaults to None?

    URIs must be syntactically valid

        >>> URIObject('not a URI')
        Traceback (most recent call last):
          ...
        ValueError: This does not look like a URI: 'not a URI'

    URIObjects are comparable.  Two URIObjects are equal if, and only if,
    their 'uri' attributes are equal.

        >>> uri2 = URIObject('http://example.com', 'Exampleur')
        >>> uri3 = URIObject('http://example.org', 'Exampleur')
        >>> uri2 == uri
        True
        >>> uri2 == uri3
        False
        >>> uri2 != uri
        False
        >>> uri2 != uri3
        True
        >>> uri == 'example:Just a string'
        False
        >>> uri != 'example:Just a string'
        True

    By the way, there are separate tests for == and != because in Python
    __eq__ and __ne__ are two different methods.

    What should uri == 'http://example.com' return?  I have decided that
    it should return False, because applications may rely on roles having
    `name` and `description` attributes, after they check the relationship
    type.

        >>> uri == 'http://example.com'
        False
        >>> uri != 'http://example.com'
        True

    URIObjects are hashable.  Equal objects must hash to the same value

        >>> hash(uri) == hash(uri2)
        True

    URIObjects are immutable

        >>> uri.uri = 'http://makemoneyfast.example.net'
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

        >>> uri.name = 'Friendship'
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

        >>> uri.description = 'Dunno'
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite('schooltool.relationship.uri'),
                doctest.DocTestSuite(),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
