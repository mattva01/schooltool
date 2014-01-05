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
Upgrade SchoolTool to generation 32.

Evolution script to fix a typo in default 'ethnicity' demographics field.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication

from schooltool.basicperson.interfaces import IEnumFieldDescription
from schooltool.generations import linkcatalogs
from schooltool.app.interfaces import ISchoolToolApplication


DEMOGRAPHICS_FIELDS_KEY = 'schooltool.basicperson.demographics_fields'


def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = context.connection.root().get(ZopePublication.root_name, None)

    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        if DEMOGRAPHICS_FIELDS_KEY not in app:
            continue
        fields = app[DEMOGRAPHICS_FIELDS_KEY]
        for field in fields.values():
            if not IEnumFieldDescription.providedBy(field):
                continue
            for n, item in enumerate(field.items):
                if item == u'Native Hawaiian or Other Pasific Islander':
                    field.items[n] = u'Native Hawaiian or Other Pacific Islander'

