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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Tests for SchoolTool XLS export views.
"""
import itertools
import xlrd
import datetime


class Blank(str):
    def __new__(cls, show_text=''):
        return str.__new__(cls, show_text)
    def __init__(self, show_text=''):
        str.__init__(self, show_text)
    def __repr__(self):
        return str(self)


class NoCell(Blank):
    pass


class DateTime(datetime.datetime):
    def __repr__(self):
        if self.time().isoformat() == '00:00:00':
            return self.strftime('%Y-%m-%d')
        return self.strftime('%Y-%m-%d %H:%M:%S')


def format_cell(sheet, row, col):
    try:
        cell = sheet.cell(row, col)
    except IndexError:
        return NoCell()
    if cell.ctype == xlrd.XL_CELL_BLANK:
        # Contains formatting information but no data
        return Blank()
    elif cell.ctype == xlrd.XL_CELL_EMPTY:
        return Blank()
    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
        return bool(int(cell.value))
    elif cell.ctype == xlrd.XL_CELL_DATE:
        data = xlrd.xldate_as_tuple(cell.value, sheet.book.datemode)
        return DateTime(*data)
    elif cell.ctype == xlrd.XL_CELL_NUMBER:
        return float(cell.value)
    elif cell.ctype == xlrd.XL_CELL_TEXT:
        return unicode(cell.value)
    elif cell.ctype == xlrd.XL_CELL_ERROR:
        try:
            return NoCell(show_text=xlrd.error_text_from_code.get(int(cell.value), cell))
        except ValueError:
            return NoCell(show_text=repr(cell))


def col_name(n):
    assert n > 0
    name = ''
    while n:
        n = n-1
        name = chr(65+n%26)+name
        n = n/26
    return name


def col_n(name):
    try:
        return int(name)
    except ValueError:
        pass
    name = name.upper()
    i = 0
    while name:
        i = i*26+(ord(name[0])-64)
        name = name[1:]
    return i


def str_to_n_list(s):
    result = []
    ranges = s.split(',')
    for r in ranges:
        parts = [p.strip() for p in r.split('-')]
        if not parts:
            continue
        if len(parts) == 1:
            result.append(col_n(parts[0]))
        elif len(parts) == 2:
            result.extend(range(col_n(parts[0]), col_n(parts[1])+1))
        else:
            raise ValueError('%r is not a range' % r)
    return result


def list_rows_cols(sheet, rows, cols):
    if rows is None:
        rows = range(1, sheet.nrows+1)
    elif isinstance(rows, str):
        rows = str_to_n_list(rows)
    elif not hasattr(rows, '__iter__'):
        rows = rows,

    if cols is None:
        cols = range(1, sheet.ncols+1)
    elif isinstance(cols, str):
        cols = str_to_n_list(cols)
    elif not hasattr(cols, '__iter__'):
        cols = cols,

    rows = list(rows)
    cols = list(cols)
    return rows, cols


def build_sheet_table(sheet, rows=None, cols=None):
    rows, cols = list_rows_cols(sheet, rows, cols)

    table = []
    if not rows or not cols:
        return table

    trow = [NoCell(show_text='*')]
    prev_col = cols[0]-1
    for ncol in cols:
        if ncol != prev_col+1:
            trow.append(NoCell())
        trow.append(NoCell(show_text=col_name(ncol)))
        prev_col = ncol
    table.append(trow)

    prev_row = rows[0]-1
    for nrow in rows:
        assert nrow > 0
        if nrow != prev_row+1:
            table.append([NoCell(show_text='...')])
        trow = [NoCell(show_text=' %d ' % (nrow))]
        prev_col = cols[0]-1
        for ncol in cols:
            if ncol > prev_col+1:
                trow.append(NoCell(show_text='...'))
            prev_col = ncol
            cell = format_cell(sheet, nrow-1, ncol-1)
            trow.append(cell)
        prev_row = nrow
        table.append(trow)

    return table


def format_sheet_table(table):
    mlen = [max([len(repr(cell)) for cell in col])
            for col in itertools.izip_longest(*table, fillvalue=NoCell())]
    def val(cell, ncoll):
        r = repr(cell)
        l = len(r)
        s = (mlen[ncoll]-l)
        val = '%s%s%s' % (' '*(s/2), r, ' '*(s-s/2))
        if isinstance(cell, NoCell):
            return ' %s ' % val
        return '[%s]' % val
    for y, row in enumerate(table):
        for x, cell in enumerate(row):
            table[y][x] = val(cell, x)
    return '\n'.join([''.join([str(c) for c in r]) for r in table])


def print_sheet(sheet, rows=None, cols=None):
    table = build_sheet_table(sheet, rows=rows, cols=cols)
    print format_sheet_table(table)
