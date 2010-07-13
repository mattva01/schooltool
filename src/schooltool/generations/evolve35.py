#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 35.

Evolution script to unregister old catalog utilities.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.component import queryUtility
from zope.component.hooks import getSite, setSite
from zope.traversing.api import traverse

from schooltool.app.interfaces import ISchoolToolApplication
from zope.catalog.interfaces import ICatalog


CATALOG_KEYS = [
    'schooltool.basicperson',
    'schooltool.contact',
    'schooltool.person',
    ]


def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)

    old_site = getSite()
    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)
        sm = app.getSiteManager()
        default = traverse(app, '++etc++site/default')

        for key in CATALOG_KEYS:
            util = queryUtility(ICatalog, name=key, default=None)
            if util is None:
                continue
            name = util.__name__
            sm.unregisterUtility(util, ICatalog, key)
            del default[name]

    setSite(old_site)
