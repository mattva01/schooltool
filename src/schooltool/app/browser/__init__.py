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
Browser views for the SchoolTool application.
"""
import calendar
import itertools

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPage
from zope.component import adapts, queryMultiAdapter
from zope.container.interfaces import IWriteContainer
from zope.size.interfaces import ISized
from zope.traversing.interfaces import IPathAdapter, ITraversable
from zope.security import checkPermission
from zope.security.interfaces import IPrincipal
from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.app.dependable.interfaces import IDependable
from zope.tales.interfaces import ITALESFunctionNamespace
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canAccess, canWrite

from pytz import timezone

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.flourish.interfaces import IContentProviders, IPageBase
from schooltool.person.interfaces import IPerson

from schooltool.common import SchoolToolMessage as _


class SchoolToolAPI(object):
    """TALES function namespace for SchoolTool specific actions.

    In a page template you can use it as follows:

        tal:define="app context/schooltool:app"

    """

    implements(IPathAdapter, ITALESFunctionNamespace)

    engine = None

    devmode = False

    def __init__(self, context):
        self.context = context

    def setEngine(self, engine):
        self.engine = engine

    @property
    def app(self):
        """Return the ISchoolToolApplication.

        Sample usage in a page template:

            <a tal:attributes="href context/schooltool:app/@@absolute_url">
               Front page
            </a>

        """
        return ISchoolToolApplication(None)

    @property
    def content(self):
        """Get traversable content providers for the context.

        Say, we have a viewlet manager named ExtraInfo, registered for persons.
        As viewlet managers implement IContentProvider, we can do:

        <div tal:repeat="person view/persons">
          <p tal:content="person/title"></p>
          <div tal:replace="structure person/schooltool:content/ExtraInfo"></div>
        </div>

        """
        if self.engine is None:
            return None
        vars = self.engine.vars
        context = self.context
        request = vars.get('request', None)
        view = vars.get('view', None)
        providers = queryMultiAdapter(
            (context, request, view),
            IContentProviders)
        if ITALESFunctionNamespace.providedBy(providers):
            providers.setEngine(self.engine)
        return providers

    @property
    def page_content(self):
        """Get traversable content providers for the context.

        Say, we have a viewlet manager named ExtraInfo, registered for persons.
        As viewlet managers implement IContentProvider, we can do:

        <div tal:repeat="person view/persons">
          <p tal:content="person/title"></p>
          <div tal:replace="structure person/schooltool:page_content/ExtraInfo"></div>
        </div>

        """
        if self.engine is None:
            return None
        vars = self.engine.vars
        context = self.context
        request = vars.get('request', None)
        page = view = vars.get('view', None)
        while (page is not None and
               not IPageBase.providedBy(page)):
            page = getattr(page, '__parent__', None)
        if page is None:
            page = view
            while (page is not None and
                   not IBrowserPage.providedBy(page)):
                page = getattr(page, '__parent__', None)
        providers = queryMultiAdapter(
            (context, request, page),
            IContentProviders)
        if ITALESFunctionNamespace.providedBy(providers):
            providers.setEngine(self.engine)
        return providers

    @property
    def person(self):
        """Adapt context to IPerson, default to None.

        Sample usage in a page template:

            <a tal:define="person request/principal/schooltool:person"
               tal:condition="person"
               tal:attributes="person/calendar/@@absolute_url">
               My calendar
            </a>

        """
        return IPerson(self.context, None)

    @property
    def authenticated(self):
        """Check whether context is an authenticated principal.

        Sample usage in a page template:

            <tal:span tal:define="user request/principal"
                      tal:condition="user/schooltool:authenticated"
                      tal:replace="user/title">
              User title
            </tal:span>
            <tal:span tal:define="user request/principal"
                      tal:condition="not:user/schooltool:authenticated">
              Anonymous
            </tal:span>

        """
        if self.context is None: # no one is logged in
            return False
        if not IPrincipal.providedBy(self.context):
            raise TypeError("schooltool:authenticated can only be applied"
                            " to a principal but was applied on %r" % self.context)
        return not IUnauthenticatedPrincipal.providedBy(self.context)

    @property
    def preferences(self):
        """Return ApplicationPreferences for the SchoolToolApplication.

        Sample usage in a page template:

          <div tal:define="preferences context/schooltool:preferences">
            <b tal:content="preferences/title"></b>
          </div>

        """
        return IApplicationPreferences(self.app)

    @property
    def has_dependents(self):
        """Check whether an object has dependents (via IDependable).

        Objects that have dependents cannot be removed from the system.

        Sample usage in a page template:

          <input type="checkbox" name="delete"
                 tal:attributes="disabled obj/schooltool:has_dependents" />

        """
        # We cannot adapt security-proxied objects to IDependable.  Unwrapping
        # is safe since we do not modify anything, and the information whether
        # an object can be deleted or not is not classified.
        unwrapped_context = removeSecurityProxy(self.context)
        dependable = IDependable(unwrapped_context, None)
        if dependable is None:
            return False
        else:
            return bool(dependable.dependents())

    def can_view(self):
        return checkPermission("schooltool.view", self.context)

    def can_edit(self):
        return checkPermission("schooltool.edit", self.context)

    def can_delete(self):
        container = self.context.__parent__
        if not IWriteContainer.providedBy(container):
            raise NotImplementedError()
        return canAccess(container, '__delitem__')


class PathAdapterUtil(object):

    adapts(None)
    implements(IPathAdapter, ITraversable)

    def __init__(self, context):
        self.context = context


class SortBy(PathAdapterUtil):
    """TALES path adapter for sorting lists.

    In a page template you can use it as follows:

        tal:repeat="something some_iterable/sortby:attribute_name"

    In Python code you can write

        >>> l = [{'name': 'banana'}, {'name': 'apple'}]
        >>> SortBy(l).traverse('name')
        [{'name': 'apple'}, {'name': 'banana'}]

    You can sort arbitrary iterables, not just lists.  The sort key
    can refer to a dictionary key, or an object attribute.
    """

    def traverse(self, name, furtherPath=()):
        """Return self.context sorted by a given key."""
        # We need to get the first item without losing it forever
        iterable = iter(self.context)
        try:
            first = iterable.next()
        except StopIteration:
            return [] # We got an empty list
        iterable = itertools.chain([first], iterable)
        # removeSecurityProxy is safe here because subsequent getattr() will
        # raise Unauthorized or ForbiddenAttribute as appropriate.  It is
        # necessary here to fix http://issues.schooltool.org/issue174
        if hasattr(removeSecurityProxy(first), name):
            items = [(getattr(item, name), item) for item in iterable]
        else:
            items = [(item[name], item) for item in iterable]
        items.sort()
        return [row[-1] for row in items]


class CanAccess(PathAdapterUtil):
    """TALES path adapter for checking access rights.

    In a page template this adapter can be used like this:

        <p tal:condition="context/can_access:title"
           tal:content="context/title" />

    """

    def traverse(self, name, furtherPath=()):
        """Returns True if self.context.(name) can be accessed."""
        return canAccess(self.context, name)


class CanModify(PathAdapterUtil):
    """TALES path adapter for checking access rights.
    """

    def traverse(self, name, furtherPath=()):
        """Returns True if self.context.(name) can be changed."""
        return canWrite(self.context, name)


class FilterAccessible(PathAdapterUtil):
    """TALES path adapter for XXX

    In a page template this adapter can be used like this:

        <p tal:repeat="group context/groups/filter_accessible:title"
           tal:content="group/title" />

    """

    def traverse(self, name, furtherPath=()):
        """XXX"""
        return [item for item in self.context
                if canAccess(item, name)]


class SortedFilterAccessible(PathAdapterUtil):
    """TALES path adapter for XXX

    In a page template this adapter can be used like this:

        <p tal:repeat="group context/groups/sorted_filter_accessible:title"
           tal:content="group/title" />

    """

    def traverse(self, name, furtherPath=()):
        """XXX"""
        filtered = FilterAccessible(self.context).traverse(name)
        return SortBy(filtered).traverse(name)


class SchoolToolSized(object):
    """An adapter to provide number of persons in a SchoolTool instance."""

    implements(ISized)

    def __init__(self, app):
        self._app = app

    def sizeForSorting(self):
        return (_("Persons"), len(self._app['persons']))

    def sizeForDisplay(self):
        num = self.sizeForSorting()[1]
        if num == 1:
            msgid = _("1 person")
        else:
            msgid = _("${number} persons", mapping={'number': num})
        return msgid


class ViewPreferences(object):
    """Preference class to attach to views."""

    def __init__(self, request):
        try:
            app = ISchoolToolApplication(None)
            prefs = IApplicationPreferences(app)
        except (ValueError, TypeError):
            prefs = None

        if prefs is not None:
            self.dateformat = prefs.dateformat
            self.timeformat = prefs.timeformat
            self.first_day_of_week = prefs.weekstart
            self.timezone = timezone(prefs.timezone)
        else:
            # no user, no application - test environment
            self.dateformat = '%Y-%m-%d'
            self.timeformat = '%H:%M'
            self.first_day_of_week = calendar.MONDAY
            self.timezone = timezone('UTC')

    def renderDatetime(self, dt):
        dt = dt.astimezone(self.timezone)
        return dt.strftime('%s %s' % (self.dateformat, self.timeformat))


def same(obj1, obj2):
    """Return True if the references obj1 and obj2 point to the same object.

    The references may be security-proxied.
    """
    return removeSecurityProxy(obj1) is removeSecurityProxy(obj2)
