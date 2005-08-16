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
Upgrade SchoolTool to generation 3.

evolve2.py creates a site calendar, but the default permissions prevent
unknown visitors from seeing it.

$Id$
"""

from zope.app import zapi
from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.app.security.interfaces import IUnauthenticatedGroup
from schooltool.interfaces import ISchoolToolApplication


def evolve(context):
    """Set the site security policy to the SchoolTool 0.11 defaults.

    See schooltool.app.applicationCalendarPermissionsSubscriber for details.
    """
    root = context.connection.root().get(ZopePublication.root_name, None)
    for app in findObjectsProviding(root, ISchoolToolApplication):
        unauthenticated = zapi.queryUtility(IUnauthenticatedGroup)

        app_perms = IPrincipalPermissionManager(app)
        app_perms.grantPermissionToPrincipal(
            'schoolbell.view', unauthenticated.id)
        app_perms.grantPermissionToPrincipal(
            'schoolbell.viewCalendar', unauthenticated.id)

        containers = ['persons', 'groups', 'resources', 'sections', 'courses']
        for container in containers:
            container_perms = IPrincipalPermissionManager(app[container])
            container_perms.denyPermissionToPrincipal(
                    'schoolbell.view', unauthenticated.id)
            container_perms.denyPermissionToPrincipal(
                    'schoolbell.viewCalendar', unauthenticated.id)
