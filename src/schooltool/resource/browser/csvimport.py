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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
csv importing.
"""
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.browser.csvimport import BaseCSVImporter
from schooltool.app.browser.csvimport import BaseCSVImportView
from schooltool.app.browser.csvimport import FlourishBaseCSVImportView
from schooltool.resource.resource import Resource, Location

from schooltool.common import SchoolToolMessage as _


def resourceFactory(self, title=u"", description=u"", isLocation=False):
    if isLocation:
        return Location(title=title, description=description)
    else:
        return Resource(title=title, description=description)


class ResourceCSVImporter(BaseCSVImporter):
    """Resource CSV Importer"""

    factory = resourceFactory

    def createAndAdd(self, data, dry_run=True):
        """Create objects and add them to the container."""

        if len(data) < 1:
            self.errors.fields.append(_('Insufficient data provided.'))
            return

        if not data[0]:
            self.errors.fields.append(_('Titles may not be empty'))
            return

        if len(data) > 1:
            description = data[1]
        else:
            description = ''

        isLocation =  len(data) > 2

        obj = self.factory(title=data[0], description=description,
                           isLocation=isLocation)
        name = self.chooser.chooseName('', obj)

        if not dry_run:
            self.container[name] = obj


class ResourceCSVImportView(BaseCSVImportView):
    """View for Resource CSV importer."""

    importer_class = ResourceCSVImporter


class FlourishResourceCSVImportView(FlourishBaseCSVImportView):

    importer_class = ResourceCSVImporter

    def nextURL(self):
        return absoluteURL(self.context, self.request)
