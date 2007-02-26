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
        >>> column.isDisabled(ItemStub())
        False
        >>> column.renderCell(ItemStub(), None)
        '<input type="checkbox" name="prefix.itemStub" id="prefix.itemStub" />'

    Let's try to disable the check box if the name of the item is 'foo'

        >>> def isDisabled(item):
        ...     if item.__name__ == 'foo':
        ...         return True
        ...     return False
        >>> class ItemStub(object):
        ...     __name__ = "itemStub"
        >>> column = CheckboxColumn("prefix", "name", "title",
        ...                         isDisabled=isDisabled)
        >>> column.isDisabled(ItemStub())
        False
        >>> fooStub = ItemStub()
        >>> fooStub.__name__ = 'foo'
        >>> column.isDisabled(fooStub)
        True
        >>> column.renderCell(fooStub, None)
        ''
    """


def doctest_LabelColumn():
    """Tests for LabelColumn.

    Let's try creating a LabelColumn first:

        >>> class ColumnStub(object):
        ...     title = "The title"
        ...     def __init__(self):
        ...         self.__name__ = "name"
        ...     def renderCell(self, item, formatter):
        ...         return item.title
        >>> column = ColumnStub()

        >>> from schooltool.skin.table import LabelColumn
        >>> lc = LabelColumn(column, prefix='some_prefix')
        >>> lc._prefix
        'some_prefix'

    We want to be able to sort by this column:

        >>> from zc.table.interfaces import ISortableColumn
        >>> ISortableColumn.providedBy(lc)
        True

        >>> class ItemStub(object):
        ...     __name__ = "item_stub"
        ...     title = "Title of The Item"
        >>> column.renderCell(ItemStub(), None)
        'Title of The Item'

        >>> lc.renderCell(ItemStub(), None)
        '<label for="some_prefix.item_stub">Title of The Item</label>'

    If there is not prefix set, we plain __name__ of the item is used
    as the id:

        >>> lc._prefix = ""
        >>> lc.renderCell(ItemStub(), None)
        '<label for="item_stub">Title of The Item</label>'

    """


def doctest_URLColumn():
    """Tests for URLColumn.

    Let's try creating a URLColumn first:

        >>> class ColumnStub(object):
        ...     title = "The title"
        ...     def __init__(self):
        ...         self.__name__ = "name"
        ...     def renderCell(self, item, formatter):
        ...         return item.title
        >>> column = ColumnStub()

        >>> from schooltool.skin.table import LabelColumn
        >>> lc = LabelColumn(column, prefix='some_prefix')
        >>> lc._prefix
        'some_prefix'

    We want to be able to sort by this column:

        >>> from zc.table.interfaces import ISortableColumn
        >>> ISortableColumn.providedBy(lc)
        True

        >>> class ItemStub(object):
        ...     __name__ = "item_stub"
        ...     title = "Title of The Item"
        >>> column.renderCell(ItemStub(), None)
        'Title of The Item'

        >>> lc.renderCell(ItemStub(), None)
        '<label for="some_prefix.item_stub">Title of The Item</label>'

    If there is not prefix set, we plain __name__ of the item is used
    as the id:

        >>> lc._prefix = ""
        >>> lc.renderCell(ItemStub(), None)
        '<label for="item_stub">Title of The Item</label>'

    """


def doctest_LocaleAwareGetterColumn():
    """Tests for LocaleAwareGetterColumn.

    Provide an interaction:

        >>> from zope.security.management import restoreInteraction
        >>> from zope.security.management import endInteraction
        >>> from zope.security.management import newInteraction

        >>> endInteraction()
        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> newInteraction(request)

    Register collation adapter:

        >>> from zope.i18n.interfaces.locales import ICollator
        >>> from zope.i18n.interfaces.locales import ILocale
        >>> from zope.component import provideAdapter
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

    Let's try creating a LocaleAwareGetterColumn first:

        >>> from schooltool.skin.table import LocaleAwareGetterColumn
        >>> lac = LocaleAwareGetterColumn()
        >>> formatter = lambda s: s
        >>> item = "Item"
        >>> lac.getSortKey(item, formatter)
        'CollatorKey(Item)'

        >>> restoreInteraction()

    """

def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       globs={'pprint': doctestunit.pprint},
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
