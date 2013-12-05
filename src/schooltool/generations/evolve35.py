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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Upgrade SchoolTool to generation 35.

Evolution script to unregister old catalog utilities.
"""
import zope.catalog
import zope.catalog.catalog
import zope.catalog.interfaces
import zope.intid
import zope.intid.interfaces
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.component import queryUtility, getUtility
from zope.component.hooks import getSite, setSite
from zope.traversing.api import traverse

from schooltool.generations import linkcatalogs
from schooltool.testing.mock import ModulesSnapshot
from schooltool.app.interfaces import ISchoolToolApplication
from zope.catalog.interfaces import ICatalog


CATALOG_KEYS = [
    'schooltool.basicperson',
    'schooltool.contact',
    'schooltool.person',
    ]


def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = context.connection.root().get(ZopePublication.root_name, None)

    # Mock the renaming of zope.app.catalog and zope.app.intid to
    # zope.catalog and zope.intid.
    # This is for Critical Links deployments only - this part of Zope's evolution
    # was missed somehow.
    modules = ModulesSnapshot()
    modules.mock_module('zope.app.catalog')
    modules.mock_module('zope.app.catalog.interfaces')
    modules.mock_module('zope.app.catalog.catalog')
    modules.mock_module('zope.app.intid')
    modules.mock_module('zope.app.intid.interfaces')

    modules.mock_attr('zope.app.catalog.catalog', 'Catalog', zope.catalog.catalog.Catalog)
    modules.mock_attr('zope.app.catalog.interfaces', 'ICatalog', zope.catalog.interfaces.ICatalog)

    modules.mock_attr('zope.app.intid', 'IntIds', zope.intid.IntIds)
    modules.mock_attr('zope.app.intid.interfaces', 'IIntIds', zope.intid.interfaces.IIntIds)

    # Proceed with normal evolution now.

    old_site = getSite()
    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)
        sm = app.getSiteManager()
        default = traverse(app, '++etc++site/default')

        intids = getUtility(zope.intid.interfaces.IIntIds)
        intids._p_changed = True

        for key in CATALOG_KEYS:
            util = queryUtility(ICatalog, name=key, default=None)
            if util is None:
                continue
            name = util.__name__
            sm.unregisterUtility(util, ICatalog, key)
            del default[name]

    setSite(old_site)

    modules.restore()
