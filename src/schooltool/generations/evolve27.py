#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 27.

Fix timetables to reference theirs school timetables and terms
directly instead of using __name__ to do that.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication

from schooltool.app.interfaces import ISchoolToolApplication

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)

    for app in findObjectsProviding(root, ISchoolToolApplication):
        sections = app['sections']
        for section in sections.values():
            annotations = getattr(section, '__annotations__', {})
            ttdict = annotations.get('schooltool.timetable.timetables', {})
            for key, timetable in ttdict.items():
                term_id, schooltt_id = key.split('.')
                term = app['terms'][term_id]
                schooltt = app['ttschemas'][schooltt_id]
                timetable.term = term
                timetable.schooltt = schooltt
