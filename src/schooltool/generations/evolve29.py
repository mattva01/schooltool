#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Upgrade SchoolTool to generation 29.

Remove unused attributes from person schema.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from schooltool.generations import linkcatalogs

from schooltool.app.interfaces import ISchoolToolApplication

def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = context.connection.root().get(ZopePublication.root_name, None)

    for app in findObjectsProviding(root, ISchoolToolApplication):
        persons = app['persons']
        for person in persons.values():
            del person.email
            del person.phone
            if hasattr(person, 'gradeclass'):
                del person.gradeclass
