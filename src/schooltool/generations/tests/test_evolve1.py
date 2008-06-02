#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve1
"""
import unittest

from zope.testing import doctest


def doctest_evolve1():
    """Evolution to generation 1.

    Let's run the evolve script on this whole thing:

        >>> from schooltool.generations.evolve1 import evolve
        >>> evolve(None)
        Traceback (most recent call last):
        ...
        NotImplementedError: Evolving from versions prior to 2008.04 is not
        supported! Please upgrade to SchoolTool version 2008.04 first.

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS
                                                 | doctest.NORMALIZE_WHITESPACE),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
