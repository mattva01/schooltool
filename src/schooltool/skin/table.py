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
from zope.interface import implements
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate import ViewPageTemplateFile
from zc.table import table

from schooltool.batching import Batch
from schooltool.skin.interfaces import IFilterWidget


class TablePage(BrowserPage):
    """Base class to easily created table-driven views.

    Has support for batching and sorting.

    Subclass and define columns() and values() to make this work for
    your own data. columns() must return a list of zc.table column
    objects and values() must return an iterable of objects in the
    table.
    """

    __call__ = ViewPageTemplateFile('templates/table.pt')

    def __init__(self, context, request):
        super(TablePage, self).__init__(context, request)
        self.batch_start = int(request.form.get('batch_start', 0))
        self.batch_size = int(request.form.get('batch_size', 10))
        self._cached_values = None

    def table(self):
        formatter = table.StandaloneFullFormatter(
            self.context, self.request, self.cached_values(),
            columns=self.columns(),
            batch_start=self.batch_start, batch_size=self.batch_size,
            sort_on=self.sortOn())
        # set CSS class for the zc.table generated tables, to differentiate it
        # from other tables.
        formatter.cssClasses['table'] = 'data'
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

    def sortOn(self):
        """ Default sort on. """
        return ()


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
        return '&SEARCH=%s' % self.request.get('SEARCH')
