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
Browser views for the SchoolTool application.

$Id: __init__.py 3405 2005-04-12 16:08:43Z bskahan $
"""
import itertools

from zope.interface import implements
from zope.component import adapts
from zope.app.publisher.browser import BrowserView
from zope.app.size.interfaces import ISized
from zope.app.traversing.interfaces import IPathAdapter, ITraversable
from zope.app.security.interfaces import IPrincipal
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.dependable.interfaces import IDependable
from zope.tales.interfaces import ITALESFunctionNamespace
from zope.security.proxy import removeSecurityProxy

from pytz import timezone

from schooltool import SchoolToolMessage as _
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.app import getSchoolToolApplication
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonPreferences

utc = timezone('UTC')


class NavigationView(BrowserView):
    """View for the navigation portlet.

    A separate view lets us vary the content of the navigation portlet
    according to the currently logged in user and/or context.  Currently
    we do not make use of this flexibility, though.

    This view finds the schooltool application from context and makes it
    available to the page template as view/app.  Rendering this view on
    an object that is not a part of a SchoolTool instance will raise an error,
    so don't do that.

    There is a SchoolTool version of this view in the schooltool layer.
    """

    def __init__(self, context, request):
        super(NavigationView, self).__init__(context, request)
        self.app = getSchoolToolApplication()


class SchoolToolAPI(object):
    """TALES function namespace for SchoolTool specific actions.

    In a page template you can use it as follows:

        tal:define="app context/schooltool:app"

    """

    implements(IPathAdapter, ITALESFunctionNamespace)

    def __init__(self, context):
        self.context = context

    def setEngine(self, engine):
        """See ITALESFunctionNamespace."""
        pass

    def app(self):
        """Return the ISchoolToolApplication.

        Sample usage in a page template:

            <a tal:attributes="href context/schooltool:app/@@absolute_url">
               Front page
            </a>

        """
        return getSchoolToolApplication()
    app = property(app)

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
    person = property(person)

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
        if not IPrincipal.providedBy(self.context):
            raise TypeError("schooltool:authenticated can only be applied"
                            " to a principal")
        return not IUnauthenticatedPrincipal.providedBy(self.context)
    authenticated = property(authenticated)

    def preferences(self):
        """Return ApplicationPreferences for the SchoolToolApplication.

        Sample usage in a page template:

          <div tal:define="preferences context/schooltool:preferences">
            <b tal:content="preferences/title"></b>
          </div>

        """
        return IApplicationPreferences(self.app)
    preferences = property(preferences)

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
    has_dependents = property(has_dependents)


class SortBy(object):
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

    adapts(None)
    implements(IPathAdapter, ITraversable)

    def __init__(self, context):
        self.context = context

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
        person = IPerson(request.principal, None)
        if person is not None:
            prefs = IPersonPreferences(person)
            self.dateformat = prefs.dateformat
            self.timeformat = prefs.timeformat
            self.first_day_of_week = prefs.weekstart
            self.timezone = timezone(prefs.timezone)
        else:
            self.first_day_of_week = 0
            self.timeformat = '%H:%M'  # HH:MM
            self.dateformat = '%Y-%m-%d'  # YYYY-MM-DD
            self.timezone = utc
