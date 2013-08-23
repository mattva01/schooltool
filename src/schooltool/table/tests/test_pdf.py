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
"""
import unittest
import doctest
from pprint import pprint

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.table.pdf import GridCell, Grid
from schooltool.table.pdf import makeCoordinateBlocks


def print_blocks(blocks):
    sx = min([b[0][0] for b in blocks])
    ex = max([b[1][0] for b in blocks])
    sy = min([b[0][1] for b in blocks])
    ey = max([b[1][1] for b in blocks])
    bmap = {}
    for n, block in enumerate(blocks):
        for x in range(block[0][0], block[1][0]+1):
            for y in range(block[0][1], block[1][1]+1):
                bmap[(x, y)] = n
    result = ''
    template = '%%%ds' % (len(str(n))+1)
    for y in range(sy, ey+1):
        result += '\n:'
        for x in range(sx, ex+1):
            result += template % bmap.get((x, y), '')
    print result


def test_makeCoordinateBlocks():
    """

    makeCoordinateBlocks takes coordinates and returns spanning blocks.

        >>> blocks = makeCoordinateBlocks([
        ...     (0,1), (1,1), (2,1), (3,1),
        ...     (0, 2), (2, 2),
        ...     (0, 3), (1, 3)
        ... ])

        >>> blocks
        [((0, 1), (3, 1)),
         ((0, 2), (0, 2)),
         ((2, 2), (2, 2)),
         ((0, 3), (1, 3))]

    We can see it prefers building horizontal blocks over vertical ones.

        >>> print_blocks(blocks)
        : 0 0 0 0
        : 1   2
        : 3 3

        >>> blocks = makeCoordinateBlocks([
        ... (0,1), (1,1), (2,1), (3,1),
        ... (0, 2), (1,2), (2, 2),
        ... (0, 3), (1,3),
        ... ])

        >>> print_blocks(blocks)
        : 0 0 0 0
        : 1 1 1
        : 2 2

    Blocks are created when it finds a line of coordinates that can be
    extruded "down".

        >>> print_blocks(makeCoordinateBlocks([
        ...     (1, 1), (1, 2), (2, 1), (2,2), (2, 3)]))
        : 0 0
        : 0 0
        :   1

        >>> print_blocks(makeCoordinateBlocks([
        ...     (1, 0), (1, 1), (1, 2), (2, 1), (2, 2), (4, 2), (2, 3),
        ...     (3, 1), (3, 2)]))
        : 0
        : 1 1 1
        : 1 1 1 2
        :   3

    Blocks are however made only when "upper" scanline can be extruded "down"

        >>> print_blocks(makeCoordinateBlocks([
        ...     (1, 0), (1, 1), (1, 2), (2, 1), (2, 2), (4, 1), (2, 3),
        ...     (3, 1), (3, 2)]))
        : 0
        : 1 1 1 1
        : 2 2 2
        :   3

    """


def doctest_Grid_getStyleDirectives():
    """

        >>> grid = Grid([], [],  {}, 0)

        >>> cell = GridCell('Hello',
        ...     font_name='Font',
        ...     font_size=816,
        ...     font_leading=7,
        ...     color='very_black',
        ...     background_color='very_white',
        ...     align='left',
        ...     valign='bottom',
        ...     )

        >>> directives = grid.getStyleDirectives(cell, 5, 10)

        >>> pprint(directives)
        {'blockAlignment': [('value', 'left')],
         'blockBackground': [('colorName', 'very_white')],
         'blockFont': [('leading', 7), ('name', 'Font'), ('size', 816)],
         'blockTextColor': [('colorName', 'very_black')],
         'blockValign': [('value', 'bottom')]}

        >>> pprint(grid.getStyleDirectives(GridCell('?', padding=4), 1, 1))
        {'blockBottomPadding': [('length', 4.0)],
         'blockLeftPadding': [('length', 4.0)],
         'blockRightPadding': [('length', 4.0)],
         'blockTopPadding': [('length', 4.0)]}

        >>> pprint(grid.getStyleDirectives(GridCell('?', padding=(2, 4)), 1, 1))
        {'blockBottomPadding': [('length', 4)],
         'blockLeftPadding': [('length', 2)],
         'blockRightPadding': [('length', 2)],
         'blockTopPadding': [('length', 4)]}

        >>> pprint(grid.getStyleDirectives(GridCell('?', padding=(1,2,3,4)), 1, 1))
        {'blockBottomPadding': [('length', 4)],
         'blockLeftPadding': [('length', 1)],
         'blockRightPadding': [('length', 3)],
         'blockTopPadding': [('length', 2)]}

        >>> pprint(grid.getStyleDirectives(GridCell('?', span_rows=4), 2, 5))
        {'blockSpan': [('start', '2 5'), ('stop', '2 8')]}

        >>> pprint(grid.getStyleDirectives(GridCell('?', span_cols=4), 2, 5))
        {'blockSpan': [('start', '2 5'), ('stop', '5 5')]}

        >>> pprint(grid.getStyleDirectives(GridCell('?', span_cols=3, span_rows=2), 2, 5))
        {'blockSpan': [('start', '2 5'), ('stop', '4 6')]}

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
