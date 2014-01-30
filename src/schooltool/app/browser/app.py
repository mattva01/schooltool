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
SchoolTool application views.
"""
import re
import urllib

from zope.cachedescriptors.property import Lazy
from ZODB.FileStorage.FileStorage import FileStorageError
from ZODB.interfaces import IDatabase
from zope.location.location import LocationProxy
from zope.interface import implementer
from zope.interface import implements
from zope.interface import Interface
from zope.security.interfaces import IParticipation
from zope.security.management import getSecurityPolicy
from zope.security.proxy import removeSecurityProxy
from zope.app.form.utility import getWidgetsData, setUpWidgets
from zope.app.form.browser.add import AddView
from zope.app.form.browser.editview import EditView
from zope.app.form.interfaces import IInputWidget
from zope.app.form.interfaces import WidgetsError
from zope.app.applicationcontrol.browser.runtimeinfo import RuntimeInfoView
from zope.app.applicationcontrol.browser.zodbcontrol import ZODBControlView
from zope.app.applicationcontrol.interfaces import IApplicationControl
from zope.app.applicationcontrol.interfaces import IRuntimeInfo
from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.error.interfaces import IErrorReportingUtility
from zope.i18n import translate
from zope.publisher.browser import BrowserView
from zope.component import getMultiAdapter, queryMultiAdapter
from zope.component import getUtility
from zope.component import adapter, adapts
from zope.authentication.interfaces import IAuthentication
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserPage
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.schema import Int, Bool, Tuple, Choice
from z3c.form import form, field, button
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.interfaces import DISPLAY_MODE
from zc.table.table import FormFullFormatter

from schooltool.calendar.icalendar import convert_calendar_to_ical
from schooltool.app.browser.interfaces import IManageMenuViewletManager
from schooltool.app.interfaces import ISchoolToolAuthenticationPlugin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import IApplicationTabs
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IAsset
from schooltool.app.utils import vocabulary
from schooltool.skin.flourish.content import ContentProvider
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.person.interfaces import IPerson
from schooltool import table
from schooltool.table.table import CheckboxColumn
from schooltool.table.table import label_cell_formatter_factory
from schooltool.table.table import ImageInputColumn
from schooltool.table.interfaces import ITableFormatter
from schooltool.securitypolicy.crowds import inCrowd
from schooltool.skin.skin import OrderedViewletManager
from schooltool.skin import flourish
from schooltool.skin.flourish.form import Form
from schooltool.skin.flourish.form import Dialog
from schooltool.schoolyear.interfaces import ISchoolYearContainer

from schooltool.common import SchoolToolMessage as _


class ApplicationView(BrowserView):
    """A view for the main application."""

    def update(self):
        prefs = IApplicationPreferences(ISchoolToolApplication(None))
        if prefs.frontPageCalendar:
            url = absoluteURL(ISchoolToolCalendar(self.context),
                              self.request)
        else:
            url = absoluteURL(self.context,
                              self.request) + '/auth/@@login.html'
        self.request.response.redirect(url)



class BaseAddView(AddView):
    """Common functionality for adding groups and resources"""

    def nextURL(self):
        return absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class BaseEditView(EditView):
    """An edit view for resources and groups"""

    def update(self):
        if 'CANCEL' in self.request:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        else:
            status = EditView.update(self)
            if 'UPDATE_SUBMIT' in self.request and not self.errors:
                url = absoluteURL(self.context, self.request)
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
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]

    def getAvailableItemsContainer(self):
        """Returns the backend storage for available items."""
        raise NotImplementedError("Subclasses should override this method.")

    def createTableFormatter(self, **kwargs):
        prefix = kwargs['prefix']
        container = self.getAvailableItemsContainer()
        formatter = getMultiAdapter((container, self.request),
                                    ITableFormatter)
        columns_before = [CheckboxColumn(prefix=prefix, title="")]
        formatters = [label_cell_formatter_factory(prefix)]
        formatter.setUp(formatters=formatters,
                        columns_before=columns_before,
                        **kwargs)
        return formatter

    def getOmmitedItems(self):
        return self.getSelectedItems()

    def setUpTables(self):
        self.available_table = self.createTableFormatter(
            ommit=self.getOmmitedItems(),
            prefix="add_item")

        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=self.getSelectedItems(),
            prefix="remove_item",
            batch_size=0)

    def update(self):
        context_url = absoluteURL(self.context, self.request)

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

        self.setUpTables()


class CSSFormatter(table.table.SortUIHeaderMixin, FormFullFormatter):

    def renderHeaders(self):
        result = []
        old_css_class = self.cssClasses.get('th')
        for col in self.visible_columns:
            self.cssClasses['th'] = col.name.replace('_', '-')
            result.append(self.renderHeader(col))
        self.cssClasses['th'] = old_css_class
        return ''.join(result)


class RelationshipButton(ImageInputColumn):

    onclick = None
    button_class = None
    text_getter = None

    def __init__(self, prefix, title=None, name=None,
                 alt=None, library=None, image=None, id_getter=None,
                 onclick=None, text_getter=None):
        ImageInputColumn.__init__(self, prefix, title=title, name=name,
                                  alt=alt, library=library, image=image,
                                  id_getter=id_getter)
        self.text_getter = text_getter
        self.onclick = onclick
        classname = '-'.join(filter(None, (prefix, name))).lower()
        self.button_class = re.sub('[\W]+', '-', classname)

    def params(self, item, formatter):
        params = ImageInputColumn.params(self, item, formatter)
        params['tokens_name'] = ".".join(
            filter(None, ["displayed", self.prefix, "tokens"]))
        params['tokens_value'] = self.id_getter(item)
        params['onclick'] = self.onclick or ''
        params['css_class'] = self.button_class
        if self.text_getter is not None:
            params['text'] = self.text_getter(item)
        return params

    def template(self):
        template = '\n'.join([
                '<input name="%(tokens_name)s" value="%(tokens_value)s"'
                ' type="hidden" />',
                '<button class="image %(css_class)s" type="submit" name="%(name)s"'
                ' onclick="%(onclick)s"'
                ' title="%(title)s" value="1">',
                '<img src="%(src)s" alt="%(alt)s" />',
                '</button>'
                ])
        if self.text_getter is not None:
            template = '<span>%(text)s</span>\n' + template
        return template


class RelationshipCheckboxColumn(CheckboxColumn):

    def template(self):
        return '<input type="checkbox" name="%(tokens_name)s" value="%(tokens_value)s" />'

    def params(self, item, formatter):
        params = CheckboxColumn.params(self, item, formatter)
        params['tokens_name'] = ".".join(
            filter(None, ["displayed", self.prefix, "tokens"]))
        params['tokens_value'] = self.id_getter(item)
        return params


class RelationshipButtonTableMixin(object):

    button_prefix = ""
    extras_prefix = ""
    button_title = u""
    button_image = ''
    onclick = None
    empty_message = _('There are none.')

    ignoreRequest = False
    changed = False

    form_wrapper = InlineViewPageTemplate("""
      <form method="post" tal:attributes="action view/@@absolute_url">
        <tal:block replace="structure view/template" />
        <input type="hidden"
               tal:condition="view/batch"
               tal:attributes="value view/batch/start;
                               name string:${view/extras_prefix}.batch_start" />
        <input type="hidden"
               tal:condition="view/batch"
               tal:attributes="value view/batch/size;
                               name string:${view/extras_prefix}.batch_size" />
      </form>
    """)

    empty_template = InlineViewPageTemplate('''
      <h3 tal:content="view/empty_message" />
    ''')

    def submitItems(self, item):
        raise NotImplementedError

    @property
    def source(self):
        return self.view.getAvailableItemsContainer()

    def makeTextGetter(self):
        return None

    def columns(self):
        # XXX: evil!
        default = super(RelationshipButtonTableMixin, self).columns()

        action = RelationshipCheckboxColumn(
            self.button_prefix, name='action',
            title=self.button_title,
            id_getter=self.view.getKey)
        return [action] + default

    def update(self):
        super(RelationshipButtonTableMixin, self).update()
        self.applyChanges()

    def applyChanges(self):
        if not self.fromPublication:
            return
        item_prefix = self.button_prefix+'.'
        item_submitted = False
        for param in self.request.form:
            if param.startswith(item_prefix):
                item_submitted = True
        if item_submitted:
            self.changed = True
            self.submitItems()

    def nextURL(self):
        next_url = absoluteURL(self.view, self.request)
        next_url += '?'+self.extra_url()
        if self.batch:
            batch = self.batch
            if self.extras_prefix+'.batch_start' in self.request:
                next_url += "&start%s=%s" % (
                    batch.name, self.request[self.extras_prefix+'.batch_start'])
                if self.extras_prefix+'.batch_size' in self.request:
                    next_url += "&size%s=%s" % (
                        batch.name, self.request[self.extras_prefix+'.batch_size'])
        return next_url

    def renderTable(self):
        # XXX: evil!
        if (self._table_formatter is None or
            not self._items):
            return self.empty_template()
        return super(RelationshipButtonTableMixin, self).renderTable()

    def render(self, *args, **kw):
        if self.changed:
            next = self.nextURL()
            self.request.response.redirect(next)
            return ''
        # XXX: more evil!
        return super(RelationshipButtonTableMixin, self).render(*args, **kw)


class RelationshipAddTableMixin(RelationshipButtonTableMixin):

    button_prefix = "add_item"
    extras_prefix = "on_add"
    button_title = _('Add')
    button_image = 'add-icon.png'

    def submitItems(self):
        for item in self.view.getAvailableItems():
            key = '%s.%s' % (self.button_prefix, self.view.getKey(item))
            if key in self.request:
                self.view.add(removeSecurityProxy(item))

    def updateFormatter(self):
        ommit = self.view.getOmmitedItems()
        columns = self.columns()
        self.setUp(columns=columns,
                   ommit=ommit,
                   table_formatter=self.table_formatter,
                   batch_size=self.batch_size,
                   prefix=self.__name__,
                   css_classes={'table': 'data relationships-table'})


class RelationshipRemoveTableMixin(RelationshipButtonTableMixin):

    button_prefix = "remove_item"
    extras_prefix = "on_remove"
    button_title = _('Remove')
    button_image = 'remove-icon.png'

    def submitItems(self):
        for item in self.view.getSelectedItems():
            key = '%s.%s' % (self.button_prefix, self.view.getKey(item))
            if key in self.request:
                self.view.remove(removeSecurityProxy(item))

    def updateFormatter(self):
        items = self.view.getSelectedItems()
        columns = self.columns()
        self.setUp(columns=columns,
                   items=items,
                   table_formatter=self.table_formatter,
                   batch_size=self.batch_size,
                   prefix=self.__name__,
                   css_classes={'table': 'data relationships-table'})


class ResultsButton(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <div i18n:domain="schooltool">
        <p>
          <a href="#" onclick="return ST.table.select_all(event);" i18n:translate="" tal:attributes="id view/select_all_name">Select All</a> |
          <a href="#" onclick="return ST.table.select_none(event);" i18n:translate="" tal:attributes="id view/select_none_name">Select None</a>
        </p>
      </div>
      <div class="buttons">
        <input class="submit-widget button-field button-ok" type="submit"
               tal:attributes="name view/button_name;
                               value view/title" />
      </div>
    ''')

    @property
    def select_all_name(self):
        return self.manager.html_id + '-select-all'

    @property
    def select_none_name(self):
        return self.manager.html_id + '-select-none'

    def processSearchResults(self):
        if (self.button_name not in self.request or
            self.token_key not in self.request):
            return False
        item_ids = self.request[self.token_key]
        if not isinstance(item_ids, list):
            item_ids = [item_ids]
        changed = False
        relationship_view = self.manager.view
        for item in self.view_items(relationship_view):
            if relationship_view.getKey(item) in item_ids:
                self.process_item(relationship_view, item)
                changed = True
        return changed

    def update(self):
        self.processSearchResults()
        if self.button_name in self.request:
            self.manager.changed = True

    def render(self, *args, **kw):
        if not self.manager._items:
            return ''
        return self.template(*args, **kw)


class AddAllResultsButton(ResultsButton):

    title = _('Add')
    button_name = 'ADD_DISPLAYED_RESULTS'
    token_key = 'displayed.add_item.tokens'

    def view_items(self, relationship_view):
        return relationship_view.getAvailableItems()

    def process_item(self, relationship_view, item):
        relationship_view.add(removeSecurityProxy(item))


class RemoveAllResultsButton(ResultsButton):

    title = _('Remove')
    button_name = 'REMOVE_DISPLAYED_RESULTS'
    token_key = 'displayed.remove_item.tokens'

    def view_items(self, relationship_view):
        return relationship_view.getSelectedItems()

    def process_item(self, relationship_view, item):
        relationship_view.remove(removeSecurityProxy(item))


class EditRelationships(flourish.page.Page):

    content_template = ViewPageTemplateFile('templates/f_tabled_edit_relationships.pt')

    current_title = None
    available_title = None

    def add(self, item):
        collection = removeSecurityProxy(self.getCollection())
        if item not in collection:
            collection.add(item)

    def remove(self, item):
        collection = removeSecurityProxy(self.getCollection())
        if item in collection:
            collection.remove(item)

    def getCollection(self):
        """Return the backend storage for related objects."""
        raise NotImplementedError("Subclasses should override this method.")

    def getSelectedItems(self):
        """Return a sequence of items that are already selected."""
        return self.getCollection()

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]

    def getAvailableItemsContainer(self):
        """Returns the backend storage for available items."""
        raise NotImplementedError("Subclasses should override this method.")

    def getOmmitedItems(self):
        return self.getSelectedItems()

    def getKey(self, item):
        return item.__name__

    def nextURL(self):
        url = self.request.get('nexturl')
        if url is None:
            url = absoluteURL(self.context, self.request)
        return url


class FlourishRelationshipViewBase(flourish.page.Page):

    content_template = ViewPageTemplateFile('templates/f_edit_relationships.pt')

    current_title = None
    available_title = None

    def add(self, item):
        collection = removeSecurityProxy(self.getCollection())
        if item not in collection:
            collection.add(item)

    def remove(self, item):
        collection = removeSecurityProxy(self.getCollection())
        if item in collection:
            collection.remove(item)

    def getCollection(self):
        """Return the backend storage for related objects."""
        raise NotImplementedError("Subclasses should override this method.")

    def getSelectedItems(self):
        """Return a sequence of items that are already selected."""
        return self.getCollection()

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]

    def nextURL(self):
        url = self.request.get('nexturl')
        if url is None:
            url = absoluteURL(self.context, self.request)
        return url

    def getAvailableItemsContainer(self):
        """Returns the backend storage for available items."""
        raise NotImplementedError("Subclasses should override this method.")

    def getColumnsAfter(self, prefix):
        actions = {
            'add_item': {'label': _('Add'), 'icon': 'add-icon.png'},
            'remove_item': {'label': _('Remove'), 'icon': 'remove-icon.png'},
            }
        label, icon = actions[prefix]['label'], actions[prefix]['icon']
        action = RelationshipButton(
            prefix, name='action', title=label, alt=label,
            library='schooltool.skin.flourish',
            image=icon, id_getter=self.getKey)
        return [action]

    def createTableFormatter(self, **kwargs):
        container = self.getAvailableItemsContainer()
        formatter = getMultiAdapter((container, self.request),
                                    ITableFormatter)
        formatter.setUp(columns_after=self.getColumnsAfter(kwargs['prefix']),
                        table_formatter=CSSFormatter,
                        **kwargs)
        return formatter

    def getOmmitedItems(self):
        return self.getSelectedItems()

    def setUpTables(self):
        self.available_table = self.createTableFormatter(
            ommit=self.getOmmitedItems(),
            prefix="add_item")

        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=self.getSelectedItems(),
            prefix="remove_item",
            batch_size=0)

    def getKey(self, item):
        return item.__name__

    def applyFormChanges(self):
        changed = False
        add_item_prefix = 'add_item.'
        remove_item_prefix = 'remove_item.'
        add_item_submitted = False
        remove_item_submitted = False
        for param in self.request.form:
            if param.startswith(add_item_prefix):
                add_item_submitted = True
            elif param.startswith(remove_item_prefix):
                remove_item_submitted = True
        if add_item_submitted:
            for item in self.getAvailableItems():
                if add_item_prefix + self.getKey(item) in self.request:
                    self.add(removeSecurityProxy(item))
                    changed = 'added'
        if remove_item_submitted:
            for item in self.getSelectedItems():
                if remove_item_prefix + self.getKey(item) in self.request:
                    self.remove(removeSecurityProxy(item))
                    changed = 'removed'
        return changed

    def addSearchResults(self):
        key = 'displayed.add_item.tokens'
        if key not in self.request:
            return False
        add_ids = self.request[key]
        if not isinstance(add_ids, list):
            add_ids = [add_ids]
        changes = False
        for item in self.getAvailableItems():
            if self.getKey(item) in add_ids:
                self.add(removeSecurityProxy(item))
                changes = 'added'
        return changes

    def update(self):
        changes = self.applyFormChanges()
        self.setUpTables()

        if not changes:
            if 'ADD_DISPLAYED_RESULTS' in self.request:
                changes = self.addSearchResults()

        if changes:
            this_url = '%s?nexturl=%s' % (str(self.request.URL),
                                          urllib.quote(self.nextURL()))
            # XXX: this be evil hacks indeed
            if changes == 'added':
                this_url += self.available_table.extra_url()
                if self.available_table.batch:
                    batch = self.available_table.batch
                    if 'on_add.batch_start' in self.request:
                        this_url += "&batch_start%s=%s" % (
                            batch.name, self.request['on_add.batch_start'])
                    if 'on_add.batch_size' in self.request:
                        this_url += "&batch_size%s=%s" % (
                            batch.name, self.request['on_add.batch_size'])
            elif changes == 'removed':
                this_url += self.selected_table.extra_url()
                if self.selected_table.batch:
                    batch = self.selected_table.batch
                    if 'on_remove.batch_start' in self.request:
                        this_url += "&batch_start%s=%s" % (
                            batch.name, self.request['on_remove.batch_start'])
                    if 'on_remove.batch_size' in self.request:
                        this_url += "&batch_size%s=%s" % (
                            batch.name, self.request['on_remove.batch_size'])
            self.request.response.redirect(this_url)
            return


class ApplicationLoginView(BrowserView):
    """Backwards compatible login view that redirects to the actual login view."""

    def __call__(self):
        nexturl = absoluteURL(self.context,
                                   self.request) + '/auth/@@login.html'
        if 'nexturl' in self.request:
            nexturl += '?nexturl=' + self.request['nexturl']
        self.request.response.redirect(nexturl)


class ApplicationLogoutView(BrowserView):
    """Backwards compatible logout view that redirects to the actual logout view."""

    def __call__(self):
        nexturl = absoluteURL(self.context,
                              self.request) + '/auth/@@logout.html'
        self.request.response.redirect(nexturl)


class LoginView(BrowserView):
    """A login view"""

    error = None

    def __call__(self):
        self.update()
        return self.index()

    def update(self):
        if ('LOGIN' in self.request and 'username' in self.request and
            'password' in self.request):
            auth = getUtility(IAuthentication)
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
                    nexturl = absoluteURL(
                        person, self.request) + '/@@logindispatch'
                else:
                    nexturl = absoluteURL(ISchoolToolApplication(None),
                                               self.request)
                self.request.response.redirect(nexturl)


class LoginDispatchView(BrowserView):
    """Redirects to the proper starting page after login.

    By default the schooltool redirects to the persons calendar.
    """

    def __call__(self):
        nexturl = absoluteURL(
            ISchoolToolCalendar(self.context), self.request)
        self.request.response.redirect(nexturl)


class FlourishLoginDispatchView(BrowserView):
    implements(flourish.interfaces.IPage)

    title = None
    subtitle = None
    has_header = True
    page_class = ''
    container_class = ''
    template = None
    page_template = None
    content_template = None

    def update(self):
        app = ISchoolToolApplication(None)
        manager = queryMultiAdapter(
            (app, self.request, self),
            flourish.interfaces.IContentProvider, 'header_navigation')
        manager.collect()
        apptabs = removeSecurityProxy(IApplicationTabs(app))
        viewlet = manager.get(apptabs.default, None)
        if viewlet is not None and viewlet.enabled:
            nexturl = viewlet.url
        else:
            nexturl = absoluteURL(
                ISchoolToolCalendar(self.context), self.request)
        self.request.response.redirect(nexturl)

    def render(self, *args, **kw):
        return ''

    def __call__(self, *args, **kw):
        self.update()
        if self.request.response.getStatus() in [300, 301, 302, 303,
                                                 304, 305, 307]:
            return u''
        result = self.render(*args, **kw)
        return result


class LogoutView(BrowserView):
    """Clears the authentication creds from the session"""

    def __call__(self):
        auth = getUtility(IAuthentication)
        auth.clearCredentials(self.request)
        url = absoluteURL(ISchoolToolApplication(None),
                               self.request)
        self.request.response.redirect(url)


class LoginNavigationViewlet(flourish.page.LinkViewlet):

    @property
    def authenticated_person(self):
        principal = getattr(self.request, 'principal', None)
        if principal is None:
            return None
        if IUnauthenticatedPrincipal.providedBy(principal):
            return None
        return IPerson(principal, None)

    @property
    def title(self):
        person = self.authenticated_person
        if person is None:
            return _("Log in")
        return _("Log out")

    @property
    def login_url(self):
        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        return '%s/%s' % (app_url, 'login.html')

    @property
    def logout_url(self):
        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        return '%s/%s' % (app_url, 'logout.html')

    @property
    def url(self):
        person = self.authenticated_person
        if person is None:
            return self.login_url
        return self.logout_url


class LoginRedirectBackNavigationViewlet(LoginNavigationViewlet):

    @property
    def login_url(self):
        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        next_url = urllib.quote(str(self.request.URL))
        return '%s/%s?nexturl=%s' % (app_url, 'login.html', next_url)


class CalendarLoginNavigationViewlet(LoginNavigationViewlet):

    @property
    def login_url(self):
        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        if ISchoolToolApplication.providedBy(self.context.__parent__):
            return '%s/%s' % (app_url, 'login.html')
        next_url = urllib.quote(str(self.request.URL))
        return '%s/%s?nexturl=%s' % (app_url, 'login.html', next_url)


class LoggedInNameViewlet(LoginNavigationViewlet):

    @property
    def url(self):
        person = self.authenticated_person
        if not person:
            return None
        return absoluteURL(person, self.request)

    @property
    def title(self):
        person = self.authenticated_person
        if not person:
            return None
        title_content = queryMultiAdapter(
            (person, self.request, self.view),
            flourish.interfaces.IContentProvider,
            'title')
        if title_content is None:
            return ''
        return title_content.title


class BreadcrumbViewlet(flourish.viewlet.Viewlet):

    def render(self, *args, **kw):
        breadcrumbs = queryMultiAdapter(
            (self.context, self.request, self.view),
            flourish.interfaces.IContentProvider,
            'breadcrumbs')
        if breadcrumbs is None:
            return ''
        return breadcrumbs()


class ApplicationPreferencesView(BrowserView):
    """View used for editing application preferences."""

    __used_for__ = IApplicationPreferences

    error = None
    message = None

    schema = IApplicationPreferences

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        app = ISchoolToolApplication(None)
        prefs = self.schema(app)
        initial = {}
        for field in self.schema:
            initial[field] = getattr(prefs, field)
        setUpWidgets(self, self.schema, IInputWidget, initial=initial)

    def update(self):
        if 'CANCEL' in self.request:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        elif 'UPDATE_SUBMIT' in self.request:
            try:
                data = getWidgetsData(self, self.schema)
            except WidgetsError:
                return # Errors will be displayed next to widgets

            app = ISchoolToolApplication(None)
            prefs = self.schema(app)
            for field in self.schema:
                if field in data: # skip non-fields
                    setattr(prefs, field, data[field])


class FlourishApplicationPreferencesView(Form, form.EditForm):

    template = flourish.templates.Inherit(flourish.page.Page.template)
    fields = field.Fields(IApplicationPreferences)
    fields = fields.select('frontPageCalendar',
                           'timezone',
                           'timeformat',
                           'dateformat',
                           'weekstart',)
    label = None
    legend = _('Calendar settings')

    def getContent(self):
        return IApplicationPreferences(self.context)

    def update(self):
        form.EditForm.update(self)

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handle_edit_action(self, action):
        super(FlourishApplicationPreferencesView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        url = absoluteURL(self.context, self.request) + '/settings'
        return url

    def updateActions(self):
        super(FlourishApplicationPreferencesView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishSchoolNameEditView(FlourishApplicationPreferencesView):

    fields = field.Fields(IApplicationPreferences).select('title', 'logo')
    legend = _('School Name')

    def updateActions(self):
        super(FlourishSchoolNameEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self):
        super(FlourishSchoolNameEditView, self).updateWidgets()
        self.widgets['title'].label = _('Name')
        self.widgets['logo'].label = _('Logo')

    def nextURL(self):
        url = absoluteURL(self.context, self.request) + '/manage'
        return url


class ProbeParticipation:
    """A stub participation for use in hasPermissions."""
    implements(IParticipation)
    def __init__(self, principal):
        self.principal = principal
        self.interaction = None


def hasPermissions(permissions, object, principalid):
    """Test if the principal has access according to the security policy."""
    principal = getUtility(IAuthentication).getPrincipal(principalid)
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


class ManageView(BrowserView):
    pass


class ManageMenuViewletManager(OrderedViewletManager):
    implements(IManageMenuViewletManager)


class ViewRobot(BrowserPage):

    def __call__(self):
        return "User-agent: *\nDisallow: /"


@adapter(ISchoolToolApplication)
@implementer(ISchoolToolAuthenticationPlugin)
def getAuthentication(app):
    return LocationProxy(getUtility(ISchoolToolAuthenticationPlugin),
                         app, 'auth')


def getCharset(content_type, default="UTF-8"):
    """Get charset out of content-type

        >>> getCharset('text/xml; charset=latin-1')
        'latin-1'

        >>> getCharset('text/xml; charset=yada-yada')
        'yada-yada'

        >>> getCharset('text/xml; charset=yada-yada; fo=ba')
        'yada-yada'

        >>> getCharset('text/plain')
        'UTF-8'

        >>> getCharset(None)
        'UTF-8'

    """
    if not content_type:
        return default

    parts = content_type.split(";")
    if len(parts) == 0:
        return default

    stripped_parts = [part.strip() for part in parts]

    charsets = [part for part in stripped_parts
                if part.startswith("charset=")]

    if len(charsets) == 0:
        return default

    return charsets[0].split("=")[1]


class HTTPCalendarView(BrowserView):
    """Restive view for calendars"""

    def GET(self):
        data = "\r\n".join(convert_calendar_to_ical(self.context)) + "\r\n"
        request = self.request
        request.response.setHeader('Content-Type',
                                   'text/calendar; charset=UTF-8')
        request.response.setHeader('Content-Length', len(data))
        request.response.setStatus(200)
        return data

    def PUT(self):
        request = self.request

        for name in request:
            if name.startswith('HTTP_CONTENT_'):
                # Unimplemented content header
                request.response.setStatus(501)
                return ''

        body = self.request.bodyStream
        data = body.read()
        charset = getCharset(self.request.getHeader("Content-Type"))

        from schooltool.app.interfaces import IWriteCalendar
        adapter = IWriteCalendar(self.context)
        adapter.write(data, charset)
        return ''


class TitleView(BrowserView):

    def __call__(self):
        return self.context.title


class ContentTitle(ContentProvider):
    render = InlineViewPageTemplate('''
        <span tal:replace="structure view/title"></span>
    '''.strip())

    @property
    def title(self):
        __not_set = object()
        title = getattr(self.context, 'title', __not_set)
        if title is __not_set:
            return getattr(self.context, '__name__', None)
        return title


class ContentLink(ContentTitle):
    render = InlineViewPageTemplate('''
        <a tal:attributes="href view/url" tal:content="view/title"></a>
    '''.strip())

    def url(self):
        return absoluteURL(self.context, self.request)


class ContentLabel(ContentLink):
    def title(self):
        __not_set = object()
        label = getattr(self.context, 'label', __not_set)
        if label is __not_set:
            return super(ContentLabel, self).title
        return label


class ManageSiteBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    follow_crumb = None
    title = _('Server')

    @property
    def url(self):
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        return '%s/settings' % app_url


class ManageSite(flourish.page.Page):
    pass


class ServerActionsLinks(flourish.page.RefineLinksViewlet):
    """Server actions links viewlet."""


class ManageSchool(flourish.page.Page):
    pass


class ActiveSchoolYearContentMixin(object):

    @Lazy
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(ISchoolToolApplication(None))
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def has_schoolyear(self):
        return self.schoolyear is not None

    def url_with_schoolyear_id(self, obj, view_name=''):
        schoolyear = self.schoolyear
        schoolyear_id = schoolyear.__name__ if schoolyear is not None else ''
        params = {'schoolyear_id': schoolyear_id.encode('utf-8')}
        context_url = absoluteURL(obj, self.request)
        return '%s/%s?%s' % (context_url, view_name, urllib.urlencode(params))


class ManageItemDoneLink(flourish.viewlet.Viewlet,
                         ActiveSchoolYearContentMixin):
    template = InlineViewPageTemplate('''
      <h3 tal:define="can_manage view/can_manage"
          class="done-link"
          i18n:domain="schooltool">
        <tal:block condition="can_manage">
          <a tal:attributes="href view/manage_url"
             i18n:translate="">Done</a>
        </tal:block>
        <tal:block condition="not:can_manage">
          <a tal:attributes="href request/principal/schooltool:person/@@absolute_url"
             i18n:translate="">Done</a>
        </tal:block>
      </h3>
      ''')

    @property
    def can_manage(self):
        return flourish.canEdit(self.context) or \
               inCrowd(self.request.principal, 'administration', self.context)

    def manage_url(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='manage')


class ManageSiteLinks(flourish.page.RefineLinksViewlet):
    """Manage Site links viewlet."""


class CustomizeSchoolLinks(flourish.page.RefineLinksViewlet):
    """Customize School links viewlet."""


class SchoolAddLinks(flourish.page.RefineLinksViewlet):
    """School add links viewlet."""


class SchoolActionsLinks(flourish.page.RefineLinksViewlet):
    """School actions links viewlet."""


class AboutLinks(flourish.page.RefineLinksViewlet):
    """About links viewlet."""


def getAppViewlet(context, request, view, manager, name):
    app = ISchoolToolApplication(None)
    viewlet = flourish.viewlet.lookupViewlet(
        app, request, view, manager, name=name)
    return viewlet


class ApplicationControlLinks(flourish.page.RefineLinksViewlet):
    """Application Control links viewlet."""


class FlourishRuntimeInfoView(RuntimeInfoView, ZODBControlView):

    def dbSettings(self):
        result = {}
        database_settings = self.databases[0]
        result['dbSize'] = database_settings['size']
        result['dbName'] = database_settings['dbName']
        return result

    def update(self):
        pass


class FlourishServerSettingsOverview(flourish.page.Content,
                                     ZODBControlView,
                                     RuntimeInfoView):

    body_template = ViewPageTemplateFile(
        'templates/f_server_settings_overview.pt')

    @property
    def settings(self):
        result = {}
        database_settings = self.databases[0]
        result['dbSize'] = database_settings['size']
        result['dbName'] = database_settings['dbName']
        control_settings = (
            'Uptime',
            'SystemPlatform',
            'PythonVersion',
            'CommandLine',
            )
        runtimeInfo = self.runtimeInfo()
        for setting in control_settings:
            result[setting] = runtimeInfo.get(setting)
        return result

    def runtimeInfo(self):
        application_control = IApplicationControl(self.context)
        try:
            ri = IRuntimeInfo(application_control)
        except TypeError:
            formatted = dict.fromkeys(self._fields, self._unavailable)
            formatted["Uptime"] = self._unavailable
        else:
            formatted = self._getInfo(ri)
        return formatted


class PackageVersionsOverview(flourish.page.Content):

    body_template = ViewPageTemplateFile(
        'templates/package_versions.pt')


class FlourishCalendarSettingsOverview(flourish.form.FormViewlet):

    fields = field.Fields(IApplicationPreferences)
    fields = fields.select('frontPageCalendar', 'timezone', 'timeformat',
                           'dateformat', 'weekstart')
    template = ViewPageTemplateFile(
        'templates/f_calendar_settings_overview.pt')
    mode = DISPLAY_MODE


class PackDatabaseLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Pack Database')
        return translate(title, context=self.request)


class PackDatabaseView(Dialog):

    def initDialog(self):
        super(PackDatabaseView, self).initDialog()
        self.ajax_settings['dialog']['dialogClass'] = 'explicit-close-dialog'
        self.ajax_settings['dialog']['closeOnEscape'] = False

    def update(self):
        Dialog.update(self)
        if 'DONE' in self.request:
            url = absoluteURL(self.context, self.request) + '/settings'
            self.request.response.redirect(url)
            return
        days = 0
        db = getUtility(IDatabase, name='')
        try:
            db.pack(days=days)
            self.status = _('Database successfully packed.')
        except FileStorageError, err:
            self.status = _('There were errors while packing the database: ${error}',
                            mapping={'error': err})


class FlourishErrorsViewBase(flourish.page.Page):

    @property
    def error_utility(self):
        default_site = self.context.getSiteManager().get('default')
        return getUtility(IErrorReportingUtility, context=default_site)


class FlourishErrorsView(FlourishErrorsViewBase):

    def formatEntryValue(self, value):
        return len(value) < 70 and value or value[:70] + '...'

    def getLogEntries(self):
        return self.error_utility.getLogEntries()

    def settings(self):
        result = {}
        properties = self.error_utility.getProperties()
        for setting in ('keep_entries', 'ignored_exceptions'):
            result[setting] = properties[setting]
        if properties['copy_to_zlog']:
            result['copy_to_zlog'] = _('Yes')
        else:
            result['copy_to_zlog'] = _('No')
        return result


class FlourishErrorEntryView(FlourishErrorsViewBase):

    def update(self):
        entryId = self.request.get('id')
        if not entryId:
            self.request.response.redirect(self.nextURL())
            return
        self.entry = self.error_utility.getLogEntryById(entryId)
        if self.entry is not None:
            error_type = self.entry['type']
            self.subtitle = _('${type} Error', mapping={'type': error_type})

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/errors'


class IErrorsSettings(Interface):

    keep_entries = Int(
        title=_('Number of exceptions to show'))

    copy_to_zlog = Bool(
        title=_('Copy exceptions to the event log'),
        default=False)

    ignored_exceptions = Tuple(
        title=_('Ignored exception types'),
        value_type=Choice(vocabulary=vocabulary([
                    ('Unauthorized', 'Unauthorized'),
                    ('NotFound', 'NotFound')])),
        required=False)


class ErrorsSettingsAdapter(object):

    adapts(IErrorReportingUtility)
    implements(IErrorsSettings)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __getattr__(self, name):
        if name == 'ignored_exceptions':
            return getattr(self.context, '_ignored_exceptions')
        return getattr(self.context, name)

    def __setattr__(self, name, value):
        if name == 'ignored_exceptions':
            self.context._ignored_exceptions = value
            return
        setattr(self.context, name, value)


class FlourishErrorsConfigureView(Form, FlourishErrorsViewBase):

    template = flourish.templates.Inherit(flourish.page.Page.template)
    legend = _('Errors Settings')
    fields = field.Fields(IErrorsSettings)
    fields['ignored_exceptions'].widgetFactory = CheckBoxFieldWidget

    def getContent(self):
        return self.error_utility

    @button.buttonAndHandler(_('Submit'))
    def handle_submit_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        form.applyChanges(self, self.getContent(), data)
        self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        url = absoluteURL(self.context, self.request) + '/errors'
        return url

    def updateActions(self):
        super(FlourishErrorsConfigureView, self).updateActions()
        self.actions['submit'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class ErrorsBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    title = _('Errors')

    @property
    def url(self):
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        return '%s/errors' % app_url

    @property
    def follow_crumb(self):
        return ManageSiteBreadcrumb(self.context, self.request, self.view)


class FlourishHideUnhideTabsView(flourish.page.Page):

    ignore_tabs = ['manage_school', 'manage_site']

    @property
    def tabs(self):
        tabs = []
        apptabs = removeSecurityProxy(IApplicationTabs(self.context))
        manager = queryMultiAdapter(
            (self.context, self.request, self),
            flourish.interfaces.IContentProvider, 'header_navigation')
        manager.collect()
        for name in manager.order:
            if name in self.ignore_tabs:
                continue
            tabs.append({
                'title': removeSecurityProxy(manager[name]).title,
                'name': name,
                'checked': apptabs.get(name, True) and 'checked' or '',
                'default': name == apptabs.default and 'checked' or '',
                })
        return tabs

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        elif 'SUBMIT' in self.request:
            default = self.request.get('default_tab')
            visible = set(self.request.get('visible', []))
            visible.add(default)
            names = set([tab['name'] for tab in self.tabs])
            if default in names and visible.issubset(names):
                apptabs = removeSecurityProxy(IApplicationTabs(self.context))
                apptabs.default = default
                for name in names:
                    if name in visible:
                        if not apptabs.get(name, True):
                            apptabs[name] = True
                    else:
                        apptabs[name] = False
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/settings'


class TabsBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    title = _('Tabs')

    @property
    def url(self):
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        return '%s/hide_unhide_tabs.html' % app_url

    @property
    def follow_crumb(self):
        return ManageSiteBreadcrumb(self.context, self.request, self.view)


class FlourishAboutView(flourish.page.Page):

    pass


class SchoolLogoView(flourish.widgets.ImageView):

    @property
    def image(self):
        app = ISchoolToolApplication(None)
        prefs = IApplicationPreferences(app)
        return prefs.logo


class SchoolLogoViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate("""
    <div class="header">
      <div class="photo-display">
        <img tal:attributes="src view/url; alt view/title" />
      </div>
    </div>
    """)

    @property
    def enabled(self):
        app = ISchoolToolApplication(None)
        prefs = IApplicationPreferences(app)
        return prefs.logo is not None

    @property
    def url(self):
        app = ISchoolToolApplication(None)
        base = absoluteURL(app, self.request)
        return '%s/logo' % base

    def render(self, *args, **kw):
        if not self.enabled:
            return ""
        return self.template(*args, **kw)


class SchoolLoginLogoViewlet(SchoolLogoViewlet):

    template = InlineViewPageTemplate("""
    <div class="header">
      <div class="photo-display">
        <img tal:attributes="src view/url; alt view/title" />
      </div>
    </div>
    <div class="body">
      <div>
        <h3 tal:content="context/schooltool:app/title" />
      </div>
    </div>
    """)


class ManageSchoolViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        if not self.title:
            return False
        return inCrowd(self.request.principal, 'administration', context=self.context)


class NameSortingEditView(FlourishApplicationPreferencesView):

    fields = field.Fields(IApplicationPreferences).select('name_sorting')
    legend = _('Name Sorting')

    def updateActions(self):
        super(NameSortingEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self):
        super(NameSortingEditView, self).updateWidgets()
        self.widgets['name_sorting'].label = _('Sort by')

    def nextURL(self):
        url = absoluteURL(self.context, self.request) + '/settings'
        return url


class NameSortingBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    title = _('Name Sorting')

    @property
    def url(self):
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        return '%s/name_sorting.html' % app_url

    @property
    def follow_crumb(self):
        return ManageSiteBreadcrumb(self.context, self.request, self.view)
