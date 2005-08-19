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
Upgrade SchoolTool to generation 1.

The first incompatible change from generation 0 was introduced in rev 4128.

$Id$
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.cal import Calendar
from schooltool.timetable import TimetableDict


def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    for app in findObjectsProviding(root, ISchoolToolApplication):
        app.calendar = Calendar(app)
        app.timetables = TimetableDict()
        app.timetables.__parent__ = app
