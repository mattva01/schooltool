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
import urllib

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter
from zope.security.checker import canAccess
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.table.batch import IterableBatch
from schooltool.table.table import url_cell_formatter
from schooltool.table.interfaces import ITableFormatter
from schooltool.skin.flourish.page import Page
from schooltool.common import SchoolToolMessage as _


class ContainerView(Page):
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
            search_string = self.request['SEARCH'].encode('UTF-8')
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


class ContainerDeleteView(Page):
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


class TableContainerView(Page):
    """A base view for containers that use zc.table to display items."""

    empty_message = _('There are none.')
    content_template = ViewPageTemplateFile('templates/table_container.pt')

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
        return canAccess(self.container, '__delitem__')
