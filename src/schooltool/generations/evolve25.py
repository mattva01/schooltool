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
Upgrade SchoolTool to generation 21.

Create workheet for section activities and move existing activities
into that worksheet.

$Id: evolve21.py 6527 2006-12-28 12:25:35Z ignas $
"""

import zope.event
from zope.annotation.interfaces import IAnnotations
from zope.app.container.interfaces import INameChooser
from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.gradebook.activity import Worksheet

def evolve(context):
    root = context.connection.root()[ZopePublication.root_name]
    for app in findObjectsProviding(root, ISchoolToolApplication):
        for section in app['sections'].values():
            annotations = IAnnotations(section)
            activities = annotations.get('schooltool.gradebook.activities')
            if activities:
                worksheet = Worksheet('Worksheet1')
                for key, activity in list(activities.items()):
                    activity.__parent__ = None
                    worksheet[key] = activity
                    activity.__parent__ = worksheet
                    del activities[key]
                nameChooser = INameChooser(activities)
                name = nameChooser.chooseName('', worksheet)
                activities[name] = worksheet

