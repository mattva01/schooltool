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
from zope.app.publisher.browser import BrowserView
from schooltool.app.app import getSchoolToolApplication

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
        self.app = getSchoolToolApplication()
