#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Unit tests for schooltool.app.
"""
import unittest
import doctest

from schooltool.skin.flourish import sorting


def doctest_scc_tarjan():
    """Tests for Tarjan's strongly connected components.

    First, we need items to sort.

        >>> items = ['fire', 'water', 'cheese', 'goat', 'cabbage']

    Items are used as a priority queue; if there are no dependencies,
    queue is left unchanged.

        >>> sorting.scc_tarjan(items, {})
        [('fire',), ('water',), ('cheese',), ('goat',), ('cabbage',)]

    Say we have some dependencies:

        >>> graph = {'cheese': ['goat']}
        >>> sorting.scc_tarjan(items, graph)
        [('fire',), ('water',), ('goat',), ('cheese',), ('cabbage',)]

        >>> graph = {'cheese': ['goat'], 'goat': ['cabbage']}
        >>> sorting.scc_tarjan(items, graph)
        [('fire',), ('water',), ('cabbage',), ('goat',), ('cheese',)]

    Tarjan's algorithm is mainly used to detect cyclic dependencies.

        >>> graph = {'goat': ['cabbage'], 'cabbage': ['water'],
        ...          'fire': ['cabbage'], 'water': ['goat']}
        >>> sorting.scc_tarjan(items, graph)
        [('cabbage', 'water', 'goat'), ('fire',), ('cheese',)]

    """


def doctest_topological_sort():
    """Tests for a simple implementation of a topological sort.

        >>> items = ['1', '2', '3', '4', '5', '6']
        >>> graph = {'1': ['3'], '5': ['1'], '6': ['3']}

    Graph is a dict of dependencies, 'x' comes after ['y1', 'y2']

        >>> sorting.topological_sort(items, graph)
        ['2', '3', '1', '5', '6', '4']

    topological_sort can also accept a dict of reverse dependencies,
    'x' comes before ['y1', 'y2']

        >>> sorting.topological_sort(items, graph, reverse=True)
        ['2', '5', '1', '6', '3', '4']

    """


def doctest_dependency_graph():
    """Tests for dependency_graph builder.

        The builder takes dicts of revers and direct dependencies and
        makes a combined direct dependecy graph.

        >>> before = {'1': ['3'], '5': ['3'], '4': ['1']}
        >>> after = {'3': ['4', '5', '6']}

        >>> graph = sorting.dependency_graph(before, after)
        >>> for n, d in sorted(graph.items()):
        ...     print n, ':', sorted(d)
        1 : ['4']
        3 : ['1', '4', '5', '6']

    """


def doctest_dependency_sort():
    """Tests for dependency_sort

    dependency_sort sorts items given direct and reverse dependencies.

        >>> items = ['under', 'pants', 'shirt',
        ...          'shoes', 'socks', 'watch', 'tie']

        >>> after = {
        ...     'pants': ['under', 'shirt'],
        ...     }

        >>> before = {
        ...     'pants': ['shoes'],
        ...     'shirt': ['tie'],
        ...     'socks': ['shoes'],
        ...     }

        >>> sorting.dependency_sort(items, before, after)
        ['under', 'socks', 'shirt', 'pants', 'shoes', 'watch', 'tie']


    Usually dependencies can be sorted in many valid ways.  This implementation
    tries to keep 'before' and 'after' items close to their dependencies, at
    the same time maintaining original order.

    Note that '6' after '4' gives different results than '4' before '6':

        >>> items = ['1', '2', '3', '4', '5', '6', '7']

        >>> after = {'6': ['4']}
        >>> before = {'4': ['2']}
        >>> sorting.dependency_sort(items, before, after)
        ['1', '4', '6', '2', '3', '5', '7']


        >>> after = {'2': ['4']}
        >>> before = {'4': ['6']}
        >>> sorting.dependency_sort(items, before, after)
        ['1', '3', '5', '4', '2', '6', '7']


    Here are some more loose tests:

        >>> after = {'3': ['1']}
        >>> before = {'1': ['2'], '5': ['2'],}
        >>> sorting.dependency_sort(items, before, after)
        ['1', '3', '5', '2', '4', '6', '7']

        >>> after = {'2': ['5']}
        >>> before = {'3': ['2'], '4': ['2']}
        >>> sorting.dependency_sort(items, before, after)
        ['1', '3', '4', '5', '2', '6', '7']

        >>> after = {'2': ['4'], '4': ['3']}
        >>> before = {'3': ['6']}
        >>> sorting.dependency_sort(items, before, after)
        ['1', '5', '3', '4', '2', '6', '7']

        >>> after = {'2': ['3'], '3': ['6']}
        >>> before = {'5': ['4']}
        >>> sorting.dependency_sort(items, before, after)
        ['1', '5', '4', '6', '3', '2', '7']


    """


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_NDIFF)

    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=optionflags),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
