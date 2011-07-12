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
from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.publisher.browser import BrowserView
from zope.component import getMultiAdapter, queryMultiAdapter
from zope.component import getUtility
from zope.component import adapter
from zope.component import getAdapter
from zope.authentication.interfaces import IAuthentication
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserPage
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.api import traverse

from zc.table.column import Column
from zc.table.table import FormFullFormatter

from schooltool.calendar.icalendar import convert_calendar_to_ical
from schooltool.app.browser.interfaces import IManageMenuViewletManager
from schooltool.app.interfaces import ISchoolToolAuthenticationPlugin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IAsset
from schooltool.skin.flourish.content import ContentProvider
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.person.interfaces import IPerson
from schooltool.table.table import CheckboxColumn
from schooltool.table.table import label_cell_formatter_factory
from schooltool.table.table import stupid_form_key
from schooltool.table.table import ImageInputColumn
from schooltool.table.interfaces import ITableFormatter
from schooltool.skin.skin import OrderedViewletManager
from schooltool.skin.breadcrumbs import CustomNameBreadCrumbInfo
from schooltool.skin import flourish
import schooltool.skin.flourish.page

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


class CSSFormatter(FormFullFormatter):

    def renderHeaders(self):
        result = []
        old_css_class = self.cssClasses.get('th')
        for col in self.visible_columns:
            self.cssClasses['th'] = col.name.replace('_', '-')
            result.append(self.renderHeader(col))
        self.cssClasses['th'] = old_css_class
        return ''.join(result)


class FlourishRelationshipViewBase(flourish.page.NoSidebarPage):

    content_template = ViewPageTemplateFile('templates/f_edit_relationships.pt')

    current_title = None
    available_title = None

    def add(self, item):
        collection = removeSecurityProxy(self.getCollection())
        collection.add(item)

    def remove(self, item):
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

    def getColumnsAfter(self, prefix):
        actions = {
            'add_item': {'label': _('Add'), 'icon': 'add-icon.png'},
            'remove_item': {'label': _('Remove'), 'icon': 'remove-icon.png'},
            }
        label, icon = actions[prefix]['label'], actions[prefix]['icon']
        action = ImageInputColumn(
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
                    changed = True
        if remove_item_submitted:
            for item in self.getSelectedItems():
                if remove_item_prefix + self.getKey(item) in self.request:
                    self.remove(removeSecurityProxy(item))
                    changed = True
        return changed

    def update(self):
        changes = self.applyFormChanges()
        if changes:
            self.request.response.redirect(self.request.getURL())
            return
        self.setUpTables()


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
    def url(self):
        person = self.authenticated_person
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        if person is None:
            return '%s/%s' % (app_url, 'login.html')
        return '%s/%s' % (app_url, 'logout.html')


class LoggedInNameViewlet(LoginNavigationViewlet):

    url = None

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


class FlourishLeaderView(FlourishRelationshipViewBase):

    current_title = _("Current responsible parties")
    available_title = _("Available responsible parties")

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


SchoolBreadcrumbInfo = CustomNameBreadCrumbInfo(_('school'))


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
        <span tal:content="view/title"></span>
    '''.strip())

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
            return ContentLink.title(self)
        return label


class ManageSiteNavLink(flourish.page.LinkViewlet):
    @property
    def url(self):
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        return '%s/settings' % app_url


class ManageSchoolNavLink(flourish.page.LinkViewlet):
    @property
    def url(self):
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        return '%s/manage' % app_url


class ManageSite(flourish.page.Page):
    pass


class ManageSchool(flourish.page.Page):
    pass


class ManageSiteLinks(flourish.page.RefineLinksViewlet):
    """Manage Site links viewlet."""


class ManageSchoolLinks(flourish.page.RefineLinksViewlet):
    """Manage School links viewlet."""


def getAppViewlet(context, request, view, manager, name):
    app = ISchoolToolApplication(None)
    viewlet = flourish.viewlet.lookupViewlet(
        app, request, view, manager, name=name)
    return viewlet
