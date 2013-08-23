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
CSV import view for BasicPerson.
"""
from zope.component import getUtility
from zope.container.interfaces import INameChooser
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.browser.csvimport import BaseCSVImporter
from schooltool.app.browser.csvimport import BaseCSVImportView
from schooltool.app.browser.csvimport import FlourishBaseCSVImportView
from schooltool.person.interfaces import IPersonFactory

from schooltool.common import SchoolToolMessage as _


class BasicPersonCSVImporter(BaseCSVImporter):
    """A Person CSV importer."""

    def createAndAdd(self, data, dry_run=True):
        """Create Person object and add to container.

        We are requiring that we have a username and fullname (title) set.  If
        any duplicates are found then an error is reported and the duplicate
        entries are reported back to the user.
        """
        if len(data) < 3:
            self.errors.fields.append(_("""Insufficient data provided."""))
            return

        if not data[0]:
            self.errors.fields.append(_('username may not be empty'))
            return

        if not data[1]:
            self.errors.fields.append(_('first name may not be empty'))
            return

        if not data[2]:
            self.errors.fields.append(_('last name may not be empty'))
            return

        username = data[0]
        first_name = data[1]
        last_name = data[2]
        if len(data) > 3:
            password = data[3]
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

        # XXX: this has to be fixed
        # XXX: SchoolTool should handle UTF-8
        try:
            username.encode('ascii')
        except UnicodeEncodeError:
            error_msg = _("Usernames cannot contain non-ascii characters")
            self.errors.fields.append(error_msg)
            return

        obj = self.personFactory(username, first_name, last_name)

        if password:
            obj.setPassword(password)

        if not dry_run:
            self.container[data[0]] = obj

    def personFactory(self, username, first_name, last_name):
        factory = getUtility(IPersonFactory)
        person = factory(username=username,
                         first_name=first_name,
                         last_name=last_name)
        return person


class BasicPersonCSVImportView(BaseCSVImportView):
    """View for Person CSV importer."""

    importer_class = BasicPersonCSVImporter


class FlourishBasicPersonCSVImportView(FlourishBaseCSVImportView):

    importer_class = BasicPersonCSVImporter

    def nextURL(self):
        return absoluteURL(self.context, self.request)
