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
Upgrade to generation 6.

Changing time and date formatting preferences requires changing the preferences
currently stored on existing Person instances.

$Id$
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding

from schooltool.app.interfaces import IHavePreferences, IPersonPreferences

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    for person in findObjectsProviding(root, IHavePreferences):
        prefs = IPersonPreferences(person)

        if prefs.timeformat == 'HH:MM':
            prefs.timeformat = '%H:%M'
        elif prefs.timeformat == 'H:MM am/pm':
            prefs.timeformat = '%I:%M %p'

        if prefs.dateformat == 'MM/DD/YY':
            prefs.dateformat = '%m/%d/%y'
        elif prefs.dateformat == 'YYYY-DD-MM':
            prefs.dateformat = '%Y-%m-%d'
        elif prefs.dateformat == 'Day Month, Year':
            prefs.dateformat = '%d %B, %Y'

