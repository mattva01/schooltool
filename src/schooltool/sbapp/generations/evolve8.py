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
Upgrade to generation 8.

Issue349 - while the original evolution script (evolve6) evolved
properties that were set properly. Default settings 'YYYY-MM-DD' were
left unmodified.

$Id: evolve6.py 4741 2005-08-16 17:41:15Z ignas $
"""

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding

from schoolbell.app.interfaces import IHavePreferences, IPersonPreferences

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    for person in findObjectsProviding(root, IHavePreferences):
        prefs = IPersonPreferences(person)

        if prefs.dateformat == 'YYYY-MM-DD':
            prefs.dateformat = '%Y-%m-%d'
