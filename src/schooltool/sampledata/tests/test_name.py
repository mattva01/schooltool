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
Unit tests for schooltool.sampledata.name
"""

import unittest
import doctest


def doctest_NameGenerator():
    """Person name generator

    First, let's instantiate the generator, passing the random seed as
    a parameter:

        >>> from schooltool.sampledata.name import NameGenerator
        >>> gen = NameGenerator(42)

    It's got its own random generator seeded with the seed passed:

        >>> other = NameGenerator(42)
        >>> gen.random.random() == other.random.random()
        True

        >>> gen = NameGenerator(42)
        >>> other = NameGenerator(43)
        >>> gen.random.random() != other.random.random()
        True

    It's got lists of first names and last names:

        >>> import repr
        >>> print repr.repr(gen.first_names)
        ['Ada', 'Adam', 'Adrian', 'Agnieszka', 'Ainhoa', 'Al', ...]
        >>> print repr.repr(gen.last_names)
        ['Adams', 'Alexander', 'Allen', 'Alvarez', 'Andersen', 'Anderson', ...]

    Now, we can ask for a name:

        >>> gen.random.seed(42)
        >>> gen.generate()
        ('Margarita', 'Austin', 'Margarita Austin')
        >>> gen.generate()
        ('Erin', 'Duncan', 'Erin Duncan')

    The names can and will repeat:

        >>> seen = set()
        >>> count = 0
        >>> while True:
        ...     count +=1
        ...     first_name, last_name, name = gen.generate()
        ...     if name in seen:
        ...         break
        ...     else:
        ...         seen.add(name)

        >>> print count, name
        334 Joanne Snyder

    We'll have approximately this many matching pairs of names in the school:

        >>> seen = set()
        >>> for i in range(1000):
        ...     seen.add(gen.generate()[2])
        >>> 1000 - len(seen)
        3

    """

def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS
                             |doctest.NORMALIZE_WHITESPACE),
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
