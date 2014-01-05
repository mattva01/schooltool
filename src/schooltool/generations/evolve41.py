#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 41.

After permissions remap, add superuser to managers and clerks in all years.
"""

from zope.app.generations.utility import getRootFolder, findObjectsProviding
from zope.component.hooks import getSite, setSite

from schooltool.generations import linkcatalogs
from schooltool.app.membership import Membership
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.group.interfaces import IGroupContainer


def makeManager(app, schoolyear, person):
    groups = IGroupContainer(schoolyear)

    default_admin_names = ('manager', 'clerks')
    admin_groups = [groups.get(name)
                    for name in default_admin_names
                    if name in groups]

    person_groups = [group for group in Membership.query(member=person)
                     if group.__parent__.__name__ == groups.__name__]

    for group in admin_groups:
        if group not in person_groups:
            Membership(group=group, member=person)


def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = getRootFolder(context)

    old_site = getSite()
    app = root
    setSite(app)
    persons = ISchoolToolApplication(None)['persons']
    manager = persons.super_user
    if manager is not None:
        syc = ISchoolYearContainer(app)
        for sy in syc.values():
            makeManager(app, sy, manager)

    setSite(old_site)
