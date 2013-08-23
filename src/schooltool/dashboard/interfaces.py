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
"""Dashboard Interfaces
"""
__docformat__ = 'reStructuredText'
import zope.schema
from zope.viewlet import interfaces
from schooltool.common import SchoolToolMessage as _


class IDashboard(interfaces.IViewletManager):
    """Dashboard

    The dashboard is a central place, which provides an overview of the tasks
    a particular user can complete.
    """


class IDashboardCategory(interfaces.IViewlet):
    """Dashbard Category

    One of the categories in the dashboard.
    """

    title = zope.schema.TextLine(
        title=_("Title"),
        required=True)

    weight = zope.schema.Int(
        title=_("Weight"),
        required=True,
        default=100)

    def isAvailable(self):
        """Determine whether the category is available.

        Ususally, the discrimination the viewlet provides is enough to
        determine availability. However, in this case we want to determine
        availability by user group.
        """
