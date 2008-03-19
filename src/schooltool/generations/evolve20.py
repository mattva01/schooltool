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
Upgrade SchoolTool to generation 20.

Remove local IPersonFactory utility.

$Id$
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from zope.app.component.hooks import setSite
from zope.component import queryUtility
from zope.app.container.interfaces import IContained
from zope.traversing.api import traverse

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPersonFactory


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        setSite(app)
        manager = app.getSiteManager()
        default = traverse(app, '++etc++site/default')
        local_utility = queryUtility(IPersonFactory, default=None)
        if (local_utility is not None and
            IContained.providedBy(local_utility) and
            local_utility.__parent__ is default):
            name = local_utility.__name__
            manager.unregisterUtility(local_utility, IPersonFactory)
            del default[name]
        setSite(None)
