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
Upgrade SchoolTool to generation 19.

Install catalog and reindex persons.

$Id$
"""

import base64

from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication

from schooltool.app.interfaces import IHaveCalendar

def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for obj in findObjectsProviding(root, IHaveCalendar):
        if not hasattr(obj, '__annotations__'):
            continue
        calendar = obj.__annotations__.get('schooltool.app.calendar.Calendar',
                                           None)

        if not calendar:
            continue

        for event in calendar:
            event.__name__ = base64.encodestring(event.unique_id).replace('\n', '')
