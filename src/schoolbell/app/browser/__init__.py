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
from schoolbell.app.interfaces import ISchoolBellApplication
from zope.app.location.interfaces import ILocation


def getSchoolBellApplication(obj):
    """Return the nearest ISchoolBellApplication from ancestors of obj"""
    cur = obj
    while True:
        if ISchoolBellApplication.providedBy(cur):
            return cur

        if ILocation.providedBy(cur):
            cur = cur.__parent__
        else:
            cur = None

        if cur is None:
            raise ValueError("can't get a SchoolBellApplication from %r" % obj)


class NavigationView(BrowserView):

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.app = getSchoolBellApplication(context)
