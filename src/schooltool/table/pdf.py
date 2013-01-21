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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
RML tables.
"""
import math
import os

import zope.component
from zope.interface import implements, Interface
from zope.cachedescriptors.property import Lazy

from reportlab.lib import units
from reportlab.pdfbase import pdfmetrics

from schooltool.skin import flourish
from schooltool.table import interfaces
from schooltool.table.column import unindex

from schooltool.common import SchoolToolMessage as _


def getRMLTable(formatter, request):
    table = zope.component.queryMultiAdapter(
        (formatter.context, request, formatter.view, formatter),
        interfaces.IRMLTable)
    return table


class FlatRMLTable(flourish.content.ContentProvider):
    implements(interfaces.IRMLTable)
    zope.component.adapts(Interface,
                          flourish.interfaces.IFlourishLayer,
                          flourish.interfaces.IPageBase,
                          interfaces.ITableFormatter)

    __name__ = '@@rml'

    formatter = None

    template = flourish.templates.XMLFile('rml/table.pt')

    def __init__(self, context, request, schooltool_formatter, table):
        flourish.content.ContentProvider.__init__(
            self, context, request, schooltool_formatter)
        self.table = table

    @property
    def visible_column_names(self):
        if self.formatter is None:
            return ()
        return [c.name for c in self.formatter.visible_columns]

    def makeFormatter(self):
        if self.table._table_formatter is None:
            # XXX: implicit updates are not a good idea.
            self.table.update()
        formatter = self.table.makeFormatter()
        return formatter

    def update(self):
        self.formatter = self.makeFormatter()

    def getColumns(self):
        visible_names = list(self.visible_column_names)
        # XXX: also add columns we want, remove columns we want to hide
        columns = [self.formatter.columns_by_name[name]
                   for name in visible_names]
        return columns

    def getRMLColumns(self, columns):
        columns = filter(lambda c: c is not None and c.visible, [
            zope.component.queryMultiAdapter(
                (self.context, self.request, self.view, column),
                interfaces.IRMLColumn,
                column.name
                )
            or
            zope.component.queryMultiAdapter(
                (self.context, self.request, self.view, column),
                interfaces.IRMLColumn,
                )
            for column in columns])

        return columns

    def getItems(self):
        # reset batching
        self.formatter.batch_start = self.formatter.batch_size = None
        items = self.formatter.getItems()
        for item in items:
            yield item

    def getRMLId(self, prefix=''):
        parent = self.__parent__
        parents = []
        while (parent is not None and
               flourish.interfaces.IPDFPage.providedBy(parent)):
            name = getattr(parent, '__name__', None)
            parents.append(str(name))
            parent = parent.__parent__
        name_list = ([str(self.__name__)] +
                     parents[:-1] +
                     [prefix])
        return flourish.page.sanitize_id('-'.join(reversed(name_list)))

    def render(self):
        columns = self.getColumns()
        rml_columns = self.getRMLColumns(columns)

        if not rml_columns:
            return ''

        items = self.getItems()

        n_cols = len(rml_columns)
        col_width = max(int(100./n_cols), 1)
        widths_string = ' '.join(
            ['%d%%' % col_width] * (n_cols-1) +
            ['%d%%' % max(100-col_width*(n_cols-1), 1)])
        headers = [[column.renderHeader(self.formatter)
                    for column in rml_columns]]
        tables = [
            {'rows': [[column.renderCell(item, self.formatter)
                       for column in rml_columns]
                      for item in items]
             }]

        rml = self.template(
            headers=headers, content=tables,
            col_widths=widths_string)
        return rml


class RMLTable(FlatRMLTable):

    def getColumns(self):
        columns = super(RMLTable, self).getColumns()
        group_by_column = self.formatter.group_by_column
        if group_by_column:
            columns = [column
                       for column in columns
                       if column.name != group_by_column]
        return columns

    def render(self):
        columns = self.getColumns()
        rml_columns = self.getRMLColumns(columns)

        if not rml_columns:
            return ''

        items = self.getItems()

        n_cols = len(rml_columns)
        col_width = max(int(100./n_cols), 1)
        widths_string = ' '.join(
            ['%d%%' % col_width] * (n_cols-1) +
            ['%d%%' % max(100-col_width*(n_cols-1), 1)])

        headers = [[column.renderHeader(self.formatter)
                 for column in rml_columns]]

        tables = []
        rows = []
        current_group = None
        for item in items:
            group = self.formatter.getSubGroup(item)
            if group != current_group:
                if rows:
                    tables.append({
                        'headers': current_group and [[current_group]] or [],
                        'rows': rows,
                        })
                current_group = group
                rows = []
            rows.append([column.renderCell(item, self.formatter)
                         for column in rml_columns])

        if rows:
            tables.append({
                    'headers': current_group and [[current_group]] or [],
                    'rows': rows,
                    })

        rml = self.template(
            headers=headers, content=tables,
            col_widths=widths_string)
        return rml


class IndexedRMLTable(RMLTable):
    zope.component.adapts(Interface,
                          flourish.interfaces.IFlourishLayer,
                          flourish.interfaces.IPageBase,
                          interfaces.IIndexedTableFormatter)

    def getColumns(self):
        columns = super(IndexedRMLTable, self).getColumns()
        # Make sure columns can handle indexed objects
        indexed_columns = [interfaces.IIndexedColumn(c) for c in columns]
        return indexed_columns


class RMLTablePart(flourish.report.PDFPart, RMLTable):

    template = flourish.templates.XMLFile('rml/table_part.pt')

    title = None
    table_name = 'table'

    render = RMLTable.render

    def __init__(self, context, request, view, manager):
        flourish.report.PDFPart.__init__(self, context, request, view, manager)

    @Lazy
    def table(self):
        table = self.view.providers[self.table_name]
        return table

    def update(self):
        flourish.report.PDFPart.update(self)
        RMLTable.update(self)

    def getColumns(self):
        table = self.table
        columns = RMLTable.getColumns(self)
        if interfaces.IIndexedTableFormatter.providedBy(table):
            indexed_columns = [interfaces.IIndexedColumn(c) for c in columns]
            return indexed_columns
        return columns


class RMLColumn(object):
    implements(interfaces.IRMLColumn)

    visible = True

    def __init__(self, context, request, view, column):
        self.context = context
        self.request = request
        self.view = view
        self.column = column

    @property
    def name(self):
        return self.column.name

    @property
    def title(self):
        return self.column.title

    def renderHeader(self, formatter):
        header = self.column.renderHeader(formatter)
        return header

    def renderCell(self, item, formatter):
        return ''

    def escape(self, value):
        return value and unicode(value).replace(
            '&', '&amp;').replace(
            '<', '&lt;').replace(
            '>', '&gt;').strip() or ''


class HiddenRMLColumn(RMLColumn):
    visible = False


class RMLGetterColumn(RMLColumn):

    def renderCell(self, item, formatter):
        value = self.column.getter(item, formatter)
        return self.escape(value)


class RMLDateColumn(RMLColumn):

    def renderCell(self, item, formatter):
        value = self.column.getter(item, formatter)
        view = zope.component.queryMultiAdapter(
            (value, formatter.request),
            name='mediumDate',
            default=lambda: '')
        date = view()
        return date


class RMLIndexedColumn(RMLGetterColumn):

    def renderCell(self, indexed_item, formatter):
        item = unindex(indexed_item)
        cell = super(RMLIndexedColumn, self).renderCell(item, formatter)
        return cell


class Config(dict):

    def __init__(self, default=None, **kw):
        dict.__init__(self)
        if default is not None:
            self.update(default)
        self.update(kw)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if not hasattr(instance, '_schooltool_table_pdf_Config'):
            setattr(instance, '_schooltool_table_pdf_Config', Config())
            instance._schooltool_table_pdf_Config.update(self)
        return instance._schooltool_table_pdf_Config

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __repr__(self):
        return '<%s (%s)>' % (self.__class__.__name__, dict.__repr__(self))


class GridCell(object):

    style = Config(
        para_class=None,
        )

    def __init__(self, text, item=None, name=None, no_data=False, **kw):
        self.__name__ = name if name is not None else text
        self.item = item
        self.text = text
        self.no_data = no_data
        self.style.update(kw)

    def __call__(self):
        if self.style.para_class:
            return '<para style="%s">%s</para>' % (
                self.style.para_class, self.text)
        return self.text


class GridColumn(GridCell):

    def __cmp__(self, other):
        return cmp((self.__name__, self.item), (other.__name__, other.item))


class GridRow(GridCell):

    style = Config(
        GridCell.style,
        para_class='grade.table.row-title',
        )

    def __cmp__(self, other):
        return cmp((self.__name__, self.item), (other.__name__, other.item))


def random_id(numbers=4):
    return 'id-'+os.urandom(numbers).encode('hex')


class Grid(object):

    config = Config(
        table_style_name = "grade.table.grades",
        title_column_width = 4 * units.cm,
        header_font = 'Ubuntu_Regular',
        header_font_size = 12,
        column_padding = 4,
        )

    rows = None
    columns = None
    getter = None

    template = flourish.templates.XMLFile('rml/grid.pt')

    def __init__(self, rows, columns, data_getter, table_width, style_id=None,
                 config=None, **kw):
        if config is not None:
            self.config.update(config)
        self.config.update(kw)

        if style_id is None:
            self.style_id = self.random_id()
        else:
            self.style_id = style_id
        self.rows = rows
        self.columns = columns
        self.table_width = table_width
        if hasattr(data_getter, 'get'):
            self._getter_data = data_getter
            self.getter = lambda row, column: data_getter.get((row, column))
        else:
            self.getter = data_getter

    random_id = lambda self: random_id()

    def getCell(self, row, column):
        cell = self.getter(row, column)
        if cell is None:
            return GridCell(u'', item=None)
        if isinstance(cell, GridCell):
            return cell
        return GridCell(unicode(cell), item=cell)

    def getMaxTextSize(self, columns, default_font, default_font_size):
        max_text_length = max([
            pdfmetrics.stringWidth(
                    unicode(column.text),
                    column.style.get('font_name', default_font),
                    column.style.get('font_size', default_font_size),
                    )
            for column in columns
            ])
        max_text_width = max([column.style.get('font_size', default_font_size)
                              for column in columns])
        return max_text_length, max_text_width

    def getDataColumnWidth(self, width, columns, font_size):
        n_cols = len(columns)
        if n_cols <= 1:
            return width

        ang = math.cos(45./180*math.pi)

        max_column_text_length, _unused = self.getMaxTextSize(
            columns, self.config.header_font, font_size)

        last_font_size = columns[-1].style.get('font_size', font_size)

        slanted_header_horiz_w = (max_column_text_length + last_font_size) * ang
        slanted_header_vert_w = last_font_size * ang
        slanted_header_w = slanted_header_horiz_w - slanted_header_vert_w/2

        data_col_w = min(
            (width - slanted_header_w) / (n_cols - 0.5),
            width / n_cols)
        return data_col_w

    def getColumnStrings(self, columns, col_width):
        result = []
        ang = math.cos(45./180*math.pi)
        x = ang*self.config.title_column_width
        padding = col_width / 2 + self.config.header_font_size * ang / 2
        font_name = None
        font_size = None
        for n, column in enumerate(self.columns):
            pos = x + (n * col_width + padding) * ang
            col_font = column.style.get('font_name', self.config.header_font)
            col_font_size = column.style.get('font_size', self.config.header_font_size)
            changed = (col_font != font_name or col_font_size != font_size)
            result.append({
                    'font_changed': changed,
                    'font_name': col_font,
                    'font_size': col_font_size,
                    'x': pos,
                    'y': -pos,
                    'text': column.text,
                    })
            font_name = col_font
            font_size = col_font_size
        return result

    def updateColumns(self, columns, table_width):
        data_width = table_width - self.config.title_column_width
        self.data_column_width = self.getDataColumnWidth(
            data_width, columns, self.config.header_font_size)
        self.column_strings = self.getColumnStrings(
            columns, self.data_column_width)

        n_cols = len(self.columns)
        spacing = max(0, self.table_width
                         - self.config.title_column_width
                         - self.data_column_width*n_cols)
        widths = ([self.config.title_column_width] +
                  [self.data_column_width] * n_cols +
                  [spacing])
        self.column_widths = ' '.join([str(width) for width in widths])

    def updateHeaderGraphics(self):
        self.header_width = self.table_width

        max_text_length, max_text_width = self.getMaxTextSize(
            self.columns, self.config.header_font, self.config.header_font_size)

        ang = math.cos(45./180*math.pi)
        line_len = max_text_length + max_text_width
        self.header_height = line_len * ang

        left = self.config.title_column_width * ang
        self.header_lines = []
        for n in range(len(self.columns)):
            pos = left + n*self.data_column_width*ang
            self.header_lines.append(
                '%d %d %d %d' % (pos, -pos, pos+line_len, -pos))

    def updateData(self):
        self.data = [
            [row] + [self.getCell(row, column)
                     for column in self.columns]
            for row in self.rows
            ]

    def getStyleDirectives(self, cell, x, y):
        directives = {}
        font = dict(
             filter(lambda v: v[1], [
                    ('name', cell.style.get('font_name')),
                    ('size', cell.style.get('font_size')),
                    ('leading', cell.style.get('font_leading')),
                    ]))
        if font:
            directives['blockFont'] = sorted(font.items())

        color = cell.style.get('color')
        if color:
            directives['blockTextColor'] = [('colorName', color)]

        bg_color = cell.style.get('background_color')
        if bg_color:
            directives['blockBackground'] = [('colorName', bg_color)]

        align = cell.style.get('align')
        if align:
            directives['blockAlignment'] = [('value', align)]

        valign = cell.style.get('valign')
        if valign:
            directives['blockValign'] = [('value', valign)]

        span_rows = cell.style.get('span_rows')
        span_cols = cell.style.get('span_cols')
        if span_rows or span_cols:
            span_rows = int(span_rows or 1)
            span_cols = int(span_cols or 1)
            directives['blockSpan'] = [
                ('start', '%d %d' % (x, y)),
                ('stop', '%d %d' % (x+span_cols-1, y+span_rows-1)),
                ]
        padding = cell.style.get('padding')
        if padding is not None:
            if isinstance(padding, (tuple, list)):
                if len(padding) == 2:
                    left, top = padding
                    right = left
                    bottom = top
                else:
                    left, top, right, bottom = padding
            else:
                left = top = bottom = right = float(padding)
            directives['blockLeftPadding'] = [('length', left)]
            directives['blockTopPadding'] = [('length', top)]
            directives['blockRightPadding'] = [('length', right)]
            directives['blockBottomPadding'] = [('length', bottom)]
        return directives

    def updateStyles(self):
        style_map = {}
        for y, row in enumerate(self.data):
            for x, cell in enumerate(row):
                directives = self.getStyleDirectives(cell, x, y)
                for directive, signature in directives.items():
                    if directive not in style_map:
                        style_map[directive] = {}
                    if signature not in style_map[directive]:
                        style_map[directive][signature] = [(x, y)]
                    else:
                        style_map[directive][signature].append((x, y))
        self.styles = {}
        for directive, signatures in sorted(style_map.items()):
            if directive not in self.styles:
                self.styles[directive] = []
            for signature, coordinates in sorted(signatures.items()):
                blocks = makeCoordinateBlocks(coordinates)
                for starts, ends in blocks:
                    style = {'start': '%d %d' % starts,
                             'stop': '%d %d' % ends}
                    style.update(dict(list(signature)))
                    self.styles[directive].append(style)

    def update(self):
        self.updateColumns(self.columns, self.table_width)
        self.updateHeaderGraphics()
        self.updateData()
        self.updateStyles()

    def renderStyles(self):
        result = []
        for directive in self.styles:
            for entries in self.styles[directive]:
                for entry in entries:
                    result.append('<%s %s />' % (
                        directive,
                        ' '.join(['%s="%s"' % (k, v)
                                  for k, v in sorted(entry.items())])
                        ))
        return '\n'.join(result)

    def render(self):
        return self.template()


class AutoFitGrid(Grid):

    config = Config(
        Grid.config,
        header_min_font_size = 8,
        min_column_width = None,
        max_column_width = None,
        continued_font = Grid.config.header_font,
        continued_text = _('Continued ...'),
        )

    remaining_columns = None

    def getDataColumnWidth(self, width, columns, font_size):
        data_column_width = Grid.getDataColumnWidth(self, width, columns, font_size)
        if self.config.max_column_width is None:
            return data_column_width
        min_headers_column_width = self.getMinHeadersWidth(columns, font_size)
        return max(min_headers_column_width,
                   min(data_column_width, self.config.max_column_width)
                )

    def getMinHeadersWidth(self, columns, font_size):
        ang = math.cos(45./180*math.pi)
        _unused, max_text_height = self.getMaxTextSize(
            columns, self.config.header_font, font_size)
        # Min width so that headers would fit
        min_headers_column_width = (max_text_height * ang
                                    + max_text_height * ang
                                    + self.config.column_padding * 2)
        return min_headers_column_width

    def columnsFit(self, columns, table_width, font_size):
        min_headers_column_width = self.getMinHeadersWidth(columns, font_size)
        data_column_width = self.getDataColumnWidth(table_width, columns, font_size)
        if self.config.min_column_width is None:
            return data_column_width >= min_headers_column_width
        # Column must fit headers and honour desired min_column_width
        min_column_width = max(min_headers_column_width,
                               self.config.min_column_width)
        return data_column_width >= min_column_width

    def fitColumns(self, columns, table_width):
        if not columns:
            return

        # Try fitting all columns, reducing the font if necessary
        orig_font_size = self.config.header_font_size
        font_size = self.config.header_font_size
        while font_size >= self.config.header_min_font_size:
            if self.columnsFit(columns, table_width, font_size):
                self.columns = columns
                self.remaining_columns = []
                self.config.header_font_size = font_size
                return
            font_size -= 1
        self.config.header_font_size = orig_font_size

        # Fit as many columns as we can
        continued = [GridColumn(self.config.continued_text,
                                font_name=self.config.continued_font,
                                no_data=True)]
        n = 1
        while n < len(columns):
            if not self.columnsFit(
                columns[:n] + continued, table_width, self.config.header_font_size):
                break
            n += 1
        self.columns = columns[:n] + continued
        self.remaining_columns = columns[n:]

    def updateColumns(self, columns, table_width):
        self.all_columns = columns
        self.remaining_columns = []
        self.fitColumns(columns, table_width)
        super(AutoFitGrid, self).updateColumns(self.columns, table_width)


class GridContent(flourish.content.ContentProvider):

    tables = None

    def getTableWidth(self):
        return self.view.page_size[0] - self.view.margin.left - self.view.margin.right

    def getRMLId(self, prefix=''):
        parent = self.__parent__
        parents = []
        while (parent is not None and
               flourish.interfaces.IPDFPage.providedBy(parent)):
            name = getattr(parent, '__name__', None)
            parents.append(str(name))
            parent = parent.__parent__
        name_list = ([str(self.__name__)] +
                     parents[:-1] +
                     [prefix])
        return flourish.page.sanitize_id('-'.join(reversed(name_list)))

    def updateTables(self):
        id_base = self.getRMLId()
        table_width = self.getTableWidth()
        table = AutoFitGrid(
            self.rows, self.columns, self.grid, table_width,
            style_id=id_base+'-style')
        table.update()
        self.tables = [table]
        while table.remaining_columns:
            other = AutoFitGrid(
                self.rows, table.remaining_columns, self.grid, table_width,
                style_id=id_base+'-style%d' % len(self.tables),
                config=table.config)
            other.update()
            self.tables.append(other)
            table = other

    def update(self):
        super(GridContent, self).update()
        self.updateGrid()
        self.updateTables()

    def render(self):
        return '\n'.join([table.render() for table in self.tables])

    def updateGrid(self):
        # List of GridColumn
        self.columns = []
        # List of GridRow
        self.rows = []
        # data[GridRow, GridColumn] = GridCell / number / string
        self.grid = {}


class GridContentBlock(flourish.report.PDFContentBlock, GridContent):

    template = flourish.templates.XMLFile('rml/grid_part.pt')
    render = template

    update = GridContent.update


class GridPart(flourish.report.PDFPart, GridContentBlock):

    template = flourish.templates.XMLFile('rml/grid_part.pt')
    render = template

    def update(self):
        flourish.report.PDFPart.update(self)
        GridContentBlock.update(self)

    def __init__(self, context, request, view, manager):
        GridContent.__init__(self, context, request, view)
        flourish.report.PDFPart.__init__(self, context, request, view, manager)


def makeCoordinateBlocks(coords):
    if not coords:
        return []
    if len(coords) == 1:
        return [(coords[0], coords[0])]
    coords = sorted(coords, key=lambda c: (c[1], c[0]))
    slices = []

    sx, sy = coords[0]
    ex = sx
    for x, y in coords[1:]:
        if y == sy and x == ex+1:
            ex = x
        else:
            slices.append(((sx, sy), (ex, sy)))
            sx = ex = x
            sy = y
    if coords[-1] != slices[-1][-1]:
        slices.append(((sx, sy), (ex, sy)))

    blocks = []
    while slices:
        slice = slices.pop(0)
        (sx, sy), (ex, ey) = slice
        for other in list(slices):
            if (other[0][0] == sx and
                other[1][0] == ex and
                other[0][1] == ey+1):
                ey = ey + 1
                slices.remove(other)
            elif (ex > sx and
                  other[0][0] == sx and
                  other[1][0] > ex and
                  other[0][1] == ey+1):
                ey = ey + 1
                slices[slices.index(other)] = ((ex+1, other[0][1]),
                                               (other[1][0], other[1][1]))
        blocks.append(((sx, sy), (ex, ey)))
    return blocks
