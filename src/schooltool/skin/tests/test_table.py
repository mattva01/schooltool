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
"""Table tests

$Id$
"""
import unittest

from zope.testing import doctest, doctestunit
from zope.testing.doctestunit import pprint

from schooltool.app.browser.testing import setUp, tearDown


def doctest_FilterWidget():
    """Doctest for FilterWidget.

    Let's create the FilterWidget:

        >>> from zope.publisher.browser import TestRequest
        >>> from schooltool.skin.table import FilterWidget
        >>> class ItemStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def __repr__(self):
        ...         return '<ItemStub %s>' % self.title
        >>> container = map(ItemStub, ['alpha', 'beta', 'lambda'])
        >>> request = TestRequest()
        >>> widget = FilterWidget(container, request)

    Rendering the widget returns whatever is returned by calling the template:

        >>> widget.template = lambda : 'I am a rendered widget!'
        >>> widget.render()
        'I am a rendered widget!'

    The state of the widget (whether it will filter the data or not)
    is determined by checking whether there is a query parameter in
    the request:

        >>> widget.active()
        False

        >>> request.form = {'SEARCH': 'lamb'}
        >>> widget.active()
        True

    The information that we got from the request can be appended to
    the url:

        >>> widget.extra_url()
        '&SEARCH=lamb'

    If there is no query in the request - an empty string get seturned:

        >>> request.form = {}
        >>> widget.extra_url()
        ''

    Filtering is done by skipping any entry that doesn't contain the
    query string in it's title:

        >>> request.form = {'SEARCH': 'lamb'}
        >>> widget.filter(widget.context)
        [<ItemStub lambda>]

   The search is case insensitive:

        >>> request.form = {'SEARCH': 'AlphA'}
        >>> widget.filter(widget.context)
        [<ItemStub alpha>]

    If clear search button is clicked, the form attribute is cleared,
    and all items are displayed:

        >>> request.form['CLEAR_SEARCH'] = 'Yes'

        >>> widget.filter(widget.context)
        [<ItemStub alpha>, <ItemStub beta>, <ItemStub lambda>]
        >>> request.form['SEARCH']
        ''
    """


def doctest_IndexedFilterWidget():
    """Doctest for IndexedFilterWidget.

    First we need a container with a catalog associated with it:

        >>> from zope.app.catalog.interfaces import ICatalog
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
        >>> from schooltool.skin.table import IndexedFilterWidget

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


def doctest_CheckboxColumn():
    """Tests for CheckboxColumn.

    Let's try creating a CheckboxColumn first:

        >>> from schooltool.skin.table import CheckboxColumn
        >>> column = CheckboxColumn("prefix", "name", "title")
        >>> column.title
        'title'
        >>> column.name
        'name'
        >>> column.prefix
        'prefix'

        >>> class ItemStub(object):
        ...     __name__ = "itemStub"
        >>> column.renderCell(ItemStub(), None)
        '<input type="checkbox" name="prefix.itemStub" id="prefix.itemStub" />'

    """


def doctest_label_cell_formatter_factory():
    """Tests for label_cell_formatter_factory.

    Let's create a label formatter:

        >>> from schooltool.skin.table import label_cell_formatter_factory
        >>> formatter = label_cell_formatter_factory()

    And render it:

        >>> class ItemStub(object):
        ...     __name__ = "item_stub"

        >>> formatter("Title of The Item", ItemStub(), "formatter")
        '<label for="item_stub">Title of The Item</label>'

    If we pass a prefix to the formatter factory, we get a label with
    the prefix before the item id:

        >>> formatter = label_cell_formatter_factory("some_prefix")
        >>> formatter("Title of The Item", ItemStub(), "formatter")
        '<label for="some_prefix.item_stub">Title of The Item</label>'

    """


def doctest_LocaleAwareGetterColumn():
    """Tests for LocaleAwareGetterColumn.

    Provide an interaction:

        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()

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
        >>> from zope.component import provideAdapter
        >>> provideAdapter(CollatorAdapterStub)

    Let's try creating a LocaleAwareGetterColumn first:

        >>> from schooltool.skin.table import LocaleAwareGetterColumn
        >>> lac = LocaleAwareGetterColumn()
        >>> class FormatterStub(object):
        ...     request = request
        >>> formatter = FormatterStub()
        >>> item = "Item"
        >>> lac.getSortKey(item, formatter)
        'CollatorKey(Item)'

    """


def doctest_IndexedGetterColumn():
    """Tests for IndexedGetterColumn.

    Indexed columnt requires an additional keyword argument (index)
    for it's constructor:

        >>> from schooltool.skin.table import IndexedGetterColumn
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

        >>> context = {}
        >>> catalog = {'title': index}
        >>> item = {'id': 5,
        ...         'context': context,
        ...         'catalog': catalog,
        ...         'key': 'peter'}

    The key of the index is used when getting the sort key of the
    column, so the only object touched is the index in the catalog,
    the Peter object is not used when sorting in any way:

        >>> column.getSortKey(item, None)
        'Peter'

    As we are rendering only a small set of items we are using the
    real object for that, because indexed information used for
    sorting/filtering might be different from the one that is being
    displayed:

        >>> class PersonStub(object):
        ...     def __init__(self, title):
        ...         self.title = title

        >>> context['peter'] = PersonStub('Mr. Peter')
        >>> column.renderCell(item, None)
        u'Mr. Peter'

    """


def doctest_SchoolToolTableFormatter():
    """Tests for SchoolToolTableFormatter.

    First some set up so we could render actual tables:

        >>> from zope.component import provideAdapter
        >>> from zope.interface import Interface
        >>> class ResourcePathStub(object):
        ...     def __init__(self, context):
        ...         pass
        ...     def __call__(self):
        ...         return ""
        >>> provideAdapter(ResourcePathStub,
        ...                adapts=[Interface],
        ...                provides=Interface,
        ...                name="zc.table")

    A table formatter is meant to make rendering of tables more
    standard and convenient. All you need to do is create a table
    formatter, though usualy it is an adapter on the container and
    request, but for the testing purposes we will create it directly:

        >>> from schooltool.skin.table import SchoolToolTableFormatter
        >>> container = {}
        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> formatter = SchoolToolTableFormatter(container, request)

        >>> from schooltool.skin.interfaces import ITableFormatter
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(ITableFormatter, formatter)
        True

    Before rendering the table we must set it up, we will provide a
    fake filter function so we would not have to set up FilterWidgets
    yet:

        >>> formatter.setUp()

        >>> print formatter.render()
        <BLANKLINE>
        <table class="data">
          <thead>
            <tr>
              <th>
        <BLANKLINE>
                    <span class="zc-table-sortable" ...>
                        Title</span> <img src="/sort_arrows_down.gif" ... alt="(descending)"/>
        <BLANKLINE>
              </th>
            </tr>
          </thead>
          <tbody>
          </tbody>
        </table>
        <input type="hidden" name=".sort_on:tokens" id=".sort_on" value="title" />
        <BLANKLINE>

    The table has no items though, but these items are sorted by title
    by default.


    Lets add some items to play around with:

        >>> class ItemStub(object):
        ...     def __init__(self, title, email):
        ...         self.title, self.email = title, email
        ...         self.__name__ = self.title.lower()

        >>> pete = container['pete'] = ItemStub('Pete', 'pete@example.com')
        >>> john = container['john'] = ItemStub('John', 'john@example.com')
        >>> toad = container['toad'] = ItemStub('Toad', 'toad@example.com')
        >>> frog = container['frog'] = ItemStub('Frog', 'frog@example.com')

    Now the table has all 4 of them:

        >>> formatter.setUp()
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            Frog
          </td>
        </tr>
        <tr class="even">
          <td>
            John
          </td>
        </tr>
        <tr class="odd">
          <td>
            Pete
          </td>
        </tr>
        <tr class="even">
          <td>
            Toad
          </td>
        </tr>
        </tbody>
        ...

    Lets provide a filter widget:

        >>> from schooltool.skin.interfaces import IFilterWidget
        >>> from zope.interface import implements
        >>> class FilterWidget(object):
        ...     implements(IFilterWidget)
        ...     def __init__(self, context, request):
        ...         self.request = request
        ...     def filter(self, list):
        ...         if 'SEARCH' in self.request:
        ...             return [item for item in list
        ...                     if self.request['SEARCH'] in item.title.lower()]
        ...         return list

        >>> from zope.interface import Interface
        >>> from zope.publisher.interfaces.browser import IBrowserRequest
        >>> provideAdapter(FilterWidget, adapts=[Interface, IBrowserRequest],
        ...                              provides=IFilterWidget)

    Now if we will put a SEARCH string into the request, we will only
    get part of the items:

        >>> request.form = {'SEARCH': 'o'}
        >>> formatter.setUp()
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            Frog
          </td>
        </tr>
        <tr class="even">
          <td>
            John
          </td>
        </tr>
        <tr class="odd">
          <td>
            Toad
          </td>
        </tr>
        </tbody>
        ...

    We can limit items that are being displayed ourselves as well:

        >>> request.form = {}
        >>> formatter.setUp(items=[frog, toad])
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            Frog
          </td>
        </tr>
        <tr class="even">
          <td>
            Toad
          </td>
        </tr>
        </tbody>
        ...

    We can provide custom columns to the formatter if we want:

        >>> from zc.table.column import GetterColumn
        >>> email = GetterColumn(name='email',
        ...                      title=u"Email",
        ...                      getter=lambda i, f: i.email,
        ...                      subsort=True)
        >>> from zope.interface import directlyProvides
        >>> from zc.table.interfaces import ISortableColumn
        >>> directlyProvides(email, ISortableColumn)
        >>> formatter.setUp(columns=[email], sort_on=(("email", False),))
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            frog@example.com
          </td>
        </tr>
        <tr class="even">
          <td>
            john@example.com
          </td>
        </tr>
        <tr class="odd">
          <td>
            pete@example.com
          </td>
        </tr>
        <tr class="even">
          <td>
            toad@example.com
          </td>
        </tr>
        </tbody>
        ...

    We could of course add the column after the title:

        >>> formatter.setUp(columns_after=[email])
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            Frog
          </td>
          <td>
            frog@example.com
          </td>
        </tr>
        <tr class="even">
          <td>
            John
          </td>
          <td>
            john@example.com
          </td>
        </tr>
        <tr class="odd">
          <td>
            Pete
          </td>
          <td>
            pete@example.com
          </td>
        </tr>
        <tr class="even">
          <td>
            Toad
          </td>
          <td>
            toad@example.com
          </td>
        </tr>
        </tbody>
        ...

    Now let's add a checkbox before the Title column:

        >>> from schooltool.skin.table import CheckboxColumn
        >>> checkbox = CheckboxColumn("delete", "delete", "Delete")
        >>> formatter.setUp(columns_before=[checkbox], columns_after=[email],
        ...                 items=[frog, john])
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            <input type="checkbox" name="delete.frog" id="delete.frog" />
          </td>
          <td>
            Frog
          </td>
          <td>
            frog@example.com
          </td>
        </tr>
        <tr class="even">
          <td>
            <input type="checkbox" name="delete.john" id="delete.john" />
          </td>
          <td>
            John
          </td>
          <td>
            john@example.com
          </td>
        </tr>
        </tbody>
        ...

    We can pass custom formatters for the default columns if we want:

        >>> from schooltool.skin.table import label_cell_formatter_factory
        >>> label_formatter = label_cell_formatter_factory("delete")
        >>> formatter.setUp(columns_before=[checkbox], columns_after=[email],
        ...                 items=[frog, john], formatters=[label_formatter])
        >>> print formatter.render()
        <BLANKLINE>
        ...
        <tbody>
        <tr class="odd">
          <td>
            <input type="checkbox" name="delete.frog" id="delete.frog" />
          </td>
          <td>
            <label for="delete.frog">Frog</label>
          </td>
          <td>
            frog@example.com
          </td>
        </tr>
        <tr class="even">
          <td>
            <input type="checkbox" name="delete.john" id="delete.john" />
          </td>
          <td>
            <label for="delete.john">John</label>
          </td>
          <td>
            john@example.com
          </td>
        </tr>
        </tbody>
        ...

    We can alter the batch size and starting point through the request

        >>> request.form = {'batch_start': '2',
        ...                 'batch_size': '2'}
        >>> formatter.setUp()
        >>> print formatter.render()
        <BLANKLINE>
        <table class="data">
          <thead>
            <tr>
              <th>
        <BLANKLINE>
                    <span class="zc-table-sortable" ...>
                        Title</span> <img src="/sort_arrows_down.gif" ... alt="(descending)"/>
        <BLANKLINE>
              </th>
            </tr>
          </thead>
          <tbody>
          <tr class="odd">
            <td>
              Pete
            </td>
          </tr>
          <tr class="even">
            <td>
              Toad
            </td>
          </tr>
          </tbody>
        </table>
        <input type="hidden" name=".sort_on:tokens" id=".sort_on" value="title" />
        <BLANKLINE>

    """


def doctest_IndexedTableFormatter_columns():
    """Tests for IndexedTableFormatter.columns.

    The default column for an indexed table formatter is an indexed
    getter column set to display the title of objects:

        >>> from schooltool.skin.table import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(None, None)
        >>> columns = formatter.columns()
        >>> columns
        [<schooltool.skin.table.IndexedGetterColumn object at ...>]

        >>> columns[0].title
        u'Title'
        >>> columns[0].index
        'title'

    """


def doctest_IndexedTableFormatter_items():
    """Tests for IndexedTableFormatter.items.

        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}
        >>> index = IndexStub()

        >>> from zope.app.catalog.interfaces import ICatalog
        >>> from zope.interface import implements
        >>> class CatalogStub(dict):
        ...     implements(ICatalog)
        ...     def __init__(self):
        ...         self['__name__'] = index
        ...     def __repr__(self):
        ...         return '<Catalog>'
        >>> catalog = CatalogStub()

        >>> class ContainerStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return catalog
        ...     def __repr__(self):
        ...         return '<Container>'

    The IndexedTableFormatter relies on catalog to list all the items
    so if there are no indexed items we get an empty list:

        >>> from schooltool.skin.table import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(ContainerStub(), None)
        >>> formatter.items()
        []

    Let's index some objects:

        >>> index.documents_to_values[1] = 'peter'
        >>> index.documents_to_values[2] = 'john'
        >>> index.documents_to_values[3] = 'ted'

    Now we should get a list of index dicts:

        >>> pprint(formatter.items())
        [{'catalog': <Catalog>,
          'context': <Container>,
          'id': 1,
          'key': 'peter'},
         {'catalog': <Catalog>,
          'context': <Container>,
          'id': 2,
          'key': 'john'},
         {'catalog': <Catalog>,
          'context': <Container>,
          'id': 3,
          'key': 'ted'}]

    """


def doctest_IndexedTableFormatter_indexItems():
    """Tests for IndexedTableFormatter.indexItems.

        >>> from zope.app.catalog.interfaces import ICatalog
        >>> class ContainerStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return '<Catalog>'
        ...     def __repr__(self):
        ...         return '<Container>'
        >>> from schooltool.skin.table import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(ContainerStub(), None)

    The formatter has a function that converts a list of objects into
    a list of index dicts that can be displayed by Indexed columns and
    filtered by indexed filter widgets:

        >>> class IntIdsStub(object):
        ...     def getId(self, obj):
        ...         return obj.id
        >>> from zope.app.intid.interfaces import IIntIds
        >>> from zope.component import provideUtility
        >>> provideUtility(IntIdsStub(), IIntIds)

        >>> class ItemStub(object):
        ...     def __init__(self, name, id):
        ...         self.__name__, self.id = name, id

        >>> items = [ItemStub('pete', 1), ItemStub('john', 2)]
        >>> pprint(formatter.indexItems(items))
        [{'catalog': '<Catalog>',
          'context': <Container>,
          'id': 1,
          'key': 'pete'},
         {'catalog': '<Catalog>',
          'context': <Container>,
          'id': 2,
          'key': 'john'}]

    """


def doctest_IndexedTableFormatter_wrapColumn():
    """Tests for IndexedTableFormatter.wrapColumn.

        >>> from schooltool.skin.table import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(None, None)

        >>> from zc.table.column import GetterColumn
        >>> column = GetterColumn(getter=lambda i, f: i.title)

    Normal columns accept objects and have a way of displaying the
    relevant data. For example this getter column when it gets a
    person passed will display its title:

        >>> class PersonStub(object):
        ...     def __init__(self, title):
        ...         self.title = title

        >>> item = PersonStub('Pete')
        >>> column.renderCell(item, None)
        u'Pete'

    But as our indexed table formatter is manipulating index dicts, we
    must wrap normal columns to use them on our data:

        >>> container = {'pete': item}
        >>> key = 'pete'
        >>> index_dict = {'context': container, 'key': key}
        >>> column = formatter.wrapColumn(column)
        >>> column.renderCell(index_dict, None)
        u'Pete'

    """


def doctest_IndexedTableFormatter_wrapColumns():
    """Tests for IndexedTableFormatter.wrapColumns.

        >>> from schooltool.skin.table import IndexedTableFormatter
        >>> formatter = IndexedTableFormatter(None, None)
        >>> formatter.wrapColumn = lambda column: "<Wrapped %s>" % column

    Wrap columns function wraps all the columns that do not implement
    IIndexedColumn and returns the new list of columns. If there were
    no columns passed to it - you get an empty list:

        >>> formatter.wrapColumns([])
        []

    Now let's pass it some real column stubs:

        >>> from zope.interface import implements
        >>> from schooltool.skin.interfaces import IIndexedColumn
        >>> class IndexedColumnStub(object):
        ...     implements(IIndexedColumn)
        ...     def __repr__(self):
        ...         return "<IndexedColumn>"
        >>> class NonIndexedColumnStub(object):
        ...     def __repr__(self):
        ...         return "<NonIndexedColumn>"

    We are getting all our non-indexed columns wrapped:

        >>> formatter.wrapColumns([IndexedColumnStub()])
        [<IndexedColumn>]

        >>> formatter.wrapColumns([IndexedColumnStub(), NonIndexedColumnStub()])
        [<IndexedColumn>, '<Wrapped <NonIndexedColumn>>']

    """


def doctest_IndexedTableFormatter_setUp():
    """Tests for IndexedTableFormatter.setUp.

        >>> from schooltool.skin.table import IndexedTableFormatter
        >>> from zope.publisher.browser import TestRequest
        >>> formatter = IndexedTableFormatter(None, TestRequest())

    Our IndexedTableFormatter can only work with index dicts and
    IndexedColumns, so before passing all the columns and items to the
    constructor of the parent class we must process them:

        >>> formatter.items = lambda: []
        >>> formatter.ommit = lambda list, ommit: list
        >>> formatter.wrapColumns = lambda list: list and list[:3] + ['wrapped'] + list[-1:] or []
        >>> formatter.columns = lambda: ['A', 'list', 'of', 'columns']
        >>> formatter.setUp()

    If no keyword parameters were passed, only the columns returned by
    the columns method get wrapped. We do this so that you could
    inherit from IndexedTableFormatter and provide your own columns
    method that has any columns you need (no performance penalty will
    occur unless you try sorting on an unindexed column):

        >>> formatter._columns
        ['A', 'list', 'of', 'wrapped', 'columns']

    If we have some after or before columns or if we pass some columns
    to the setUp they will be wrapped too:

        >>> formatter.wrapColumns = lambda list: list and ['<'] + list + ['>'] or []
        >>> formatter.setUp(columns_before=['before'],
        ...                 columns=['custom', 'columns'],
        ...                 columns_after=['after'])
        >>> formatter._columns
        ['<', 'before', '>', '<', 'custom', 'columns', '>', '<', 'after', '>']

        >>> formatter.indexItems = lambda list: ["Indexed %s" % item for item in list]

    If we pass some items to the formatter, they should be converted
    into index dicts:

        >>> formatter.setUp(items=["Pete", "John"])
        >>> formatter._items
        ['Indexed Pete', 'Indexed John']

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       globs={'pprint': doctestunit.pprint},
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
