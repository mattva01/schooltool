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
Upgrade SchoolTool to generation 40.

After permissions remap, update person groups.
"""

from zope.app.generations.utility import getRootFolder
from zope.component.hooks import getSite, setSite

from schooltool.generations import linkcatalogs
from schooltool.app.membership import Membership
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.group.interfaces import IGroupContainer


def evolvePerson(app, schoolyear, person):
    groups = IGroupContainer(schoolyear)
    admin_names = ('manager', 'administrators', 'clerks')
    admin_groups = [groups.get(name)
                    for name in admin_names
                    if name in groups]

    person_groups = [group for group in Membership.query(member=person)
                     if group.__parent__.__name__ == groups.__name__]

    if any([group in admin_groups for group in person_groups]):
        for group in admin_groups:
            if group not in person_groups:
                Membership(group=group, member=person)


def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = getRootFolder(context)
    old_site = getSite()

    app = root
    setSite(app)
    syc = ISchoolYearContainer(app)
    if not syc.values():
        setSite(old_site)
        return

    sy = syc.getActiveSchoolYear()
    if sy is None:
        sy = syc.values()[-1]
    for person in app['persons'].values():
        evolvePerson(app, sy, person)

    setSite(old_site)
