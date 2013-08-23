#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Tests for SchoolTool catalogs.
"""
import unittest
import doctest

from schooltool.app.catalog import buildQueryString


def doctest_buildQueryString():
    r"""Test buildQueryString

    No text yields empty string.

        >>> buildQueryString('')
        ''

        >>> buildQueryString(' \t \n ')
        ''

    Words are globbed.  Text is lowercase.

        >>> buildQueryString(' Tim Alan ')
        'tim* alan*'

    Commas are replaced by 'or' term.

        >>> buildQueryString(' Tim,   Alan ')
        'tim* or alan*'

        >>> buildQueryString(', Tim, ,,,  Alan ,')
        'tim* or alan*'

    Broken testcases follow.

        >>> buildQueryString('"Timothy" Alan')
        '"timothy" alan*'

        >>> buildQueryString('"Timothy, Alan"')
        '"timothy, alan"'

    Mister Tim or Tom, last name Cook or Cake:

        >>> buildQueryString('T?m C*k*')
        't?m* c*k*'

    Mister Or Arwell:

        >>> buildQueryString('"Or" Arwell')
        '"or" arwell*'

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF|
                    doctest.NORMALIZE_WHITESPACE))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
