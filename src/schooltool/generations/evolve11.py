#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 11.

Introduce new permission schooltool.viewAttendance and roles for groups
(teachers, administrators, etc).

$Id$
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.app.securitypolicy.interfaces import IPrincipalRoleManager

from schooltool.app.interfaces import ISchoolToolApplication


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        roles = IPrincipalRoleManager(app)
        roles.assignRoleToPrincipal('schooltool.manager', 'sb.group.manager')
        roles.assignRoleToPrincipal('schooltool.administrator',
                                    'sb.group.administrators')
        roles.assignRoleToPrincipal('schooltool.teacher', 'sb.group.teachers')
        roles.assignRoleToPrincipal('schooltool.clerk', 'sb.group.clerks')
        for section in app['sections'].values():
            map = IPrincipalPermissionManager(section)
            for instructor in section.instructors:
                principalid = 'sb.person.' + instructor.__name__
            map.grantPermissionToPrincipal('schooltool.viewAttendance', principalid)
