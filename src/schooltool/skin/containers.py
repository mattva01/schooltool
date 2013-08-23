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
"""
SchoolTool skin containers
"""
import urllib

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter
from zope.publisher.browser import BrowserView
from zope.security.checker import canAccess
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.table.batch import IterableBatch
from schooltool.table.table import DependableCheckboxColumn
from schooltool.table.table import url_cell_formatter
from schooltool.table.interfaces import ITableFormatter


class ContainerView(BrowserView):
    """A base view for all containers.

    Subclasses must provide the following attributes that are used in the
    page template:

        `index_title` -- Title of the index page.

    """

    @property
    def container(self):
        return self.context

    def update(self):
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in self.container.values()
                       if searchstr in item.title.lower()]
            search_string = self.request['SEARCH'].encode('utf-8')
            extra_url = "&SEARCH=%s" % urllib.quote_plus(search_string)
        else:
            self.request.form['SEARCH'] = ''
            results = self.container.values()
            extra_url = ""

        self.batch = IterableBatch(results, self.request, sort_by='title',
                                   extra_url=extra_url)

    @property
    def canModify(self):
        return canAccess(self.container, '__delitem__')


class ContainerDeleteView(BrowserView):
    """A view for deleting items from container."""

    @property
    def container(self):
        return self.context

    def listIdsForDeletion(self):
        return [key for key in self.container
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.container[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)

    def update(self):
        if 'CONFIRM' in self.request:
            for key in self.listIdsForDeletion():
                del self.container[key]
            self.request.response.redirect(self.nextURL())
        elif 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.container, self.request)


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
        # XXX: Update table formatter.  It should be set up in __call__, after
        #      update(), if rendering the correct template.  But as update is
        #      called from template for some genuine reason, I'll just stick
        #      it here for now.  I hope to find some time to fix this later on.
        self.setUpTableFormatter(self.table)

    def canModify(self):
        return canAccess(self.context, '__delitem__')

    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)
