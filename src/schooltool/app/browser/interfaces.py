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
Interfaces for SchoolTool calendar browser views.
"""

from zope.viewlet.interfaces import IViewletManager
from zope.interface import Interface

from schooltool.calendar.browser.interfaces import IEventForDisplay
from schooltool.calendar.browser.interfaces import IHaveEventLegend


class ICalendarProvider(Interface):
    """Calendar provider.

    Subscription adapters providing this interface will be used to
    combine the list of calendars that will be displayed.
    """

    def getCalendars():
        """Gets a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """


class ICalendarMenuViewlet(Interface):
    """Marker interface so we could use custom crowd for View Calendar menu item"""


class IManageMenuViewletManager(IViewletManager):
    """Provides a viewlet hook for the management menu items."""


class ISchoolMenuViewletManager(IViewletManager):
    """Provides a viewlet hook for the school menu items."""


class IReportPageTemplate(Interface):

    def stylesheet():
        """Render the stylesheet contents."""

    def __call__():
        """Render the page template itself."""
