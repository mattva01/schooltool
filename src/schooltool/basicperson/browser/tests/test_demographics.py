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
Unit tests for demographics fields.
"""
import unittest
import doctest

import zope.schema
from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest
from zope.app.testing import setup
from zope.i18n import translate

import z3c.form

from schooltool.basicperson.browser.demographics import (
    CustomEnumDataConverter)


def doctest_CustomEnumDataConverter():
    r"""Tests for CustomEnumDataConverter.

    Value conversions between widget (multi-line unicode string) and
    field(list of text lines).

        >>> field = zope.schema.List(
        ...     __name__='values',
        ...     title=u'Values')

        >>> text = z3c.form.widget.Widget(TestRequest())

        >>> converter = CustomEnumDataConverter(field, text)

        >>> verifyObject(z3c.form.interfaces.IDataConverter, converter)
        True

    Empty field values produce an empty string for the widget.

        >>> converter.toWidgetValue(field.missing_value)
        u''

        >>> converter.toWidgetValue(None)
        u''

        >>> converter.toWidgetValue([])
        u''

    Field values must be iterable object of strings.

        >>> converter.toWidgetValue(('one', 2, '3'))
        Traceback (most recent call last):
        ...
        TypeError: sequence item 1: expected string, int found

        >>> converter.toWidgetValue(iter(['four', '5', 'six']))
        u'four\n5\nsix'

    Conversion to field knows how to filter out whitespace.

        >>> print converter.toFieldValue(u'')
        None

        >>> print converter.toFieldValue(u'  \n \t \t          \n')
        None

    Newlines separate values.

        >>> converter.toFieldValue('         single \t val  ')
        [u'single \t val']

        >>> converter.toFieldValue('one\ntwo\n3')
        [u'one', u'two', u'3']

        >>> converter.toFieldValue('''
        ...
        ...    We
        ...           even
        ...
        ...   support  crazy
        ...                    spacing ''')
        [u'We', u'even', u'support  crazy', u'spacing']

    Duplicate entries are not allowed.

        >>> from z3c.form.converter import FormatterValidationError
        >>> try:
        ...     converter.toFieldValue('''
        ...        department
        ...        of
        ...        redundancy
        ...        department
        ...     ''')
        ... except FormatterValidationError, e:
        ...     print translate(e.message)
        Duplicate entry "department"

    We also have a line length limit because we currently use IDNA encoding for
    vocabularies.

        >>> long_val = (u'Very, very long lines make the idna conversion '
        ...              'throw exceptions')

        >>> len(long_val.encode('idna'))
        63

        >>> converter.toFieldValue(long_val)
        [u'Very, very long lines make the idna conversion throw exceptions']

        >>> long_val += '!'

        >>> long_val.encode('idna')
        Traceback (most recent call last):
        ...
        UnicodeError: label empty or too long

        >>> try:
        ...     converter.toFieldValue(long_val)
        ... except FormatterValidationError, e:
        ...     print translate(e.message)
        Value too long "Very, very long lines make the
        idna conversion throw exceptions!"

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
