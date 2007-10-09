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

from schooltool.app.interfaces import ISchoolToolApplication


def evolve(context):
    # this used to evolve role and permission settings but this has
    # become obsolete after the new security policy was put into place
    return
