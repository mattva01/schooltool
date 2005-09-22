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
Upgrade SchoolTool to generation 6.

Cleanup for http://issues.schooltool.org/issue369: remove stale
calendar subscription relationships.

$Id$
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding

from schooltool.person.interfaces import IPerson


def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for person in findObjectsProviding(root, IPerson):
        for calendar_info in list(person.overlaid_calendars):
            if calendar_info.calendar.__parent__.__parent__ is None:
                person.overlaid_calendars.remove(calendar_info.calendar)
