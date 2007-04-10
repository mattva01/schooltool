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
"""
SchoolTool skin containers

$Id$
"""
from zope.app import zapi
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter
from zope.publisher.browser import BrowserView
from zope.security.checker import canAccess

from zc.table import table
from zc.table.column import GetterColumn

from schooltool.batching.batch import Batch
from schooltool.demographics.browser.table import DependableCheckboxColumn
from schooltool.skin.interfaces import IFilterWidget
from schooltool.skin.table import URLColumn


class ContainerView(BrowserView):
    """A base view for all containers.

    Subclasses must provide the following attributes that are used in the
    page template:

        `index_title` -- Title of the index page.

    """

    def update(self):
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.context.values()
                       if searchstr in item.title.lower()]
        else:
            self.request.form['SEARCH'] = ''
            results = self.context.values()

        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(results, start, size, sort_by='title')

    @property
    def canModify(self):
        return canAccess(self.context, '__delitem__')


class ContainerDeleteView(BrowserView):
    """A view for deleting items from container."""

    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)

    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                del self.context[key]
            self.request.response.redirect(self.nextURL())
        elif 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return zapi.absoluteURL(self.context, self.request)


class TableContainerView(BrowserView):
    """A base view for containers that use zc.table to display items.

    Subclasses must provide the following attributes that are used in the
    page template:

        `index_title` -- Title of the index page.

    """

    template = ViewPageTemplateFile('templates/table_container.pt')
    delete_template = ViewPageTemplateFile('templates/container_delete.pt')

    def __init__(self, context, request):
        self.request = request
        self.context = context

        self.filter_widget = queryMultiAdapter((self.context, self.request),
                                               IFilterWidget)
        self.results = self.filter(self.context.values())
        self.batch_start = int(self.request.get('batch_start', 0))
        self.batch_size = int(self.request.get('batch_size', 10))
        self.batch = Batch(self.results, self.batch_start, self.batch_size)

        if 'DELETE' in self.request:
            self.template = self.delete_template

    def __call__(self):
        # XXX update should be in here but as the container_delete
        # template is shared with the ContainerDeleteView and update
        # is called in the template we are not doing it here
        return self.template()

    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                del self.context[key]

    def filter(self, list):
        return self.filter_widget.filter(list)

    @property
    def canModify(self):
        return canAccess(self.context, '__delitem__')

    def columns(self):
        return [GetterColumn(name='title',
                             title=u"Title",
                             getter=lambda i, f: i.title,
                             subsort=True)]

    def sortOn(self):
        return (("title", False),)


    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)

    def renderTable(self):
        columns = []
        if self.canModify:
            columns.append(DependableCheckboxColumn(prefix="delete",
                                                    name='delete_checkbox',
                                                    title=u''))
        available_columns = map(lambda column: URLColumn(column, self.request),
                                self.columns())
        columns.extend(available_columns)
        formatter = table.FormFullFormatter(
            self.context, self.request, self.results,
            columns=columns,
            batch_start=self.batch_start, batch_size=self.batch_size,
            sort_on=self.sortOn())
        formatter.cssClasses['table'] = 'data'
        return formatter()
