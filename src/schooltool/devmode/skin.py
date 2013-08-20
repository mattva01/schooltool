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
SchoolTool skin.
"""
from zope.interface import directlyProvidedBy
from zope.interface import directlyProvides
from zope.publisher.interfaces.browser import IBrowserRequest

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin import ISchoolToolSkin


class IDevModeLayer(IBrowserRequest):
    """SchoolTool devmode layer."""


class ISchoolToolDevModeSkin(IDevModeLayer, ISchoolToolSkin):
    """The SchoolTool devmode skin"""


def schoolToolTraverseSubscriber(event):
    """A subscriber to BeforeTraverseEvent.

    Adds DevMode layer to the request.
    """
    if (ISchoolToolApplication.providedBy(event.object) and
        IBrowserRequest.providedBy(event.request)):
        directlyProvides(event.request,
                         directlyProvidedBy(event.request) + IDevModeLayer)
