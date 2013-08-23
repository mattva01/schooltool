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
"""Base code for table rendering and filtering.
"""
import pytz
import urllib

import zope.security
from zope.interface import implements
from zope.interface import directlyProvides
from zope.i18n import translate
from zope.browserpage import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import queryMultiAdapter
from zope.traversing.browser.absoluteurl import absoluteURL

import zc.table
import zc.table.table
from zc.table.interfaces import IColumnSortedItems
from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import stupid_form_key
from schooltool.skin import flourish
from schooltool.table.batch import Batch
from schooltool.table.interfaces import IFilterWidget
from schooltool.table.interfaces import ITableFormatter

# BBB: imports
from schooltool.common import simple_form_key
from schooltool.table.column import (
    getResourceURL,
    CheckboxColumn, DependableCheckboxColumn,
    DateColumn, LocaleAwareGetterColumn,
    ImageInputColumn, ImageInputValueColumn,
    )

from schooltool.common import SchoolToolMessage as _


class SortUIHeaderMixin(object):
    """Mixin for zc table formatters."""

    def _getColumnSortClass(self, column):
        if not IColumnSortedItems.providedBy(self.items):
            return ""
        col_name = column.name
        for n, (name, reversed) in enumerate(self.items.sort_on):
            if name == col_name:
                if n == 0:
                    return (reversed and "zc-table-sort-desc-primary" or
                                         "zc-table-sort-asc-primary")
                return (reversed and "zc-table-sort-desc" or
                                     "zc-table-sort-asc")
        return "zc-table-sort-asc"

    def _addSortUi(self, header, column):
        css_class = "zc-table-sortable "
        css_class += self._getColumnSortClass(column)
        columnName = column.name
        sort_on_name = zc.table.table.getSortOnName(self.prefix)
        script_name = self.script_name
        return self._header_template(locals())

    def _header_template(self, options):
        options = dict(options)
        template = """
            <span class="%(css_class)s"
                  onclick="javascript: %(script_name)s(
                        '%(columnName)s', '%(sort_on_name)s')">
                %(header)s</span>
            """
        return template % options


class HeaderFormatterMixin(object):

    group_by_column = None
    row = 0

    def __init__(self, context, request, *args, **kw):
        self.context = context
        self.request = request
        self.group_by_column = kw.pop('group_by_column', None)
        kw = self.updateSortParameters(context, request, *args, **kw)
        super(HeaderFormatterMixin, self).__init__(
            context, request, *args, **kw)

    def updateSortParameters(self, *args, **kw):
        fixed_sort_on = self.fixed_sort_on
        if fixed_sort_on:
            if kw.get('ignore_request'):
                kw['sort_on'] = self.getFixedSortOrder(
                    fixed_sort_on, kw.get('sort_on'))
            else:
                kw['sort_on'] = self.getRequestSortOn(
                    fixed_sort_on or (),
                    kw.get('sort_on') or (),
                    prefix=kw.get('prefix'))
                kw['ignore_request'] = True
        return kw

    @property
    def fixed_sort_on(self):
        """Always presort items with this fixed part."""
        if not self.group_by_column:
            return None
        return ((self.group_by_column, False), )

    def getFixedSortOrder(self, fixed_sort_on, sort_on):
        fixed_sort_on = tuple(fixed_sort_on or ())
        fixed = set([so[0] for so in fixed_sort_on])
        also_sort_on = tuple([
            so for so in (sort_on or ())
            if so[0] not in fixed
            ])
        return fixed_sort_on + also_sort_on

    def getRequestSortOn(self, fixed_sort_on, default_sort_on, prefix=None):
        sort_on_name = zc.table.table.getSortOnName(prefix)
        request_sort_on = zc.table.table.getRequestSortOn(
            self.request, sort_on_name) or default_sort_on
        sort_on = self.getFixedSortOrder(fixed_sort_on, request_sort_on)
        return sort_on

    def hasSubGroups(self):
        return (self.group_by_column is not None and
                self.group_by_column in self.columns_by_name)

    def getSubGroup(self, item):
        if not self.hasSubGroups():
            return None
        column = self.columns_by_name[self.group_by_column]
        return column.renderCell(item, self)

    def makeCSSClass(self, cls, column_name):
        cls = cls and cls.strip() or ''
        col_cls = column_name and column_name.replace('_', '-').strip() or ''
        if cls and col_cls:
            cls += ' '
        return cls + col_cls

    def renderHeaders(self):
        result = []
        old_css_class = self.cssClasses.get('th')
        for col in self.visible_columns:
            if self.group_by_column == col.name:
                continue
            self.cssClasses['th'] = self.makeCSSClass(old_css_class, col.name)
            result.append(self.renderHeader(col))
        self.cssClasses['th'] = old_css_class
        return ''.join(result)

    def renderRows(self):
        self.row = 0 # Hack to behave like AlternatingRowFormatterMixin

        if not self.hasSubGroups():
            return ''.join([self.renderRow(item) for item in self.getItems()])

        current_group = None
        result = []
        for item in self.getItems():
            group = self.getSubGroup(item)
            if group != current_group:
                result.append(self.renderSubHeader(item))
                current_group = group
            result.append(self.renderRow(item))
        return ''.join(result)

    def renderCells(self, item):
        return ''.join(
            [self.renderCell(item, col)
             for col in self.visible_columns
             if col.name != self.group_by_column])

    def renderSubHeader(self, item):
        column = self.columns_by_name[self.group_by_column]
        content = column.renderCell(item, self)
        css_class = self.makeCSSClass(self.cssClasses.get('th', ''), column.name)
        cell = '<tr><th class="%s" colspan="%d">%s</th></tr>' % (
            css_class,
            len(self.visible_columns),
            content)
        return cell


class StandaloneHeaderFormatterMixin(HeaderFormatterMixin):

    def getRequestSortOn(self, fixed_sort_on, default_sort_on, prefix=None):
        fixed_sort_on = self.getFixedSortOrder(fixed_sort_on, default_sort_on)
        result = super(StandaloneHeaderFormatterMixin, self).getRequestSortOn(
            fixed_sort_on, (), prefix=prefix)
        return result


class FormFullFormatter(HeaderFormatterMixin,
                        SortUIHeaderMixin,
                        zc.table.table.FormFullFormatter):
    pass


class FilterWidget(object):
    """A simple one field search widget.

    Filters out items in the container by their title.
    """
    implements(IFilterWidget)

    template = ViewPageTemplateFile('templates/filter.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def source(self):
        return self.context

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
            return '&SEARCH=%s' % urllib.quote(unicode(self.request.get('SEARCH')).encode('UTF-8'))
        return ''


def label_cell_formatter_factory(prefix="", id_getter=None):
    if id_getter is None:
        id_getter = stupid_form_key
    def label_cell_formatter(value, item, formatter):
        return '<label for="%s">%s</label>' % (
            ".".join(filter(None, [prefix, id_getter(item)])), value)
    return label_cell_formatter


def url_cell_formatter(value, item, formatter):
    url = absoluteURL(item, formatter.request)
    return '<a href="%s">%s</a>' % (url, value)


def translate_cell_formatter(value, item, formatter):
    if not value:
        return value
    return translate(value, formatter.request)


def datetime_formatter(value, item, formatter):
    if value is None:
        return ''
    app = ISchoolToolApplication(None)
    preferences = IApplicationPreferences(app)
    preferred_datetime_format = '%s %s' % (preferences.dateformat,
                                           preferences.timeformat)
    app_timezone = pytz.timezone(preferences.timezone)
    local_dt = value.astimezone(app_timezone)
    return local_dt.strftime(preferred_datetime_format)


class NullTableFormatter(object):
    implements(ITableFormatter)

    filter_widget = None
    batch = None

    def __init__(self, context, request):
        self.context, self.request = context, request

    def setUp(self, **kwargs):
        pass

    def makeFormatter(self):
        formatter = zc.table.table.Formatter(
            self.context, self.request, (), columns=())
        return formatter

    def render(self):
        return ""


_undefined = object()


class SchoolToolTableFormatter(object):
    implements(ITableFormatter)

    batch = None
    batch_size = 25
    _items = ()
    prefix = None

    css_classes = None
    _table_formatter = None
    visible_column_names = ()
    group_by_column = None

    def __init__(self, context, request):
        self.context, self.request = context, request

    @property
    def source(self):
        return self.context

    def columns(self):
        title = GetterColumn(name='title',
                             title=_(u"Title"),
                             getter=lambda i, f: i.title,
                             subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    def items(self):
        return self.source.values()

    def ommit(self, items, ommited_items):
        if not ommited_items:
            return items
        ommited_items = set(ommited_items)
        return [item for item in items
                if item not in ommited_items]

    @Lazy
    def batch(self):
        return Batch(self, batch_size=self.batch_size)

    @Lazy
    def filter_widget(self):
        widget = queryMultiAdapter((self.source, self.request),
                                   IFilterWidget)
        return widget

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
              formatters=[], table_formatter=FormFullFormatter,
              batch_size=25, css_classes=None,
              group_by_column=_undefined):

        self.prefix = prefix

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

        if batch_size == 0:
            batch_size = len(list(self._items))

        self.batch_size = batch_size
        self._sort_on = sort_on or self.sortOn() or ()

        if (group_by_column is not _undefined):
            self.group_by_column = group_by_column

        if css_classes:
            self.css_classes = css_classes
        else:
            self.css_classes = {'table': 'data'}

    def extra_url(self):
        extra_url = ""
        if self.filter_widget:
            extra_url += self.filter_widget.extra_url()
        for key, value in self.request.form.items():
            if key.endswith("sort_on"):
                values = [urllib.quote(token) for token in value]
                extra_url += "&%s:tokens=%s" % (key, " ".join(values))
        return extra_url

    def makeFormatter(self):
        if self._table_formatter is None:
            return None
        formatter = self._table_formatter(
            self.source, self.request, self._items,
            visible_column_names=self.visible_column_names,
            columns=self._columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix,
            group_by_column=self.group_by_column)
        formatter.cssClasses.update(dict(self.css_classes))
        formatter.view = self
        return formatter

    def render(self):
        formatter = self.makeFormatter()
        return formatter() if formatter is not None else ''


class TableContent(flourish.content.ContentProvider, SchoolToolTableFormatter):

    def __init__(self, context, request, view):
        flourish.content.ContentProvider.__init__(
            self, context, request, view)

    @property
    def source(self):
        return self.context

    def columns(self):
        title = GetterColumn(name='title',
                             title=_(u"Title"),
                             cell_formatter=url_cell_formatter,
                             getter=lambda i, f: i.title,
                             subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    def update(self):
        flourish.content.ContentProvider.update(self)
        if self._table_formatter is None:
            self.setUp()

    def makeFormatter(self):
        if self._table_formatter is None:
            return None
        formatter = self._table_formatter(
            self.source, self.request, self._items,
            visible_column_names=self.visible_column_names,
            columns=self._columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix,
            group_by_column=self.group_by_column)
        formatter.cssClasses.update(dict(self.css_classes))
        formatter.view = self
        return formatter

    render = SchoolToolTableFormatter.render



class TableContainerView(flourish.page.Page):
    """A base view for containers that use zc.table to display items."""

    empty_message = _('There are none.')
    content_template = ViewPageTemplateFile('templates/f_table_container.pt')
    done_link = ''

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def getColumnsBefore(self):
        return []

    def getColumnsAfter(self):
        return []

    def setUpTableFormatter(self, formatter):
        columns_before = self.getColumnsBefore()
        columns_after = self.getColumnsAfter()
        formatter.setUp(formatters=[url_cell_formatter],
                        columns_before=columns_before,
                        columns_after=columns_after)

    @property
    def container(self):
        return self.context

    def update(self):
        self.table = queryMultiAdapter((self.container, self.request),
                                       ITableFormatter)
        self.setUpTableFormatter(self.table)

    @property
    def deleteURL(self):
        container_url = absoluteURL(self.container, self.request)
        return '%s/%s' % (container_url, 'delete.html')

    def canModify(self):
        return zope.security.canAccess(self.container, '__delitem__')


class DoNotFilter(flourish.EmptyViewlet):

    def extra_url(self):
        return ''

    def filter(self, list):
        return list
