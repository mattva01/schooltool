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
from zope.component import getUtility
from zope.container.interfaces import INameChooser

from schooltool.app.browser.csvimport import BaseCSVImporter, BaseCSVImportView
from schooltool.person.interfaces import IPersonFactory

from schooltool.common import SchoolToolMessage as _

class PersonCSVImporter(BaseCSVImporter):
    """A Person CSV importer."""

    def createAndAdd(self, data, dry_run=True):
        """Create Person object and add to container.

        We are requiring that we have a username and fullname (title) set.  If
        any duplicates are found then an error is reported and the duplicate
        entries are reported back to the user.
        """
        if len(data) < 2:
            self.errors.fields.append(_("""Insufficient data provided."""))
            return

        if not data[0]:
            self.errors.fields.append(_('username may not be empty'))
            return

        if not data[1]:
            self.errors.fields.append(_('fullname may not be empty'))
            return

        username = data[0]
        fullname = data[1]
        if len(data) > 2:
            password = data[2]
        else:
            password = None

        if username in self.container:
            error_msg = _("Duplicate username: ${username}",
                          mapping={'username' : ', '.join(data)})
            self.errors.fields.append(error_msg)
            return

        try:
            INameChooser(self.container).checkName(username, None)
        except ValueError:
            error_msg = _("Names cannot begin with '+' or '@' or contain '/'")
            self.errors.fields.append(error_msg)
            return

        obj = self.personFactory(data[0], data[1])

        if password:
            obj.setPassword(password)

        if not dry_run:
            self.container[data[0]] = obj

    def personFactory(self, username, title):
        factory = getUtility(IPersonFactory)
        person = factory(username=username, title=title)
        return person

class PersonCSVImportView(BaseCSVImportView):
    """View for Person CSV importer."""

    importer_class = PersonCSVImporter
