#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
The views for the schooltool.utility objects.

$Id$
"""

from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IUtilityService, IUtility
from schooltool.component import registerView
from schooltool.views import View, Template
from schooltool.views import ItemTraverseView
from schooltool.views import getURL
from schooltool.views.auth import PublicAccess

__metaclass__ = type


moduleProvides(IModuleSetup)


class UtilityServiceView(ItemTraverseView):
    """The view for the utility service"""

    template = Template("www/utilservice.pt", content_type="text/xml")
    authorization = PublicAccess

    def getName(self):
        return self.context.__name__

    def items(self):
        return [{'href': getURL(self.request, utility, absolute=False),
                 'title': utility.title}
                for utility in self.context.values()]


class UtilityView(View):
    """View for utilities in general.

    Specific utilities should provide more informative views.
    """

    template = Template('www/utility.pt', content_type="text/xml")
    authorization = PublicAccess


def setUp():
    """See IModuleSetup."""
    registerView(IUtilityService, UtilityServiceView)
    registerView(IUtility, UtilityView)

