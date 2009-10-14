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
from zope.component import queryMultiAdapter
from zope.security.proxy import removeSecurityProxy
from zope.app.dependable.interfaces import IDependable
from zope.traversing.browser.absoluteurl import absoluteURL

from zc.table import table
from zc.table import column
from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn

from schooltool.table.batch import Batch
from schooltool.table.interfaces import IFilterWidget
from schooltool.table.interfaces import ITableFormatter
from schooltool.table.interfaces import ICheckboxColumn

from schooltool.common import SchoolToolMessage as _


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


def label_cell_formatter_factory(prefix="", id_getter=None):
    if id_getter is None:
        id_getter = stupid_form_key
    def label_cell_formatter(value, item, formatter):
        return '<label for="%s">%s</label>' % (
            ".".join(filter(None, [prefix, id_getter(item)])), value)
    return label_cell_formatter


def stupid_form_key(item):
    """Simple form key that uses item's __name__.
    Very unsafe: __name__ is expected to be a unicode string that contains
    who knows what.
    """
    return item.__name__


def simple_form_key(item):
    """Unique form key for items contained within a single container."""
    name = getattr(item, '__name__', None)
    if name is None:
        return None
    key = unicode(name).encode('punycode')
    key = urllib.quote(key)
    return key


class CheckboxColumn(column.Column):
    """A columns with a checkbox

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ (or other value if form_id_builder is specified) of
    the item being displayed.
    """
    implements(ICheckboxColumn)

    def __init__(self, prefix, name=None, title=None,
                 isDisabled=None, id_getter=None):
        super(CheckboxColumn, self).__init__(name=name, title=title)
        if isDisabled:
            self.isDisabled = isDisabled
        self.prefix = prefix
        if id_getter is None:
            self.id_getter = stupid_form_key
        else:
            self.id_getter = id_getter

    def isDisabled(self, item):
        return False

    def renderCell(self, item, formatter):
        if not self.isDisabled(item):
            form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
            return '<input type="checkbox" name="%s" id="%s" />' % (
                form_id, form_id)
        else:
            return ''


class DependableCheckboxColumn(CheckboxColumn):
    """A column that displays a checkbox that is disabled if item has dependables.

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ of the item being displayed.
    """

    def __init__(self, *args, **kw):
        kw = dict(kw)
        self.show_disabled = kw.pop('show_disabled', True)
        super(DependableCheckboxColumn, self).__init__(*args, **kw)

    def renderCell(self, item, formatter):
        form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
        if self.hasDependents(item):
            if self.show_disabled:
                return '<input type="checkbox" name="%s" id="%s" disabled="disabled" />' % (form_id, form_id)
            else:
                return ''
        else:
            checked = form_id in formatter.request and 'checked="checked"' or ''
            return '<input type="checkbox" name="%s" id="%s" %s/>' % (
                form_id, form_id, checked)

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
    url = absoluteURL(item, formatter.request)
    return '<a href="%s">%s</a>' % (url, value)


class LocaleAwareGetterColumn(GetterColumn):
    """Getter columnt that has locale aware sorting."""

    implements(ISortableColumn)

    def getSortKey(self, item, formatter):
        collator = ICollator(formatter.request.locale)
        s = self.getter(item, formatter)
        return s and collator.key(s)


class NullTableFormatter(object):
    implements(ITableFormatter)

    filter_widget = None
    batch = None

    def __init__(self, context, request):
        self.context, self.request = context, request

    def setUp(self, **kwargs):
        pass

    def render(self):
        return ""


class SchoolToolTableFormatter(object):
    implements(ITableFormatter)

    filter_widget = None
    batch = None

    def __init__(self, context, request):
        self.context, self.request = context, request

    def columns(self):
        title = GetterColumn(name='title',
                             title=_(u"Title"),
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
              batch_size=25):

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

