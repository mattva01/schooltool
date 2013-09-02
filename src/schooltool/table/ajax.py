#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
"""
AJAX-style tables.
"""

from zope.interface import implements
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy

import zc.resourcelibrary
from zc.table import table

from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool.table.interfaces import IFilterWidget
from schooltool.table.interfaces import IIndexedColumn
from schooltool.table.batch import TokenBatch
from schooltool.table.table import TableContent, FilterWidget
from schooltool.table.table import url_cell_formatter
from schooltool.table.table import SortUIHeaderMixin
from schooltool.table.table import HeaderFormatterMixin
from schooltool.table.table import StandaloneHeaderFormatterMixin
from schooltool.table.catalog import IndexedTableFormatter
from schooltool.table.catalog import IndexedFilterWidget
from schooltool.common import SchoolToolMessage as _


class AJAXSortHeaderMixin(SortUIHeaderMixin):

    html_id = None

    def _header_template(self, options):
        options = dict(options)
        options['containerID'] = self.html_id
        template = """
            <span class="%(css_class)s"
                  onclick="javascript: %(script_name)s(
                        '%(containerID)s', '%(columnName)s', '%(sort_on_name)s')">
                %(header)s</span>
        """
        return template % options


class AJAXFormSortFormatter(HeaderFormatterMixin,
                            AJAXSortHeaderMixin,
                            table.FormSortFormatter):
    script_name = 'ST.table.on_form_sort'


class AJAXStandaloneSortFormatter(StandaloneHeaderFormatterMixin,
                                  AJAXSortHeaderMixin,
                                  table.StandaloneSortFormatter):
    script_name = 'ST.table.on_standalone_sort'


class Table(flourish.ajax.CompositeAJAXPart, TableContent):

    no_default_url_cell_formatter = False

    container_wrapper = ViewPageTemplateFile('templates/f_ajax_table.pt')

    form_wrapper = InlineViewPageTemplate("""
      <form method="post" tal:attributes="action view/@@absolute_url;
                                          class view/form_class;
                                          id view/form_id">
        <tal:block replace="structure view/template" />
      </form>
    """)

    empty_message = u""
    form_class = None
    form_id = None

    table_formatter = AJAXFormSortFormatter

    inside_form = False # don't surround with <form> tag if inside_form

    @Lazy
    def html_id(self):
        return flourish.page.generic_viewlet_html_id(self, self.prefix)

    @Lazy
    def filter_widget(self):
        return self.get('filter')

    @Lazy
    def batch(self):
        return self.get('batch')

    def updateFormatter(self):
        if self._table_formatter is not None:
            return
        if self.no_default_url_cell_formatter:
            formatters = []
        else:
            formatters = [url_cell_formatter]
        self.setUp(formatters=formatters,
                   table_formatter=self.table_formatter,
                   batch_size=self.batch_size,
                   prefix=self.__name__,
                   css_classes={'table': 'data'})

    def update(self):
        self.updateFormatter()
        TableContent.update(self)
        flourish.ajax.CompositeAJAXPart.update(self)

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
            ignore_request=self.ignoreRequest,
            group_by_column=self.group_by_column,
            )
        formatter.html_id = self.html_id
        formatter.view = self
        formatter.cssClasses.update(dict(self.css_classes))
        return formatter

    def renderTable(self):
        formatter = self.makeFormatter()
        return formatter() if formatter is not None else ''

    def render(self, *args, **kw):
        content = ''
        if self.inside_form:
            content = self.template(*args, **kw)
        else:
            content = self.form_wrapper(*args, **kw)

        if self.fromPublication:
            return content

        zc.resourcelibrary.need('schooltool.table')
        return self.container_wrapper(content=content)


class TableFilter(flourish.viewlet.Viewlet, FilterWidget):
    implements(IFilterWidget)

    before = ("batch", "table")

    template = ViewPageTemplateFile("templates/f_filter.pt")
    title = _("Search")
    legend = _("Search")

    @property
    def source(self):
        return self.manager.source

    @property
    def ignoreRequest(self):
        return self.manager.ignoreRequest

    def filter(self, list):
        if self.ignoreRequest:
            return list
        return FilterWidget.filter(self, list)

    @property
    def script(self):
        return "return ST.table.on_form_submit(${html_id}, this);"


class TableBatch(flourish.viewlet.Viewlet):

    before = ("table", )

    batch = None

    def __init__(self, context, request, view, manager):
        flourish.viewlet.Viewlet.__init__(
            self, context, request, view, manager)

    @property
    def html_id(self):
        return flourish.page.generic_viewlet_html_id(self)

    def __iter__(self):
        return iter(self.batch)

    def update(self):
        if self.manager.prefix:
            self.name = "." + self.manager.prefix
        else:
            self.name = ""
        if self.manager.ignoreRequest:
            start = 0
            size = self.manager.batch_size
        else:
            start = int(self.request.get(
                    'start' + self.name, 0))
            size = int(self.request.get(
                    'size' + self.name, self.manager.batch_size))
        items = self.manager._items
        self.batch = TokenBatch(
            items, size=size, start=start)

    @property
    def needsBatch(self):
        batch = self.batch
        return (batch.size < batch.full_size and batch.needsBatch)

    def extend_token(self, token, **kw):
        token = dict(token)
        script = "return ST.table.on_batch_link('%s', '%s', %d, %d);" % (
            self.manager.html_id,
            self.name, token['start'],
            token['size'])
        token['onclick'] = script
        token.update(kw)
        return token

    @property
    def start(self):
        return self.batch.start

    @property
    def size(self):
        return self.batch.size

    @property
    def length(self):
        return len(self.batch)

    @property
    def full_size(self):
        return self.batch.full_size

    @Lazy
    def previous(self):
        token = self.batch.previous()
        if token is None:
            return None
        return self.extend_token(token, css_class='previous')

    @Lazy
    def next(self):
        token = self.batch.next()
        if token is None:
            return None
        return self.extend_token(token, css_class='next')

    @Lazy
    def show_all(self):
        if self.batch.size >= self.batch.full_size:
            return None
        script = "return ST.table.on_batch_link('%s', '%s', %d, %d);" % (
            self.manager.html_id,
            self.name, 0, self.full_size)
        return {'start': 0,
                'size': self.full_size,
                'items': self.batch.items,
                'onclick': script,
                'css_class': 'all'}

    def tokens(self):
        tokens = []
        for token in self.batch.tokens():
            css_class = "batch_page"
            css_class += token['current'] and ' current' or ''
            token = self.extend_token(token, css_class=css_class)
            tokens.append(token)
        return tokens


class TableTable(flourish.viewlet.Viewlet):

    def render(self, *args, **kw):
        return self.manager.renderTable()


class IndexedTable(IndexedTableFormatter, Table):

    @Lazy
    def filter_widget(self):
        return self.get('filter')

    def makeFormatter(self):
        if self._table_formatter is None:
            return ''
        columns = [IIndexedColumn(c) for c in self._columns]
        formatter = self._table_formatter(
            self.source, self.request, self._items,
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix,
            group_by_column=self.group_by_column)
        formatter.html_id = self.html_id
        formatter.view = self
        formatter.cssClasses.update(dict(self.css_classes))
        return formatter

    renderTable = Table.renderTable

    def render(self, *args, **kw):
        return Table.render(self, *args, **kw)


class IndexedTableFilter(TableFilter, IndexedFilterWidget):

    def filter(self, list):
        if self.ignoreRequest:
            return list
        return IndexedFilterWidget.filter(self, list)
