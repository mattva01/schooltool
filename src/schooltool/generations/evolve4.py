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
Upgrade SchoolTool to generation 4.

This generation ensures that all schooltool applications have a levels folder
and a manager group.

$Id: evolve2.py 4259 2005-07-21 00:57:30Z tvon $
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from schooltool.interfaces import ISchoolToolApplication

import schooltool.app
import schooltool.level.level

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    for app in findObjectsProviding(root, ISchoolToolApplication):
        if 'levels' not in app:
            app['levels'] = schooltool.level.level.LevelContainer()

        if 'manager' not in app['groups']:
            app['groups']['manager'] = schooltool.app.Group(
                u'Manager', u'Manager Group.')

