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
Unit tests for schoolbell.app.notes
"""

import unittest

from zope.testing import doctest
from zope.app.tests import setup
from zope.interface import implements
from zope.app.annotation.interfaces import IAttributeAnnotatable


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

        >>> from schoolbell.app.notes import getNotes
        >>> notes = getNotes(obj)

        >>> from schoolbell.app.interfaces import INotes
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(INotes, notes)
        True

    If you do it more than once, you will get the same Notes object

        >>> notes is getNotes(obj)
        True

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
                doctest.DocTestSuite('schoolbell.app.notes'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
