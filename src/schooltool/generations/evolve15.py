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
Upgrade SchoolTool to generation 15.

Get rid of all local grants.

$Id$
"""

from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.annotation.interfaces import IAnnotations
from zope.annotation.interfaces import IAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication


def removeLocalGrants(obj):
    annotations = IAnnotations(obj)
    perm_key = 'zopel.app.security.AnnotationPrincipalPermissionManager'
    if annotations.has_key(perm_key):
        del annotations[perm_key]
    role_key = 'zope.app.security.AnnotationPrincipalRoleManager'
    if annotations.has_key(role_key):
        del annotations[role_key]


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        for obj in findObjectsProviding(app, IAnnotatable):
            removeLocalGrants(obj)
