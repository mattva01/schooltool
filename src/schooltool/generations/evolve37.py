#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 37.

Move per-schoolyear levels to a single per-app container.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.component import getUtility
from zope.component.hooks import getSite, setSite
from zope.intid.interfaces import IIntIds

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.level.level import LevelContainerContainer
from schooltool.schoolyear.interfaces import ISchoolYearContainer


LEVELS_APP_KEY = 'schooltool.level.level'


def guessMostRecentLevels(app):
    container = app.get(LEVELS_APP_KEY)
    if (container is None or
        not isinstance(container, LevelContainerContainer)):
        return None
    levels = None
    syc = ISchoolYearContainer(app, None)
    int_ids = getUtility(IIntIds)

    years = list(reversed(syc.sorted_schoolyears))
    active_year = syc.getActiveSchoolYear()
    if active_year is not None:
        years = [active_year] + years
    for year in years:
        sy_id = str(int_ids.getId(year))
        levels = container.get(sy_id, None)
        if levels is not None:
            return levels
    return None


def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    old_site = getSite()

    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)
        levels = guessMostRecentLevels(app)
        if levels is not None:
            del app[LEVELS_APP_KEY]
            app[LEVELS_APP_KEY] = levels

    setSite(old_site)
