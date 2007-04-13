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
"""Base code for table rendering and filtering.

$Id$
"""
import urllib

from zope.interface import implements
from zope.interface import directlyProvides
from zope.i18n.interfaces.locales import ICollator
from zope.app.pagetemplate import ViewPageTemplateFile
from zc.table import table
from zc.table import column
from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn
from zope.app import zapi
from zope.component import queryMultiAdapter
from zope.security.proxy import removeSecurityProxy
from zope.app.dependable.interfaces import IDependable
from zope.app.catalog.interfaces import ICatalog
from zope.component import getUtility
from zope.app.intid.interfaces import IIntIds

from schooltool.table.batch import Batch
from schooltool.table.interfaces import IFilterWidget
from schooltool.table.interfaces import ITableFormatter
from schooltool.table.interfaces import IIndexedColumn


class FilterWidget(object):
    """A simple one field search widget.

    Filters out items in the container by their title.
    """
    implements(IFilterWidget)

    template = ViewPageTemplateFile('templates/filter.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def render(self):
        return self.template()

    def filter(self, list):
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in list
                       if searchstr in item.title.lower()]
        else:
            self.request.form['SEARCH'] = ''
            results = list

        return results

    def active(self):
        return 'SEARCH' in self.request

    def extra_url(self):
        if 'SEARCH' in self.request:
            return '&SEARCH=%s' % self.request.get('SEARCH')
        return ''


class IndexedFilterWidget(FilterWidget):

    def filter(self, list):
        catalog = ICatalog(self.context)
        index = catalog['title']
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = []
            for item in list:
                title = index.documents_to_values[item['id']]
                if searchstr in title.lower():
                    results.append(item)
        else:
            self.request.form['SEARCH'] = ''
            results = list

        return results


class CheckboxColumn(column.Column):
    """A columns with a checkbox

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ of the item being displayed.
    """

    def __init__(self, prefix, name=None, title=None):
        super(CheckboxColumn, self).__init__(name=name, title=title)
        self.prefix = prefix

    def renderCell(self, item, formatter):
        id = "%s.%s" % (self.prefix, item.__name__)
        return '<input type="checkbox" name="%s" id="%s" />' % (id, id)


def label_cell_formatter_factory(prefix=""):
    if prefix:
        prefix = prefix + "."
    def label_cell_formatter(value, item, formatter):
        return '<label for="%s%s">%s</label>' % (prefix,
                                                 item.__name__,
                                                 value)
    return label_cell_formatter


class DependableCheckboxColumn(CheckboxColumn):
    """A column that displays a checkbox that is disabled if item has dependables.

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ of the item being displayed.
    """

    def renderCell(self, item, formatter):
        id = "%s.%s" % (self.prefix, item.__name__)

        if self.hasDependents(item):
            return '<input type="checkbox" name="%s" id="%s" disabled="disabled" />' % (id, id)
        else:
            return '<input type="checkbox" name="%s" id="%s" />' % (id, id)

    def hasDependents(self, item):
        # We cannot adapt security-proxied objects to IDependable.  Unwrapping
        # is safe since we do not modify anything, and the information whether
        # an object can be deleted or not is not classified.
        unwrapped_context = removeSecurityProxy(item)
        dependable = IDependable(unwrapped_context, None)
        if dependable is None:
            return False
        else:
            return bool(dependable.dependents())


def url_cell_formatter(value, item, formatter):
    url = zapi.absoluteURL(item, formatter.request)
    return '<a href="%s">%s</a>' % (url, value)


class LocaleAwareGetterColumn(GetterColumn):
    """Getter columnt that has locale aware sorting."""

    implements(ISortableColumn)

    def getSortKey(self, item, formatter):
        collator = ICollator(formatter.request.locale)
        s = self.getter(item, formatter)
        return s and collator.key(s)


class IndexedGetterColumn(GetterColumn):
    implements(IIndexedColumn, ISortableColumn)

    def __init__(self, **kwargs):
        self.index = kwargs.pop('index')
        super(IndexedGetterColumn, self).__init__(**kwargs)

    def renderCell(self, item, formatter):
        item = item['context'][item['key']]
        value = self.getter(item, formatter)
        return self.cell_formatter(value, item, formatter)

    def getSortKey(self, item, formatter):
        id = item['id']
        index = item['catalog'][self.index]
        return index.documents_to_values[id]


class IndexedLocaleAwareGetterColumn(IndexedGetterColumn):

    _cached_collator = None

    def getSortKey(self, item, formatter):
        if not self._cached_collator:
            self._cached_collator = ICollator(formatter.request.locale)
        s = super(IndexedLocaleAwareGetterColumn, self).getSortKey(item, formatter)
        return s and self._cached_collator.key(s)


class SchoolToolTableFormatter(object):
    implements(ITableFormatter)

    filter_widget = None
    batch = None

    def __init__(self, context, request):
        self.context, self.request = context, request

    def columns(self):
        title = GetterColumn(name='title',
                             title=u"Title",
                             getter=lambda i, f: i.title,
                             subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    def items(self):
        return self.context.values()

    def ommit(self, items, ommited_items):
        ommited_items = set(ommited_items)
        return [item for item in items
                if item not in ommited_items]

    def filter(self, items):
        # if there is no filter widget, we just return all the items
        if self.filter_widget:
            return self.filter_widget.filter(items)
        else:
            return items

    def sortOn(self):
        return (("title", False),)

    def setUp(self, items=None, ommit=[], filter=None, columns=None,
              columns_before=[], columns_after=[], sort_on=None, prefix="",
              formatters=[], table_formatter=table.FormFullFormatter,
              batch_size=10):

        self.filter_widget = queryMultiAdapter((self.context, self.request),
                                               IFilterWidget)

        self._table_formatter = table_formatter

        if not columns:
            columns = self.columns()

        if formatters:
            for formatter, column in zip(formatters, columns):
                column.cell_formatter = formatter

        self._columns = columns_before[:] + columns[:] + columns_after[:]

        if items is None:
            items = self.items()

        if not filter:
            filter = self.filter

        self._items = filter(self.ommit(items, ommit))

        self.prefix = prefix

        if batch_size == 0:
            batch_size = len(list(self._items))

        self.batch = Batch(self, batch_size=batch_size)

        self._sort_on = sort_on or self.sortOn()

    def extra_url(self):
        extra_url = ""
        if self.filter_widget:
            extra_url += self.filter_widget.extra_url()
        for key, value in self.request.form.items():
            if key.endswith("sort_on"):
                values = [urllib.quote(token) for token in value]
                extra_url += "&%s:tokens=%s" % (key, " ".join(values))
        return extra_url

    def render(self):
        formatter = self._table_formatter(
            self.context, self.request, self._items,
            columns=self._columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.cssClasses['table'] = 'data'
        return formatter()


class IndexedTableFormatter(SchoolToolTableFormatter):

    def columns(self):
        return [IndexedGetterColumn(name='title',
                                    title=u"Title",
                                    getter=lambda i, f: i.title,
                                    cell_formatter=url_cell_formatter,
                                    index='title')]

    def items(self):
        """Return a list of index dicts for all the items in the context container"""
        catalog = ICatalog(self.context)
        index = catalog['__name__']

        results = []
        for id, value in index.documents_to_values.items():
            results.append({
                    'context': self.context,
                    'id': id,
                    'catalog': catalog,
                    'key': value})
        return results


    def ommit(self, items, ommited_items):
        ommited_items = self.indexItems(ommited_items)
        ommited_ids = set([item['id'] for item in ommited_items])
        return [item for item in items
                if item['id'] not in ommited_ids]


    def indexItems(self, items):
        """Convert a list of objects to a list of index dicts"""
        int_ids = getUtility(IIntIds)
        catalog = ICatalog(self.context)
        results = []
        for item in items:
            results.append({
                    'context': self.context,
                    'id': int_ids.getId(item),
                    'catalog': catalog,
                    'key': item.__name__})
        return results

    def wrapColumn(self, column):
        """Wrap a normal column to work with index dicts"""
        original_renderCell = column.renderCell
        def unindexingRenderCell(item, formatter):
            item = item['context'][item['key']]
            return original_renderCell(item, formatter)
        column.renderCell = unindexingRenderCell

        if ISortableColumn.providedBy(column):
            original_getSortKey = column.getSortKey
            def unindexingGetSortKey(item, formatter):
                item = item['context'][item['key']]
                return original_getSortKey(item, formatter)
            column.getSortKey = unindexingGetSortKey

        return column

    def wrapColumns(self, columns):
        """Wrap all not indexed columns to work with index dicts"""
        wrapped_columns = []
        for column in columns:
            if IIndexedColumn.providedBy(column):
                wrapped_columns.append(column)
            else:
                wrapped_columns.append(self.wrapColumn(column))
        return wrapped_columns

    def setUp(self, **kwargs):
        items = kwargs.pop('items', None)
        columns = kwargs.pop('columns', None)
        columns_before = kwargs.pop('columns_before', [])
        columns_after = kwargs.pop('columns_after', [])

        if items is not None:
            items = self.indexItems(items)
        if columns is None:
            columns = self.columns()

        super(IndexedTableFormatter, self).setUp(items=items,
                columns=self.wrapColumns(columns),
                columns_before=self.wrapColumns(columns_before),
                columns_after=self.wrapColumns(columns_after),
                **kwargs)
