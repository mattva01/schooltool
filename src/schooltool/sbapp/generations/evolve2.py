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
Upgrade to generation 2.

The first incompatible change from 1 was introduced in rev .

$Id$
"""
from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from schooltool.app.interfaces import ISchoolToolApplication, IHaveNotes
from schooltool.notes import getNotes
import datetime
import random

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    for app in findObjectsProviding(root, ISchoolToolApplication):
        for noted in findObjectsProviding(root, IHaveNotes):
            for note in getNotes(noted):
                note.unique_id = '%d.%d' % (
                    datetime.datetime.utcnow().microsecond,
                    random.randrange(10 ** 6, 10 ** 7))

