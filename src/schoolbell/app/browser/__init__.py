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
Browser views for the SchoolBell application.

$Id$
"""

import itertools

from zope.interface import implements
from zope.component import adapts
from zope.app.publisher.browser import BrowserView
from zope.app.size.interfaces import ISized
from zope.app.traversing.interfaces import IPathAdapter, ITraversable
from zope.tales.interfaces import ITALESFunctionNamespace

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.app import getSchoolBellApplication


class NavigationView(BrowserView):
    """View for the navigation portlet.

    A separate view lets us vary the content of the navigation portlet
    according to the currently logged in user and/or context.  Currently
    we do not make use of this flexibility, though.

    This view finds the schoolbell application from context and makes it
    available to the page template as view/app.  Rendering this view on
    an object that is not a part of a SchoolBell instance will raise an error,
    so don't do that.
    """

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.app = getSchoolBellApplication(context)


class SchoolBellAPI(object):
    """TALES function namespace for SchoolBell specific actions.

    In a page template you can use it as follows:

        tal:define="app context/schoolbell:app"

    """

    implements(IPathAdapter, ITALESFunctionNamespace)

    def __init__(self, context):
        self.context = context

    def setEngine(self, engine):
        """See ITALESFunctionNamespace."""
        pass

    def app(self):
        """Adapt context to ISchoolBellApplication."""
        return ISchoolBellApplication(self.context)
    app = property(app)


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
        if hasattr(first, name):
            items = [(getattr(item, name), item) for item in iterable]
        else:
            items = [(item[name], item) for item in iterable]
        items.sort()
        return [row[-1] for row in items]


class SchoolBellSized(object):
    """An adapter to provide number of persons in a SchoolBell instance."""

    implements(ISized)

    def __init__(self, app):
        self._app = app

    def sizeForSorting(self):
        return len(self._app['persons'])

    def sizeForDisplay(self):
        num = self.sizeForSorting()
        if num == 1:
            return _("1 person")
        else:
            return _("%d persons" % num)
