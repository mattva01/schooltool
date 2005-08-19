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
Person security infrastructure

$Id: security.py 4431 2005-08-02 04:33:27Z tvon $
"""
from schooltool.person.interfaces import IPerson
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager

def personPermissionsSubscriber(event):
    """Grant default permissions to all new persons"""
    if IObjectAddedEvent.providedBy(event):
        if IPerson.providedBy(event.object):
            map = IPrincipalPermissionManager(event.object)
            principalid = 'sb.person.' + event.object.__name__
            map.grantPermissionToPrincipal('schooltool.view', principalid)
            map.grantPermissionToPrincipal('schooltool.edit', principalid)
            map.grantPermissionToPrincipal('schooltool.addEvent', principalid)
            map.grantPermissionToPrincipal('schooltool.modifyEvent',
                                           principalid)
            map.grantPermissionToPrincipal('schooltool.viewCalendar',
                                           principalid)
            map.grantPermissionToPrincipal('schooltool.controlAccess',
                                           principalid)
