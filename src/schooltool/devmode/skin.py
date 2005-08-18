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
SchoolBell skin.

$Id: skin.py 3335 2005-03-25 18:53:11Z ignas $
"""
from zope.app.publisher.browser import applySkin
from zope.publisher.interfaces.browser import IBrowserRequest
from schooltool.app.interfaces import ISchoolToolApplication
from schoolbell.app.browser.skin import ISchoolBellSkin 


class IDevModeLayer(IBrowserRequest):
    """SchoolBell devmode layer."""


class ISchoolBellDevModeSkin(IDevModeLayer, ISchoolBellSkin):
    """The SchoolBell devmode skin"""


def schoolBellTraverseSubscriber(event):
    """A subscriber to BeforeTraverseEvent.

    Sets the SchoolBell skin if the object traversed is a SchoolBell
    application instance.
    """
    if (ISchoolToolApplication.providedBy(event.object) and
        IBrowserRequest.providedBy(event.request)):
        applySkin(event.request, ISchoolBellDevModeSkin)
