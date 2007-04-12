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
Upgrade SchoolTool to generation 22.

Install catalog  for groups and reindex them.

$Id$
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.app.catalog.interfaces import ICatalog
from zope.app.catalog.catalog import Catalog
from zope.app.component.hooks import setSite
from zope.app.intid import addIntIdSubscriber

from zc.catalog.catalogindex import ValueIndex

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.utility.utility import setUpUtilities
from schooltool.utility.utility import UtilitySpecification
from schooltool.group.interfaces import IGroup


def catalogSetUp(catalog):
    catalog['__name__'] = ValueIndex('__name__', IGroup)
    catalog['title'] = ValueIndex('title', IGroup)


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        # install the utilities
        setSite(app)
        setUpUtilities(app, [UtilitySpecification(Catalog, ICatalog,
                                                  'schooltool.group',
                                                  setUp=catalogSetUp)])
        # catalog all groups
        for group in app['groups'].values():
            addIntIdSubscriber(group, None)
