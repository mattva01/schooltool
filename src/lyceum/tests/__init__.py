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
Helper function for tests.

$Id$
"""
from schooltool.testing.analyze import queryHTML


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


def printGradebookTable(contents):
    table_rows = []

    headers = [header.strip()
               for header in queryHTML('//table[@class="data"]//th/span//text()',
                                       contents)]
    table_rows.append(headers)

    grade_rows = queryHTML('//table[@class="data"]//tr', contents)
    for row in grade_rows:
        grades = []
        grade_cells = queryHTML('//tr//td', row)
        for grade in grade_cells:
            text = queryHTML('//td/a/text()', grade)
            if not text:
                text_input_value = queryHTML('//td//input[@type="text"]/@value', grade)
                if text_input_value:
                    text = ["[%s]" % str(text_input_value[0]).ljust(5, '_')]
            if not text:
                checkbox = queryHTML('//td//input[@type="checkbox"]', grade)
                if checkbox:
                    text = ["[ ]"]
                    input_value = queryHTML('//td//input[@type="checkbox"]/@checked', grade)
                    if input_value:
                        text = ["[V]"]
            if not text:
                text = queryHTML('//td/strong/text()', grade)
                if text:
                    text = ['*%s*' % text[0].strip()]
            if not text:
                text = queryHTML('//td/text()', grade)
            if not text:
                text = ['']
            grades.append(text[0].strip())
        if grades:
            table_rows.append(grades)
    print format_table(table_rows, header_rows=1)
