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

from schooltool.skin import flourish
from schooltool.table import interfaces
from schooltool.table.column import unindex


def getRMLTable(formatter, request):
    table = zope.component.queryMultiAdapter(
        (formatter.context, request, formatter.view, formatter),
        interfaces.IRMLTable)
    return table


class RMLTable(flourish.content.ContentProvider):
    implements(interfaces.IRMLTable)
    zope.component.adapts(Interface,
                          flourish.interfaces.IFlourishLayer,
                          flourish.interfaces.IPage,
                          interfaces.ITableFormatter)

    __name__ = '@@rml'

    formatter = None

    template = flourish.templates.XMLFile('rml/table.pt')

    def __init__(self, context, request, schooltool_formatter, table):
        flourish.content.ContentProvider.__init__(
            self, context, request, schooltool_formatter)
        self.table = table
        self.styles = {
            ('0,0', '-1,0'): {
                'background': 'table.header.background',
                'text': 'table.header.text',
                # 'font': 'Ubuntu_Bold',
                },
            }

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
        rows = [[column.renderHeader(self.formatter)
                 for column in rml_columns]]
        rows.extend(
            [[column.renderCell(item, self.formatter)
              for column in rml_columns]
             for item in items])

        styles = [
            dict([('start', pos[0]), ('stop', pos[1])] + val.items())
            for pos, val in sorted(self.styles.items())]
        rml = self.template(
            table=rows, styles=styles,
            col_widths = widths_string,
            table_style_id="XXX: unique")
        return rml


class IndexedRMLTable(RMLTable):
    zope.component.adapts(Interface,
                          flourish.interfaces.IFlourishLayer,
                          flourish.interfaces.IPage,
                          interfaces.IIndexedTableFormatter)

    def getColumns(self):
        columns = super(IndexedRMLTable, self).getColumns()
        # Make sure columns can handle indexed objects
        indexed_columns = [interfaces.IIndexedColumn(c) for c in columns]
        return indexed_columns


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
