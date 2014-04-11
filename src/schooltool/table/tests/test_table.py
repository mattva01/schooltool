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
"""Table tests
"""
import unittest
import doctest

from zope.interface import implements, Interface
from zope.component import provideAdapter
from zope.publisher.browser import TestRequest
from zope.traversing.browser.interfaces import IAbsoluteURL

from schooltool.app.browser.testing import setUp, tearDown


class FormatterStub(object):
    def __init__(self):
        self.request = TestRequest()


def doctest_FilterWidget():
    """Doctest for FilterWidget.

    Let's create the FilterWidget:

        >>> from zope.publisher.browser import TestRequest
        >>> from schooltool.table.table import FilterWidget
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


def doctest_CheckboxColumn():
    """Tests for CheckboxColumn.

    Let's try creating a CheckboxColumn first:

        >>> from schooltool.table.table import CheckboxColumn
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

        >>> from schooltool.table.table import label_cell_formatter_factory
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

    Create a formatter with a request:

        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> class FormatterStub(object):
        ...     request = request
        >>> formatter = FormatterStub()

    Register collation adapter:

        >>> from zope.i18n.interfaces.locales import ICollator
        >>> from zope.i18n.interfaces.locales import ILocale
        >>> from zope.component import adapts
        >>> class CollatorAdapterStub(object):
        ...     implements(ICollator)
        ...     adapts(ILocale)
        ...     def __init__(self, context):
        ...         self.context = context
        ...     def key(self, string):
        ...         return "CollatorKey(%s)" % string
        >>> provideAdapter(CollatorAdapterStub)

    Now when we try to get the sort key instead of getting the
    attribute of the object, we will get a collator key:

        >>> from schooltool.table.table import LocaleAwareGetterColumn
        >>> lac = LocaleAwareGetterColumn()
        >>> item = "Item"
        >>> lac.getSortKey(item, formatter)
        'CollatorKey(Item)'

    """


def doctest_ImageInputColumn():
    """Tests for ImageInputColumn.

    Let's try creating a ImageInputColumn first:

        >>> from schooltool.table.table import ImageInputColumn
        >>> column = ImageInputColumn("prefix", title="title",
        ...                           alt="alt", image="image.png")

        >>> column.title
        'title'
        >>> column.alt
        'alt'
        >>> column.name
        'title'
        >>> column.prefix
        'prefix'
        >>> column.image
        'image.png'

        >>> class ItemStub(object):
        ...     def __init__(self, name="itemStub"):
        ...         self.__name__ = name

        >>> from schooltool.common import CommonResourceURL
        >>> provideAdapter(CommonResourceURL)

    When resources are not found, column will render empty.

        >>> column.renderCell(ItemStub(), FormatterStub())
        ''

    Let's register a resource and a library with one resource.

        >>> class IStubResource(Interface):
        ...     pass

        >>> class ImageStub(object):
        ...     implements(IStubResource)
        ...     __parent__ = None
        ...     def __init__(self, name):
        ...         self.name = name
        ...
        ...     def __repr__(self):
        ...         return '<%s %r>' % (self.__class__.__name__, self.name)

        >>> class LibraryStub(object):
        ...     implements(IStubResource)
        ...     def __init__(self, name, resources):
        ...         self.name = name
        ...         self.resources = dict([(r.name, r) for r in resources])
        ...         for r in resources:
        ...             r.__parent__ = self
        ...
        ...     def get(self, name):
        ...         return self.resources.get(name)

        >>> def resourceURL(resource, request):
        ...     url = resource.name
        ...     if resource.__parent__:
        ...         url = '%s/%s' % (resource.__parent__.name, url)
        ...     return lambda: 'http://localhost/@@/%s' % url

        >>> def provideResource(resource):
        ...     provideAdapter(lambda x: resource, (TestRequest,),
        ...                    provides=Interface,
        ...                    name=resource.name)

        >>> image = ImageStub('image.png')
        >>> image2 = ImageStub('hello.png')
        >>> library = LibraryStub('images', [image2])

        >>> provideResource(image)
        >>> provideResource(library)

        >>> provideAdapter(resourceURL, (IStubResource, TestRequest),
        ...                provides=IAbsoluteURL)


    Now we can render our image directly.

        >>> print column.renderCell(ItemStub(), FormatterStub()) # doctest: +SKIP
        <button class="image" type="submit" name="prefix.itemStub"
                title="title" value="1">
          <img src="http://localhost/@@/image.png" alt="alt" />
        </button>

    Or have a column that renders an image from a library.

        >>> column = ImageInputColumn("prefix", title="title",
        ...                           alt="alt", library="images",
        ...                           image="hello.png")

        >>> print column.renderCell(ItemStub('otherItem'), FormatterStub())
        <button class="image" type="submit" name="prefix.otherItem"
                title="title" value="1">
          <img src="http://localhost/@@/images/hello.png" alt="alt" />
        </button>

    """


def doctest_SchoolToolTableFormatter():
    """Tests for SchoolToolTableFormatter.

    First some set up so we could render actual tables:

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

        >>> from schooltool.table.table import SchoolToolTableFormatter
        >>> container = {}
        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> formatter = SchoolToolTableFormatter(container, request)

        >>> from schooltool.table.interfaces import ITableFormatter
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
              <th class="title">
        <BLANKLINE>
                    <span class="zc-table-sortable zc-table-sort-asc-primary"
                          onclick="javascript: onSortClickForm(
                                'title', '.sort_on')">
                        Title</span>
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

        >>> from schooltool.table.interfaces import IFilterWidget
        >>> class FilterWidget(object):
        ...     implements(IFilterWidget)
        ...     def __init__(self, context, request):
        ...         self.request = request
        ...     def filter(self, list):
        ...         if 'SEARCH' in self.request:
        ...             return [item for item in list
        ...                     if self.request['SEARCH'] in item.title.lower()]
        ...         return list
        ...     def extra_url(self):
        ...         return "&search_info"

        >>> from zope.interface import Interface
        >>> from zope.publisher.interfaces.browser import IBrowserRequest
        >>> provideAdapter(FilterWidget, adapts=[Interface, IBrowserRequest],
        ...                              provides=IFilterWidget)

        >>> formatter = SchoolToolTableFormatter(container, request)

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

        >>> from schooltool.table.table import CheckboxColumn
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

        >>> from schooltool.table.table import label_cell_formatter_factory
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

        >>> formatter = SchoolToolTableFormatter(container, request)
        >>> formatter.setUp()

        >>> print formatter.render()
        <BLANKLINE>
        <table class="data">
          <thead>
            <tr>
              <th class="title">
        <BLANKLINE>
                    <span class="zc-table-sortable zc-table-sort-asc-primary" ...>
                        Title</span>
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
