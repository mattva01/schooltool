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
Restive XML views for the SchoolBell application.

$Id$
"""
from zope.interface import directlyProvidedBy, directlyProvides
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.http import IHTTPRequest

from schooltool.app.interfaces import ISchoolToolApplication


# XXX: This should really become an IRESTRequest; this is really a hack to
#      simulate a layer.

class ISchoolBellRequest(IHTTPRequest):
    """A request in SchoolBell (rather than SchoolBell) application"""


def restSchoolBellSubscriber(event):
    """This event subscriber to BeforeTraverseEvent sets a marker
    interface on a RESTive request if we traverse into a SchoolBell
    instance.
    """

    if (ISchoolToolApplication.providedBy(event.object)
        and not IBrowserRequest.providedBy(event.request)):
        interfaces = directlyProvidedBy(event.request)
        directlyProvides(event.request, interfaces + ISchoolBellRequest)
