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
Unit tests for schooltool.sampledata.generator
"""

import unittest
import doctest

from zope.interface import implements
from zope.app.testing import setup
from zope.component import provideUtility

from schooltool.sampledata.interfaces  import ISampleDataPlugin


class DummyPlugin:
    """A dummy sample data plugin that logs the args to a class attribute"""
    implements(ISampleDataPlugin)

    log = []  # one for all

    def __init__(self, name, deps=()):
        self.name = name
        self.dependencies = deps

    def generate(self, app, seed=None):
        self.log.append((self.name, app, seed))


def doctest_generate():
    """Unit test for schooltool.sampledata.generator.generate

    This function finds all the utilities registered with the sample
    data plugin interface and runs the generate methods of them.

    First, let's register several plugins:

        >>> p1 = DummyPlugin("p1", ())
        >>> p2 = DummyPlugin("p2", ())
        >>> p3 = DummyPlugin("p3", ())
        >>> provideUtility(p1, ISampleDataPlugin, 'p1')
        >>> provideUtility(p2, ISampleDataPlugin, 'p2')
        >>> provideUtility(p3, ISampleDataPlugin, 'p3')

    Now, let's run the generator:

        >>> DummyPlugin.log = []
        >>> import schooltool.sampledata.generator

        >>> app = 'app'
        >>> result = schooltool.sampledata.generator.generate(app,
        ...                 pluginNames=['p1','p2','p3'])

    The order of the plugins is undefined, so let's sort to see if
    they're all there.

        >>> DummyPlugin.log.sort()
        >>> DummyPlugin.log
        [('p1', 'app', None), ('p2', 'app', None), ('p3', 'app', None)]

    The result returned by this function is a dict of plugin names as
    keys and CPU times consumed as values:

        >>> sorted(result.keys())
        ['p1', 'p2', 'p3']
        >>> for v in result.values():
        ...     v < 0.1
        True
        True
        True

    Let's make p1 and p2 depend on p3:

        >>> p1.dependencies = 'p3',
        >>> p2.dependencies = 'p3',

    Now p3 must be the first plugin run:

        >>> DummyPlugin.log = []
        >>> result = schooltool.sampledata.generator.generate(app,
        ...                 pluginNames=['p1','p2','p3'])
        >>> DummyPlugin.log[0]
        ('p3', 'app', None)

    If we add a dependency on p2 to p1, the order becomes defined:

        >>> p1.dependencies = 'p2',
        >>> DummyPlugin.log = []
        >>> result = schooltool.sampledata.generator.generate(app,
        ...                 pluginNames=['p1','p2','p3'])
        >>> DummyPlugin.log
        [('p3', 'app', None), ('p2', 'app', None), ('p1', 'app', None)]

    If we add an extra dependency and close the cycle, we get an error:

        >>> p3.dependencies = 'p1',
        >>> DummyPlugin.log = []
        >>> result = schooltool.sampledata.generator.generate(app,
        ...                 pluginNames=['p1','p2','p3'])
        Traceback (most recent call last):
          ...
        CyclicDependencyError: cyclic dependency at ...

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setup.placelessSetUp,
                             tearDown=setup.placelessTearDown,
                             optionflags=doctest.ELLIPSIS
                             |doctest.NORMALIZE_WHITESPACE),
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
