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
Pluggable Traverser Implementation for the Browser
"""
from schooltool.traverser.traverser import PluggableTraverser
from zope.publisher.defaultview import getDefaultViewName


class PluggableBrowserTraverser(PluggableTraverser):

    def browserDefault(self, request):
        """See zope.publisher.browser.interfaces.IBrowserPublisher"""
        view_name = getDefaultViewName(self.context, request)
        view_uri = "@@%s" %view_name
        return self.context, (view_uri,)
