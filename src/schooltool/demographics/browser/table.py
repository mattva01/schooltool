from zope.interface import implements, directlyProvides
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app import zapi
from zc.table.interfaces import IColumn, ISortableColumn
from zc.table import table, column
from zc.table.column import GetterColumn
from schooltool.batching import Batch

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
        self._values = self.values()

    def table(self):
        formatter = table.StandaloneSortFormatter(
            self.context, self.request, self._values,
            columns=self.columns(),
            batch_start=self.batch_start, batch_size=self.batch_size)
        return formatter()

    def batch(self):
        # XXX note that the schooltool.batching system is *only* used to
        # provide enough information for the batch navigation macros. We
        # actually use the zc.table system for the actual batching
        # bit
        return Batch(self._values, self.batch_start, self.batch_size)

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
        full_name = GetterColumn(
            name='username',
            title=u'Username',
            getter=lambda i, f: i.username,
            subsort=True)
        directlyProvides(full_name, ISortableColumn)
        prefix = GetterColumn(
            name='full_name',
            title=u'Full name',
            getter=lambda i, f: i.nameinfo.full_name,
            subsort=True)
        directlyProvides(prefix, ISortableColumn)
        return [
            full_name,
            prefix,
            EditColumn(name='edit', title=u'Edit'),
            DisplayColumn(name='display', title=u'Display')
            ]

    def values(self):
        return self.context.values()

class EditColumn(column.Column):
    def renderCell(self, item, formatter):
        return '<a href="%s">Edit</a>' % (
            zapi.absoluteURL(item, formatter.request) + '/nameinfo/@@edit.html')

class DisplayColumn(column.Column):
    def renderCell(self, item, formatter):
        return '<a href="%s">Display</a>' % (
            zapi.absoluteURL(item, formatter.request) + '/nameinfo')
