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
SchoolTool application views.

$Id$
"""

from zc.table import table
from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn
from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import IParticipation
from zope.security.management import getSecurityPolicy
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.app.form.browser.add import AddView
from zope.app.form.browser.editview import EditView
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.publisher.browser import BrowserView
from zope.component import queryMultiAdapter
from zope.app.security.interfaces import IAuthentication
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import directlyProvides

from schooltool import SchoolToolMessage as _
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IAsset
from schooltool.batching import Batch
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonFactory
from schooltool.skin.interfaces import IFilterWidget
from schooltool.skin.table import CheckboxColumn
from schooltool.skin.table import label_cell_formatter_factory


class ApplicationView(BrowserView):
    """A view for the main application."""

    def update(self):
        prefs = IApplicationPreferences(getSchoolToolApplication())
        if prefs.frontPageCalendar:
            url = zapi.absoluteURL(ISchoolToolCalendar(self.context),
                                   self.request)
            self.request.response.redirect(url)


class BaseAddView(AddView):
    """Common functionality for adding groups and resources"""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class BaseEditView(EditView):
    """An edit view for resources and groups"""

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        else:
            status = EditView.update(self)
            if 'UPDATE_SUBMIT' in self.request and not self.errors:
                url = zapi.absoluteURL(self.context, self.request)
                self.request.response.redirect(url)
            return status


class RelationshipViewBase(BrowserView):
    """A base class for views that add/remove members from a relationship."""

    __call__ = ViewPageTemplateFile('templates/edit_relationships.pt')

    title = None
    current_title = None
    available_title = None

    def add(self, item):
        """Add an item to the list of selected items."""
        # Only those who can edit this section will see the view so it
        # is safe to remove the security proxy here
        collection = removeSecurityProxy(self.getCollection())
        collection.add(item)

    def remove(self, item):
        """Remove an item from selected items."""
        # Only those who can edit this section will see the view so it
        # is safe to remove the security proxy here
        collection = removeSecurityProxy(self.getCollection())
        collection.remove(item)

    def getCollection(self):
        """Return the backend storage for related objects."""
        raise NotImplementedError("Subclasses should override this method.")

    def getSelectedItems(self):
        """Return a sequence of items that are already selected."""
        return self.getCollection()

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        raise NotImplementedError("Subclasses should override this method.")

    def getAvailableItemsContainer(self):
        """Returns the backend storage for available items."""
        raise NotImplementedError("Subclasses should override this method.")

    def updateBatch(self, lst):
        self.batch_start = int(self.request.get('batch_start', 0))
        self.batch_size = int(self.request.get('batch_size', 10))
        self.batch = Batch(lst, self.batch_start, self.batch_size)

    def filter(self, list):
        return self.filter_widget.filter(list)

    def columnsForAvailable(self):
        title = GetterColumn(name='title',
                             title=u"Title",
                             getter=lambda i, f: i.title,
                             subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    columnsForSelected = columnsForAvailable

    def sortOn(self):
        return (("title", False),)

    def renderAvailableTable(self):
        prefix = "add_item"
        columns = [CheckboxColumn(prefix=prefix, name='add', title=u'')]
        available_columns = self.columnsForAvailable()
        available_columns[0].cell_formatter = label_cell_formatter_factory(prefix)
        columns.extend(available_columns)
        formatter = table.FormFullFormatter(
            self.context, self.request, self.filter(self.getAvailableItems()),
            columns=columns,
            batch_start=self.batch_start, batch_size=self.batch_size,
            sort_on=self.sortOn(),
            prefix="available")
        formatter.cssClasses['table'] = 'data'
        return formatter()

    def renderSelectedTable(self):
        prefix = "remove_item"
        columns = [CheckboxColumn(prefix=prefix, name='remove', title=u'')]
        selected_columns = self.columnsForSelected()
        selected_columns[0].cell_formatter = label_cell_formatter_factory(prefix)
        columns.extend(selected_columns)
        formatter = table.FormFullFormatter(
            self.context, self.request, self.getSelectedItems(),
            columns=columns,
            sort_on=self.sortOn(),
            prefix="selected")
        formatter.cssClasses['table'] = 'data'
        return formatter()

    def update(self):
        context_url = zapi.absoluteURL(self.context, self.request)

        self.filter_widget = queryMultiAdapter((self.getAvailableItemsContainer(),
                                                self.request),
                                               IFilterWidget)

        if 'ADD_ITEMS' in self.request:
            for item in self.getAvailableItems():
                if 'add_item.' + item.__name__ in self.request:
                    self.add(removeSecurityProxy(item))
        elif 'REMOVE_ITEMS' in self.request:
            for item in self.getSelectedItems():
                if 'remove_item.' + item.__name__ in self.request:
                    self.remove(removeSecurityProxy(item))
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)

        results = self.filter(self.getAvailableItems())
        self.updateBatch(results)


class LoginView(BrowserView):
    """A login view"""

    error = None

    def __call__(self):
        self.update()
        return self.index()

    def update(self):
        if ('LOGIN' in self.request and 'username' in self.request and
            'password' in self.request):
            auth = zapi.getUtility(IAuthentication)
            try:
                auth.setCredentials(self.request, self.request['username'],
                                    self.request['password'])
            except ValueError:
                self.error = _("Username or password is incorrect")
            else:
                principal = auth.authenticate(self.request)
                person = IPerson(principal, None)
                if 'nexturl' in self.request:
                    nexturl = self.request['nexturl']
                elif person is not None:
                    nexturl = zapi.absoluteURL(
                        ISchoolToolCalendar(person), self.request)
                else:
                    nexturl = zapi.absoluteURL(self.context, self.request)
                self.request.response.redirect(nexturl)


class LogoutView(BrowserView):
    """Clears the authentication creds from the session"""

    def __call__(self):
        auth = zapi.getUtility(IAuthentication)
        auth.clearCredentials(self.request)
        url = zapi.absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class ApplicationPreferencesView(BrowserView):
    """View used for editing application preferences."""

    __used_for__ = IApplicationPreferences

    error = None
    message = None

    schema = IApplicationPreferences

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        app = getSchoolToolApplication()
        prefs = self.schema(app)
        initial = {}
        for field in self.schema:
            initial[field] = getattr(prefs, field)
        setUpWidgets(self, self.schema, IInputWidget, initial=initial)

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        elif 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, self.schema)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            app = getSchoolToolApplication()
            prefs = self.schema(app)
            for field in self.schema:
                if field in data: # skip non-fields
                    setattr(prefs, field, data[field])


class ProbeParticipation:
    """A stub participation for use in hasPermissions."""
    implements(IParticipation)
    def __init__(self, principal):
        self.principal = principal
        self.interaction = None


def hasPermissions(permissions, object, principalid):
    """Test if the principal has access according to the security policy."""
    principal = zapi.getUtility(IAuthentication).getPrincipal(principalid)
    participation = ProbeParticipation(principal)
    interaction = getSecurityPolicy()(participation)
    return [interaction.checkPermission(permission, object)
            for permission in permissions]


class LeaderView(RelationshipViewBase):

    __used_for__ = IAsset

    title = _("Leaders")
    current_title = _("Current leaders")
    available_title = _("Available leaders")

    def getCollection(self):
        return self.context.leaders

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getAvailableItems(self):
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]

    def columnsForAvailable(self):
        return getUtility(IPersonFactory).columns()

    columnsForSelected = columnsForAvailable

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()
