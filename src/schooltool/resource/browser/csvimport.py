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
csv importing.

$Id: csvimport.py 4108 2005-06-15 14:27:59Z bskahan $
"""
from schoolbell.app.browser.csvimport import BaseCSVImporter, BaseCSVImportView
from schoolbell.app.resource.resource import Resource

from schoolbell import SchoolBellMessageID as _


class ResourceCSVImporter(BaseCSVImporter):
    """Resource CSV Importer"""

    factory = Resource

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
