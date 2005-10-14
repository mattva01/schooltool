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
Upgrade SchoolTool to generation 7.

Change the format of exceptionDays on timetable models.

$Id$
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding

from schooltool.timetable.interfaces import ITimetableSchema


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for schema in findObjectsProviding(root, ITimetableSchema):
        model = schema.model
        for date, exception in model.exceptionDays.items():
            periods = []
            for slot in exception:
                periods.append((slot.title, slot))
            model.exceptionDays[date] = periods
