#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
A base class for CSV importers.
"""

import csv
from schooltool.common import UnicodeAwareException
from schooltool.translation import ugettext as _

__metaclass__ = type


class DataError(UnicodeAwareException):
    pass


class CSVImporterBase:
    """A base class for CSV importers."""

    def recode(self, value):
        """Convert value to Unicode from the encoding used for the CSV file.

        Should be overridden in subclasses.
        """
        return unicode(value)

    def importGroupsCsv(self, csvdata):
        lineno = 0
        try:
            for lineno, row in enumerate(csv.reader(csvdata)):
                if len(row) != 4:
                    raise DataError(_("Error in group data, line %d:"
                                      " expected 4 columns, got %d") %
                                    (lineno + 1, len(row)))
                name, title, parents, facets = map(self.recode, row)
                self.importGroup(name, title, parents, facets)
        except csv.Error, e:
            raise DataError(_("Error in group data line %d: %s")
                            % (lineno + 1, e))

    def importPersonsCsv(self, csvdata):
        lineno = 0
        try:
            for lineno, row in enumerate(csv.reader(csvdata)):
                if len(row) != 6:
                    raise DataError(_("Error in persons data line %d:"
                                      " expected 6 columns, got %d") %
                                    (lineno + 1, len(row)))
                name, surname, given_name, groups, dob, comment = \
                    map(self.recode, row)
                name = self.importPerson(name, surname, given_name, groups)
                self.importPersonInfo(name, surname, given_name, dob, comment)
        except csv.Error, e:
            raise DataError(_("Error in persons data line %d: %s")
                            % (lineno + 1, e))

    def importResourcesCsv(self, csvdata):
        lineno = 0
        try:
            for lineno, row in enumerate(csv.reader(csvdata)):
                if len(row) != 2:
                    raise DataError(_("Error in resource data line %d:"
                                      " expected 2 columns, got %d") %
                                    (lineno + 1, len(row)))
                title, groups = map(self.recode, row)
                self.importResource(title, groups)
        except csv.Error, e:
            raise DataError(_("Error in resource data line %d: %s")
                            % (lineno + 1, e))

    # The methods below must be overridden by subclasses.

    def importGroup(self, name, title, parents, facets):
        raise NotImplementedError()

    def importPerson(self, name, surname, given_name, groups):
        raise NotImplementedError()

    def importResource(self, title, groups):
        raise NotImplementedError()

    def importPersonInfo(self, name, surname, given_name, dob, comment):
        raise NotImplementedError()
