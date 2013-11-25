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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Catalog indexing extensions for tabling."""

from persistent import Persistent

from zope.interface import implements, implementsOnly
from zope.cachedescriptors.property import Lazy
from zope.component import getUtility
from zope.container.contained import Contained
from zope.catalog.interfaces import ICatalogIndex
from zope.catalog.interfaces import ICatalog
from zope.intid.interfaces import IIntIds

from zc.catalog.index import SetIndex, ValueIndex
from zc.catalog.interfaces import IValueIndex, ISetIndex
from zc.catalog.interfaces import IExtentCatalog

from schooltool.table.interfaces import IIndexedTableFormatter
from schooltool.table.interfaces import IIndexedColumn
from schooltool.table.table import FilterWidget
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.table.table import url_cell_formatter

# BBB: imports
from schooltool.table.column import IndexedGetterColumn
from schooltool.table.column import IndexedLocaleAwareGetterColumn
from schooltool.table.column import makeIndexedColumn
from schooltool.table.column import RenderUnindexingMixin, unindex

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


class ConvertingSetIndexMixin(object):
    def __init__(self, converter=None, *args, **kwargs):
        assert converter is not None
        super(ConvertingSetIndexMixin, self).__init__(*args, **kwargs)
        self.value_factory = converter

    def index_doc(self, docid, texts):
        value = self.value_factory(texts)
        super(ConvertingSetIndexMixin, self).index_doc(docid, value)


class IConvertingSetIndex(ISetIndex, ICatalogIndex):
    """Index of values created by external converter."""


class ConvertingSetIndex(ConvertingSetIndexMixin, SetIndex, Contained):
    implements(IConvertingSetIndex)


class IndexedFilterWidget(FilterWidget):

    search_index = 'title'

    @Lazy
    def catalog(self):
        return ICatalog(self.source)

    def filter(self, items):
        index = self.catalog[self.search_index]
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = []
            for item in items:
                title = index.documents_to_values[item['id']]
                if searchstr in title.lower():
                    results.append(item)
        else:
            self.request.form['SEARCH'] = ''
            results = items

        return results


class IndexedTableFormatter(SchoolToolTableFormatter):
    implementsOnly(IIndexedTableFormatter)

    def columns(self):
        return [IndexedGetterColumn(name='title',
                                    title=_(u"Title"),
                                    getter=lambda i, f: i.title,
                                    cell_formatter=url_cell_formatter,
                                    index='title')]

    @Lazy
    def catalog(self):
        return ICatalog(self.source)

    def items(self):
        """Return a list of index dicts for all the items in the context container"""
        catalog = self.catalog
        if IExtentCatalog.providedBy(catalog):
            ids = list(catalog.extent)
        else:
            index = catalog.values()[0]
            ids = index.documents_to_values.keys()

        items = [{'id': id, 'catalog': catalog}
                 for id in ids]
        return items

    def ommit(self, items, ommited_items):
        if not ommited_items:
            return items
        ommited_items = self.indexItems(ommited_items)
        ommited_ids = set([item['id'] for item in ommited_items])
        return [item for item in items
                if item['id'] not in ommited_ids]

    def indexItems(self, items):
        """Convert a list of objects to a list of index dicts"""
        int_ids = getUtility(IIntIds)
        catalog = self.catalog
        results = []
        for item in items:
            results.append({
                    'id': int_ids.getId(item),
                    'catalog': catalog})
        return results

    def makeItems(self, intids):
        catalog = self.catalog
        results = [
            {'id': iid,
             'catalog': catalog}
            for iid in intids]
        return results

    def getItem(self, indexed):
        int_ids = getUtility(IIntIds)
        return int_ids.queryObject(indexed['id'])

    def setUp(self, **kwargs):
        items = kwargs.pop('items', None)
        if items is not None:
            items = self.indexItems(items)
        super(IndexedTableFormatter, self).setUp(
            items=items, **kwargs)

    def makeFormatter(self):
        if self._table_formatter is None:
            return None
        columns = [IIndexedColumn(c) for c in self._columns]
        formatter = self._table_formatter(
            self.source, self.request, self._items,
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.cssClasses.update(dict(self.css_classes))
        return formatter

