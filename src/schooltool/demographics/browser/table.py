from zope.interface import implements, directlyProvides
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app import zapi
from zope.formlib import form
from zc.table.interfaces import IColumn, ISortableColumn
from zc.table import table, column
from zc.table.column import GetterColumn
from hurry.query.interfaces import IQuery
from hurry.query import query
from schooltool.batching import Batch
from schooltool.app.browser import ViewPreferences
from schooltool.demographics import interfaces

class TablePage(BrowserPage):
    """Base class to easily created table-driven views.

    Has support for batching and sorting.

    Subclass and define columns() and values() to make this work for
    your own data. columns() must return a list of zc.table column
    objects and values() must return an iterable of objects in the
    table.
    """
    
    __call__ = ViewPageTemplateFile('table.pt')

    def __init__(self, context, request):
        super(TablePage, self).__init__(context, request)
        self.batch_start = int(request.form.get('batch_start', 0))
        self.batch_size = int(request.form.get('batch_size', 10))
        self._cached_values = None
        
    def table(self):
        formatter = table.StandaloneSortFormatter(
            self.context, self.request, self.cached_values(),
            columns=self.columns(),
            batch_start=self.batch_start, batch_size=self.batch_size)
        return formatter()

    def batch(self):
        # XXX note that the schooltool.batching system is *only* used to
        # provide enough information for the batch navigation macros. We
        # actually use the zc.table system for the actual batching
        # bit
        return Batch(self.cached_values(), self.batch_start, self.batch_size)

    def cached_values(self):
        if self._cached_values is None:
            self._cached_values = self.values()
        return self._cached_values
    
    def values(self):
        raise NotImplementedError

    def columns(self):
        raise NotImplementedError
    
    def extraUrl(self):
        return self.sortOptions()

    def sortOptions(self):
        sort_on = self.request.form.get('sort_on', None)
        if not sort_on:
            return ''
        l = ['sort_on:list=%s' % o for o in sort_on]
        return '&' + '&'.join(l)
    
class PersonTable(TablePage):
    
    def columns(self):
        username = GetterColumn(
            name='username',
            title=u'Username',
            getter=lambda i, f: i.username,
            subsort=True)
        directlyProvides(username, ISortableColumn)
        full_name = GetterColumn(
            name='full_name',
            title=u'Full name',
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(full_name, ISortableColumn)
        modified = ModifiedColumn(
            name='modified',
            title=u'Modified',
            subsort=True)
        directlyProvides(modified, ISortableColumn)
        
        return [
            username,
            full_name,
            modified,
            EditColumn(name='edit', title=u'Edit'),
            DisplayColumn(name='display', title=u'Display')
            ]

    def values(self):
        return self.context.values()
    
class SearchTable(form.FormBase, PersonTable):
    form_fields = form.Fields(interfaces.ISearch, render_context=False)
    template = ViewPageTemplateFile('search.pt')
    
    def __init__(self, context, request):
        super(SearchTable, self).__init__(context, request)
        self.search_data = {}
   
    @form.action("submit")
    def handle_submit(self, action, data):
        self.search_data = data
        
    def values(self):
        if not self.search_data:
            return []
        q = zapi.getUtility(IQuery)
        return q.searchResults(
            query.Text(('demographics_catalog', 'fulltext'),
                       self.search_data['fulltext']))

    def extraUrl(self):
        result = super(SearchTable, self).extraUrl()
        return result + self.searchOptions()

    def searchOptions(self):
        result = []
        form = self.request.form
        for key in form:
            if key.startswith('form.'):
                result.append((key, form[key]))
        if not result:
            return ''
        return '&' + '&'.join(['%s=%s' % (key, value)
                               for (key, value) in result])
    
class EditColumn(column.Column):
    def renderCell(self, item, formatter):
        return '<a href="%s">Edit</a>' % (
            zapi.absoluteURL(item, formatter.request) + '/nameinfo/@@edit.html')

class DisplayColumn(column.Column):
    def renderCell(self, item, formatter):
        return '<a href="%s">Display</a>' % (
            zapi.absoluteURL(item, formatter.request) + '/nameinfo')

class ModifiedColumn(column.SortingColumn):
    _renderDatetime = None

    def getSortKey(self, item, formatter):
        return item.modified
    
    def renderCell(self, item, formatter):
        # cache _renderDatetime for performance
        if self._renderDatetime is None:
            self._renderDatetime = ViewPreferences(
                formatter.request).renderDatetime
        return self._renderDatetime(item.modified)
