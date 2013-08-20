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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Catalog tests
"""
import unittest
import doctest

from pprint import pprint

from zope.intid.interfaces import IIntIds
from zope.component import provideUtility
from zope.component import provideAdapter

from schooltool.app.browser.testing import setUp, tearDown


def doctest_FilterImplementing():
    """Doctest for FilterImplementing

        >>> from zope.interface import implements, Interface
        >>> class IFoo(Interface):
        ...     pass
        >>> class Foo(object):
        ...     implements(IFoo)

        >>> from schooltool.table.catalog import FilterImplementing
        >>> filter = FilterImplementing(IFoo)
        >>> filter('index', 'docid', object())
        False
        >>> filter('index', 'docid', Foo())
        True

    """


def doctest_IndexedFilterWidget():
    """Doctest for IndexedFilterWidget.

    First we need a container with a catalog associated with it:

        >>> from zope.catalog.interfaces import ICatalog
        >>> from zope.interface import implements
        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}

    Our catalog has an index for title attribute:

        >>> class CatalogStub(dict):
        ...     implements(ICatalog)
        ...     def __init__(self):
        ...         self['title'] = IndexStub()

        >>> catalog = CatalogStub()

        >>> class ContainerStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return catalog

    Let's create the IndexedFilterWidget:

        >>> from zope.publisher.browser import TestRequest
        >>> from schooltool.table.catalog import IndexedFilterWidget

        >>> container = ContainerStub()
        >>> request = TestRequest()
        >>> widget = IndexedFilterWidget(container, request)

    Indexed filter widgets do not get items themselves, as filtering
    through normal object attributes would be just too slow, instead
    they get dicts with item int ids in them. All the information used
    for filtering is stored in the catalog associated with the context
    container:

        >>> catalog['title'].documents_to_values[5] = 'Lambda'
        >>> catalog['title'].documents_to_values[6] = 'Alpha'
        >>> catalog['title'].documents_to_values[7] = 'Beta'

        >>> items = [{'id': 5}, {'id': 6}, {'id': 7}]
        >>> request.form = {'SEARCH': 'lamb'}
        >>> widget.filter(items)
        [{'id': 5}]

   The search is case insensitive:

        >>> request.form = {'SEARCH': 'AlphA'}
        >>> widget.filter(items)
        [{'id': 6}]

    If clear search button is clicked, the form attribute is cleared,
    and all items are displayed:

        >>> request.form['CLEAR_SEARCH'] = 'Yes'

        >>> widget.filter(items)
        [{'id': 5}, {'id': 6}, {'id': 7}]
        >>> request.form['SEARCH']
        ''

    """


def doctest_IndexedGetterColumn():
    """Tests for IndexedGetterColumn.

    Indexed column requires an additional keyword argument (index)
    for it's constructor:

        >>> from schooltool.table.column import IndexedGetterColumn
        >>> column = IndexedGetterColumn(index='title', getter=lambda i, f: i.title)
        >>> column.index
        'title'

    Items used by this column are not ordinary objects, but rather
    index dicts:


        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}
        >>> index = IndexStub()
        >>> index.documents_to_values[5] = 'Peter'

        >>> int_ids = {}
        >>> class IntIdsStub(object):
        ...     def getObject(self, id):
        ...         return int_ids[id]
        >>> provideUtility(IntIdsStub(), IIntIds)

        >>> catalog = {'title': index}
        >>> item = {'id': 5,
        ...         'catalog': catalog}

    The key of the index is used when getting the sort key of the
    column, so the only object touched is the index in the catalog,
    the Peter object is not used when sorting in any way:

        >>> column.getSortKey(item, None)
        'Peter'

    """


def doctest_IndexedLocaleAwareGetterColumn():
    """Tests for IndexedLocaleAwareGetterColumn.

    Create a formatter with a request:

        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> class FormatterStub(object):
        ...     request = request
        >>> formatter = FormatterStub()

    Register collation adapter:

        >>> from zope.i18n.interfaces.locales import ICollator
        >>> from zope.i18n.interfaces.locales import ILocale
        >>> from zope.interface import implements
        >>> from zope.component import adapts
        >>> class CollatorAdapterStub(object):
        ...     implements(ICollator)
        ...     adapts(ILocale)
        ...     def __init__(self, context):
        ...         self.context = context
        ...     def key(self, string):
        ...         return "CollatorKey(%s)" % string
        >>> provideAdapter(CollatorAdapterStub)

    Indexed column requires an additional keyword argument (index)
    for it's constructor:

        >>> from schooltool.table.column import IndexedLocaleAwareGetterColumn
        >>> column = IndexedLocaleAwareGetterColumn(index='title',
        ...                                         getter=lambda i, f: i.title)
        >>> column.index
        'title'

    Items used by this column are not ordinary objects, but rather
    index dicts:

        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}
        >>> index = IndexStub()
        >>> index.documents_to_values[5] = 'Peter'

        >>> context = {}
        >>> catalog = {'title': index}
        >>> item = {'id': 5,
        ...         'catalog': catalog}

    The sort key for this column is not the title of the object, but
    rather a collator key derived from the title:

        >>> column.getSortKey(item, formatter)
        'CollatorKey(Peter)'

    """


def doctest_IndexedTableFormatter_columns():
    """Tests for IndexedTableFormatter.columns.

    The default column for an indexed table formatter is an indexed
    getter column set to display the title of objects:

        >>> from schooltool.table.catalog import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(None, None)
        >>> columns = formatter.columns()
        >>> columns
        [<schooltool.table.column.IndexedGetterColumn object at ...>]

        >>> columns[0].title
        u'Title'
        >>> columns[0].index
        'title'

    """


def doctest_IndexedTableFormatter_items():
    """Tests for IndexedTableFormatter.items.

        >>> from zope.catalog.interfaces import ICatalog
        >>> from zope.interface import implements
        >>> from zc.catalog.interfaces import IExtentCatalog
        >>> from schooltool.table.catalog import IndexedTableFormatter

        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}

        >>> class CatalogStub(dict):
        ...     implements(ICatalog)
        ...     def __init__(self, index):
        ...         self['__name__'] = index
        ...     def __repr__(self):
        ...         return '<Catalog>'

        >>> class ExtentCatalogStub(object):
        ...     implements(IExtentCatalog)
        ...     def __init__(self, extent):
        ...         self.extent = extent
        ...     def __repr__(self):
        ...         return '<ExtentCatalog>'

        >>> class ContainerStub(object):
        ...     def __init__(self, catalog):
        ...         self.catalog = catalog
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return self.catalog
        ...     def __repr__(self):
        ...         return '<Container>'

    The IndexedTableFormatter relies on catalog to list all the items.

    If catalog implements IExtentCatalog, it's extent is listed to obtain indexed
    item ids.

        >>> catalog = []
        >>> catalog = ExtentCatalogStub([])
        >>> formatter = IndexedTableFormatter(ContainerStub(catalog), None)
        >>> formatter.items()
        []

        >>> catalog.extent[:] = [1, 2, 3]
        >>> formatter.items()
        [{'catalog': <ExtentCatalog>,
          'id': 1},
         {'catalog': <ExtentCatalog>,
          'id': 2},
         {'catalog': <ExtentCatalog>,
          'id': 3}]

    For other catalogs, ids indexed in first index are used.

        >>> from schooltool.table.catalog import IndexedTableFormatter
        >>> index = IndexStub()
        >>> formatter = IndexedTableFormatter(
        ...     ContainerStub(CatalogStub(index)), None)
        >>> formatter.items()
        []

    Let's index some objects:

        >>> index.documents_to_values[1] = 'peter'
        >>> index.documents_to_values[2] = 'john'
        >>> index.documents_to_values[3] = 'ted'

    Now we should get a list of index dicts:

        >>> pprint(formatter.items())
        [{'catalog': <Catalog>,
          'id': 1},
         {'catalog': <Catalog>,
          'id': 2},
         {'catalog': <Catalog>,
          'id': 3}]

    """


def doctest_IndexedTableFormatter_indexItems():
    """Tests for IndexedTableFormatter.indexItems.

        >>> from zope.catalog.interfaces import ICatalog
        >>> class ContainerStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return '<Catalog>'
        ...     def __repr__(self):
        ...         return '<Container>'
        >>> from schooltool.table.catalog import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(ContainerStub(), None)

    The formatter has a function that converts a list of objects into
    a list of index dicts that can be displayed by Indexed columns and
    filtered by indexed filter widgets:

        >>> class IntIdsStub(object):
        ...     def getId(self, obj):
        ...         return obj.id
        >>> provideUtility(IntIdsStub(), IIntIds)

        >>> class ItemStub(object):
        ...     def __init__(self, name, id):
        ...         self.__name__, self.id = name, id

        >>> items = [ItemStub('pete', 1), ItemStub('john', 2)]
        >>> pprint(formatter.indexItems(items))
        [{'catalog': '<Catalog>',
          'id': 1},
         {'catalog': '<Catalog>',
          'id': 2}]

    """


def doctest_IndexedTableFormatter_setUp():
    """Tests for IndexedTableFormatter.setUp.

        >>> from schooltool.table.catalog import IndexedTableFormatter
        >>> from zope.publisher.browser import TestRequest
        >>> formatter = IndexedTableFormatter(None, TestRequest())

    Our IndexedTableFormatter can only work with index dicts and
    IndexedColumns, so before passing all the items to the
    constructor of the parent class we must process them:

        >>> formatter.indexItems = lambda list: [
        ...     {'id': "_id_%s" % item.lower(), 'catalog': "Catalog"}
        ...     for item in list]

    If we pass some items to the formatter now, they should be converted
    into index dicts:

        >>> formatter.setUp(items=["Pete", "John", "Bill"], ommit=["John"])
        >>> sorted(item['id'] for item in formatter._items)
        ['_id_bill', '_id_pete']

    """


def doctest_IndexedTableFormatter_render():
    """Tests for IndexedTableFormatter.setUp.

        >>> from schooltool.table.catalog import IndexedTableFormatter
        >>> from zope.publisher.browser import TestRequest

        >>> class ZCTableFormatterStub(object):
        ...     def __init__(self, context, request, items, **kw):
        ...         self.context = context
        ...         self.request = request
        ...         self.items = items
        ...         self.cssClasses = {}
        ...         self.args = dict(kw)
        ...
        ...     def __call__(self):
        ...         print 'Rendering', self.context
        ...         print 'Items:', self.items
        ...         print 'CSS classes:', sorted(self.cssClasses.items())
        ...         print 'Keyword arguments passed at creation:'
        ...         for k, v in sorted(self.args.items()):
        ...             print '%s:' % k, repr(v)

        >>> formatter = IndexedTableFormatter(
        ...     '<Context>', TestRequest())

     As IndexedTableFormatter works with index dicts as items, normal columns
     cannot render them (or use in any other way).  We adapt columns to
     IndexedColumns before passing to the rendering table formatter.

        >>> formatter.items = lambda: 'items'
        >>> formatter.ommit = lambda items, ommit: items + ' without ommitted'
        >>> formatter.setUp(
        ...     columns=['Column A', 'Column B'],
        ...     table_formatter=ZCTableFormatterStub)

        >>> from schooltool.table.interfaces import IIndexedColumn
        >>> provideAdapter(lambda column: 'Wrapped %s' % column,
        ...                adapts=[None],
        ...                provides=IIndexedColumn)

        >>> formatter.render()
        Rendering <Context>
        Items: items without ommitted
        CSS classes: [('table', 'data')]
        Keyword arguments passed at creation:
        batch_size: ...
        batch_start: ...
        columns: ['Wrapped Column A', 'Wrapped Column B']
        prefix: ...
        sort_on: ...

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
