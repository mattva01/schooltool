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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
AJAX-style tables.
"""

from zope.interface import implements
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy

from zc.table import table

from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool.table.interfaces import IFilterWidget
from schooltool.table.interfaces import IIndexedColumn
from schooltool.table.batch import TokenBatch
from schooltool.table.table import TableContent, FilterWidget
from schooltool.table.table import url_cell_formatter
from schooltool.table.catalog import IndexedTableFormatter
from schooltool.table.catalog import IndexedFilterWidget
from schooltool.common import SchoolToolMessage as _


class AJAXSortHeaderMixin(object):
    def _header_template(self, options):
        options = dict(options)
        options['containerID'] = self.html_id

        template = """
            <span class="zc-table-sortable"
                  onclick="javascript: %(script_name)s(
                        '%(containerID)s', '%(columnName)s', '%(sort_on_name)s')"
                    onMouseOver="javascript: this.className='sortable zc-table-sortable'"
                    onMouseOut="javascript: this.className='zc-table-sortable'">
                %(header)s</span> %(dirIndicator)s
        """
        return template % options


class AJAXFormSortFormatter(AJAXSortHeaderMixin,
                            table.FormSortFormatter):
    script_name = 'ST.table.on_form_sort'


class AJAXStandaloneSortFormatter(AJAXSortHeaderMixin,
                                  table.StandaloneSortFormatter):
    script_name = 'ST.table.on_standalone_sort'


class Table(flourish.ajax.CompositeAJAXPart, TableContent):

    container_wrapper = InlineViewPageTemplate("""
      <div tal:attributes="id view/html_id" i18n:domain="schooltool">
         <tal:block replace="structure options/content" />
      </div>
    """)

    form_wrapper = InlineViewPageTemplate("""
      <form method="post" tal:attributes="action view/@@absolute_url">
        <tal:block replace="structure view/template" />
      </form>
    """)

    empty_message = u""

    table_formatter = AJAXFormSortFormatter

    inside_form = False # don't surround with <form> tag if inside_form

    def __init__(self, *args, **kw):
        super(Table, self).__init__(*args, **kw)

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
        self.setUp(formatters=[url_cell_formatter],
                   table_formatter=self.table_formatter,
                   batch_size=self.batch_size,
                   prefix=self.__name__,
                   css_classes={'table': 'data st-table'})

    def update(self):
        self.updateFormatter()
        TableContent.update(self)

    def renderTable(self):
        if self._table_formatter is None:
            return ''
        formatter = self._table_formatter(
            self.source, self.request, self._items,
            columns=self._columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix,
            ignore_request=self.ignoreRequest,
            )
        formatter.html_id = self.html_id
        formatter.cssClasses.update(self.css_classes)
        return formatter()

    def render(self, *args, **kw):
        if self.inside_form:
            if self.fromPublication:
                return self.template(*args, **kw)
            else:
                return self.container_wrapper(
                    content=self.template(*args, **kw))
        if self.fromPublication:
            return self.form_wrapper(*args, **kw)
        else:
            return self.container_wrapper(
                content=self.form_wrapper(*args, **kw))


class TableFilter(flourish.viewlet.Viewlet, FilterWidget):
    implements(IFilterWidget)

    before = ("batch", "table")

    template = ViewPageTemplateFile("templates/f_filter.pt")
    title = _("Search")

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
        self.batch = TokenBatch(
            self.manager._items, size=size, start=start)

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

    def renderTable(self):
        if self._table_formatter is None:
            return ''
        columns = [IIndexedColumn(c) for c in self._columns]
        formatter = self._table_formatter(
            self.source, self.request, self._items,
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.html_id = self.html_id
        formatter.cssClasses.update(self.css_classes)
        return formatter()

    def render(self, *args, **kw):
        return Table.render(self, *args, **kw)


class IndexedTableFilter(TableFilter, IndexedFilterWidget):

    def filter(self, list):
        if self.ignoreRequest:
            return list
        return IndexedFilterWidget.filter(self, list)
