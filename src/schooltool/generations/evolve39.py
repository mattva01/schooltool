#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 39.

Update person photos from File to schooltool.skin.flourish.fields.ImageFile.
"""

from zope.app.generations.utility import getRootFolder, findObjectsProviding
from zope.component.hooks import getSite, setSite

from schooltool.generations import linkcatalogs
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common.fields import ImageFile


def evolvePerson(person):
    if person.photo is None:
        return
    photo = person.photo
    params = dict(photo.parameters) if photo.parameters else None
    new_photo = ImageFile(mimeType=photo.mimeType, parameters=params)
    person.photo = new_photo

    fin = photo.open("r")
    fout = new_photo.open("w")
    data = fin.read()
    fout.write(data)
    fout.close()
    fin.close()


def evolve(context):
    linkcatalogs.ensureEvolved(context)
    root = getRootFolder(context)

    old_site = getSite()
    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)
        for person in app['persons'].values():
            evolvePerson(person)

    setSite(old_site)
