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

from schooltool.batching.batch import Batch
from schooltool.skin.table import DependableCheckboxColumn
from schooltool.skin.table import url_cell_formatter
from schooltool.skin.interfaces import ITableFormatter


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
        self.table = queryMultiAdapter((context, request), ITableFormatter)

    def setUpTableFormatter(self, formatter):
        columns_before = []
        if self.canModify():
            columns_before = [DependableCheckboxColumn(prefix="delete",
                                                       name='delete_checkbox',
                                                       title=u'')]
        formatter.setUp(formatters=[url_cell_formatter],
                        columns_before=columns_before)

    def __call__(self):
        if 'DELETE' in self.request:
            return self.delete_template()

        self.setUpTableFormatter(self.table)
        # XXX update should be in here but as the container_delete
        # template is shared with the ContainerDeleteView and update
        # is called in the template we are not doing it here
        return self.template()

    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                del self.context[key]

    def canModify(self):
        return canAccess(self.context, '__delitem__')

    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)
