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
"""Dashboard Interfaces

$Id$
"""
__docformat__ = 'reStructuredText'
import zope.schema
from zope.viewlet import interfaces
from schooltool import SchoolToolMessage as _


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
        description=_("Category Title."),
        required=True)

    weight = zope.schema.Int(
        title=_("Weight"),
        description=_("Weight"),
        required=True,
        default=100)

    def isAvailable(self):
        """Determine whether the category is available.

        Ususally, the discrimination the viewlet provides is enough to
        determine availability. However, in this case we want to determine
        availability by user group.
        """
