#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
"""Catalog indexing extensions for tabling."""

from persistent import Persistent

from zope.interface import implements, implementsOnly
from zope.interface import implementer, classImplements
from zope.component import adapter
from zope.component import getUtility, queryUtility
from zope.i18n.interfaces.locales import ICollator
from zope.container.contained import Contained
from zope.catalog.interfaces import ICatalogIndex
from zope.catalog.interfaces import ICatalog
from zope.intid.interfaces import IIntIds

from zc.catalog.index import ValueIndex
from zc.catalog.interfaces import IValueIndex, IExtentCatalog
from zc.table.interfaces import IColumn, ISortableColumn
from zc.table.column import GetterColumn

from schooltool.table.interfaces import IIndexedTableFormatter
from schooltool.table.interfaces import IIndexedColumn
from schooltool.table.table import FilterWidget
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.table.table import url_cell_formatter

from schooltool.common import SchoolToolMessage as _


class FilterImplementing(Persistent):
    def __init__(self, interface):
        self.interface = interface

    def __call__(self, index, docid, item):
        return bool(self.interface.providedBy(item))


class ConvertingIndexMixin(object):
    def __init__(self, converter=None, *args, **kwargs):
        assert converter is not None
        super(ConvertingIndexMixin, self).__init__(*args, **kwargs)
        self.value_factory = converter

    def index_doc(self, docid, texts):
        value = self.value_factory(texts)
        super(ConvertingIndexMixin, self).index_doc(docid, value)


class IConvertingIndex(IValueIndex, ICatalogIndex):
    """Index of values created by external converter."""


class ConvertingIndex(ConvertingIndexMixin, ValueIndex, Contained):
    implements(IConvertingIndex)


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


class IndexedGetterColumn(GetterColumn):
    implements(IIndexedColumn, ISortableColumn)

    def __init__(self, **kwargs):
        self.index = kwargs.pop('index')
        super(IndexedGetterColumn, self).__init__(**kwargs)

    def _sort(self, items, formatter, start, stop, sorters, multiplier):
        if self.subsort and sorters:
            items = sorters[0](items, formatter, start, stop, sorters[1:])
        else:
            items = list(items) # don't mutate original
        getSortKey = self.getSortKey

        # Patch the SortableColum._sort to use both cmp and key for sorting.
        # This reduces usage of getSortKey drastically on large datasets.
        items.sort(
            cmp=lambda a, b: multiplier*cmp(a, b),
            key=lambda item: getSortKey(item, formatter))

        return items

    def renderCell(self, item, formatter):
        item = queryUtility(IIntIds).getObject(item['id'])
        return super(IndexedGetterColumn, self).renderCell(item, formatter)

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


class IndexedTableFormatter(SchoolToolTableFormatter):
    implementsOnly(IIndexedTableFormatter)

    def columns(self):
        return [IndexedGetterColumn(name='title',
                                    title=_(u"Title"),
                                    getter=lambda i, f: i.title,
                                    cell_formatter=url_cell_formatter,
                                    index='title')]

    def items(self):
        """Return a list of index dicts for all the items in the context container"""
        catalog = ICatalog(self.context)
        if IExtentCatalog.providedBy(catalog):
            ids = list(catalog.extent)
        else:
            index = catalog.values()[0]
            ids = index.documents_to_values.keys()

        items = [{'id': id, 'catalog': catalog}
                 for id in ids]
        return items

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
                    'id': int_ids.getId(item),
                    'catalog': catalog})
        return results

    def setUp(self, **kwargs):
        items = kwargs.pop('items', None)
        if items is not None:
            items = self.indexItems(items)
        super(IndexedTableFormatter, self).setUp(
            items=items, **kwargs)

    def render(self):
        columns = [IIndexedColumn(c) for c in self._columns]
        formatter = self._table_formatter(
            self.context, self.request, self._items,
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.cssClasses['table'] = 'data'
        return formatter()


def makeIndexedColumn(mixins, column, *args, **kw):
    class_ = column.__class__
    new_class = type(
        '_indexed_%s' % class_.__name__,
        tuple(mixins) + (class_,),
        {})
    classImplements(new_class, IIndexedColumn)
    new_column = super(class_, new_class).__new__(new_class, *args, **kw)
    new_column.__dict__.update(dict(column.__dict__))
    return new_column


def unindex(indexed_item):
    return queryUtility(IIntIds).getObject(indexed_item['id'])


class RenderUnindexingMixin(object):
    def renderCell(self, indexed_item, formatter):
        return super(RenderUnindexingMixin, self).renderCell(
            unindex(indexed_item), formatter)


class SortUnindexingMixin(object):
    def getSortKey(self, indexed_item, formatter):
        super(SortUnindexingMixin, self).getSortKey(
            unindex(indexed_item), formatter)


@adapter(IColumn)
@implementer(IIndexedColumn)
def getIndexedColumn(column):
    column = makeIndexedColumn(
        [RenderUnindexingMixin], column)
    return column


@adapter(ISortableColumn)
@implementer(IIndexedColumn)
def getIndexedSortableColumn(column):
    column = makeIndexedColumn(
        [RenderUnindexingMixin, SortUnindexingMixin], column)
    return column

