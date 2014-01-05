#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 34.

Evolution script to set the 'enabled' attribute in existing EmailContainers.
"""
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication

from schooltool.generations import linkcatalogs
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.email.interfaces import IEmailContainer


def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = context.connection.root().get(ZopePublication.root_name, None)

    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        container = IEmailContainer(app, None)
        if container is None:
            continue
        if getattr(container, 'enabled', None) is None:
            container.enabled = bool(container.hostname)
