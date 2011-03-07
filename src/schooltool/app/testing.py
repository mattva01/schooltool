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

import os
from schooltool.testing.analyze import queryHTML
from schooltool.testing.functional import ZCMLLayer

here = os.path.dirname(__file__)

app_functional_layer = ZCMLLayer(os.path.join(here, 'ftesting.zcml'),
                                 __name__,
                                 'app_functional_layer')


def format_table(table, header_rows=0):
    """Format an ASCII-art table.

    Example:

      >>> print format_table([['11', '12', '13'],
      ...                     ['21', 'center', '23'],
      ...                     ['31', 32, None]])
      +----+--------+------+
      | 11 | 12     | 13   |
      | 21 | center | 23   |
      | 31 | 32     | None |
      +----+--------+------+

      >>> print format_table([])
      +-+
      +-+

      >>> print format_table([['', 'x']])
      +-+---+
      | | x |
      +-+---+

      >>> print format_table([['x', 'y', 'z'],
      ...                     ['11', '12', '13'],
      ...                     ['31', 32, '33']], header_rows=1)
      +----+----+----+
      | x  | y  | z  |
      +----+----+----+
      | 11 | 12 | 13 |
      | 31 | 32 | 33 |
      +----+----+----+

    """
    ncols = table and len(table[0]) or 1
    col_width = [1] * ncols
    for row_data in table:
        for col, cell_data in enumerate(row_data):
            if cell_data != '':
                col_width[col] = max(col_width[col], len(str(cell_data)) + 2)
    hline = '+'.join([''] + ['-' * w for w in col_width] + [''])
    table_rows = ([hline] +
                  ['|'.join([''] +
                            [' ' + str(s).ljust(w - 1)
                             for s, w in zip(row_data, col_width)] +
                            [''])
                   for row_data in table] +
                  [hline])
    if 0 < header_rows < len(table):
        table_rows.insert(1 + header_rows, hline)
    table = '\n'.join(table_rows)
    return table


def format_weekly_calendar(contents):
    table = []
    for n, row in enumerate(queryHTML('//table[@id="calendar-view-week"]//tr', contents)):
        if n == 0:
            header = []
            for cell in queryHTML('//tr//th/a/text()', str(row)):
                header.append(cell)
            table.append(header)
        else:
            block = []
            for cell in queryHTML('//tr//td', str(row)):
                events = []
                for event in queryHTML('//td//a//span/text()', str(cell)):
                    events.append(event)
                block.append(", ".join(events))
            table.append(block)
    return format_table(table, header_rows=1)
