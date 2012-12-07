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

import zope.component
from zope.interface import implements, Interface
from zope.cachedescriptors.property import Lazy

from schooltool.skin import flourish
from schooltool.table import interfaces
from schooltool.table.column import unindex


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
        return self.formatter.visible_columns

    def makeFormatter(self):
        if self.table._table_formatter is None:
            # XXX: implicit updates are not a good idea.
            self.table.update()
        formatter = self.table.makeFormatter()
        return formatter

    def update(self):
        self.formatter = self.makeFormatter()

    def getColumns(self):
        visible_names = [c.name for c in self.visible_column_names]
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

    update = RMLTable.update
    render = RMLTable.render

    def __init__(self, context, request, view, manager):
        flourish.report.PDFPart.__init__(self, context, request, view, manager)

    @Lazy
    def table(self):
        table = self.view.providers[self.table_name]
        return table

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
