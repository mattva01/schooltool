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
Upgrade SchoolTool to generation 8.

Change the format of exceptionDays on timetable models.

$Id: evolve8.py 5268 2005-10-14 19:15:43Z alga $
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from zope.app.dependable.interfaces import IDependable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.group.group import Group


def evolve(context):
    default_groups =  [
        ("manager",        "Site Managers",         "Manager Group."),
        ("students",       "Students",              "Students."),
        ("teachers",       "Teachers",              "Teachers."),
        ("clerks",         "Clerks",                "Clerks."),
        ("administrators", "School Administrators", "School Administrators."),
    ]

    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        group_container = app['groups']
        for name, title, description in default_groups:
            try:
                group = group_container[name]
            except KeyError:
                group = Group(title, description)
                group_container[name] = group
            IDependable(group).addDependent("")
