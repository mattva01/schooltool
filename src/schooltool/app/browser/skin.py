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
SchoolTool skin.

$Id$
"""

from zope.interface import Interface
from zope.interface import implements
from zope.schema import Object
from zope.publisher.interfaces.browser import ILayer, IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.viewlet.interfaces import IViewletManager
from zope.viewlet.manager import ViewletManagerBase
from zope.publisher.browser import applySkin
from zope.publisher.interfaces.browser import IBrowserRequest

from schooltool.app.browser.interfaces import IEventForDisplay
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.skin import OrderedViewletManager
from schooltool.skin.skin import ISchoolToolSkin


class ICalendarEventViewletManager(IViewletManager):
    """Provides a viewlet hook for daily calendar events."""


class ICalendarEventContext(Interface):
    """Schema for attributes required by CalendarEventViewletManager."""

    event = Object(IEventForDisplay)


class CalendarEventBookingViewlet(object):
    """
    This is the view class for the booking viewlet on the CalendarEventView
    """

    def listResources(self):
        return [{'id': resource.__name__, 'title': resource.title}
                for resource in self.manager.event.context.resources]


class CalendarEventViewletManager(OrderedViewletManager):
    """Viewlet manager for displaying of additional event information."""

    implements(ICalendarEventContext)


# did not move this into schooltool.skin because this actually
# enables the skin, doesn't define it.
def schoolToolTraverseSubscriber(app, event):
    """A subscriber to BeforeTraverseEvent.

    Sets the SchoolBell skin if the object traversed is a SchoolBell
    application instance.
    """
    if IBrowserRequest.providedBy(event.request):
        applySkin(event.request, ISchoolToolSkin)
