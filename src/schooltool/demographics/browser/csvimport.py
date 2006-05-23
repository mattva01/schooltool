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

from schooltool.person.browser.csvimport import PersonCSVImporter as\
     PersonCSVImporterBase
from schooltool.demographics.person import Person
from schooltool.app.browser.csvimport import BaseCSVImportView

class PersonCSVImporter(PersonCSVImporterBase):
    def personFactory(self, username, title):
        return Person(username=username, title=title)

class PersonCSVImportView(BaseCSVImportView):
    importer_class = PersonCSVImporter
