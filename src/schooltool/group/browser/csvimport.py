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
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

import schooltool.skin.flourish.page
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.csvimport import BaseCSVImporter
from schooltool.app.browser.csvimport import BaseCSVImportView
from schooltool.app.browser.csvimport import FlourishBaseCSVImportView
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.group import Group
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


class GroupCSVImporter(BaseCSVImporter):
    """Group CSV Importer"""

    factory = Group

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

        obj = self.factory(title=data[0], description=description)
        name = self.chooser.chooseName('', obj)
        if not dry_run:
            self.container[name] = obj


class GroupCSVImportView(BaseCSVImportView):
    """View for Group CSV importer."""

    importer_class = GroupCSVImporter


class FlourishGroupCSVImportView(FlourishBaseCSVImportView, ActiveSchoolYearContentMixin):

    importer_class = GroupCSVImporter

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    def nextURL(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='groups')


class ImportGroupsLinkViewlet(flourish.page.LinkViewlet,
                              ActiveSchoolYearContentMixin):

    @property
    def url(self):
        link = self.link
        if not link:
            return None
        courses = IGroupContainer(self.schoolyear)
        return "%s/%s" % (absoluteURL(courses, self.request),
                          self.link)


class GroupMemberCSVImporter(BaseCSVImporter):
    """Group Member CSV Importer"""

    def createAndAdd(self, data, dry_run=True):
        """Create objects and add them to the container."""

        if len(data) < 1:
            self.errors.fields.append(_('Insufficient data provided.'))
            return

        if not data[0]:
            self.errors.fields.append(_('User names must not be empty.'))
            return

        app = ISchoolToolApplication(None)
        person_container = app['persons']
        username = data[0]

        if username not in person_container:
            self.errors.fields.append(_('"${username}" is not a valid username.',
                                        mapping={'username': username}))
            return

        user = person_container[username]
        if not dry_run:
            removeSecurityProxy(self.container.members).add(removeSecurityProxy(user))


class GroupMemberCSVImportView(BaseCSVImportView):
    """View for Group Member CSV importer."""

    importer_class = GroupMemberCSVImporter


class FlourishGroupMemberCSVImportView(FlourishBaseCSVImportView):

    importer_class = GroupMemberCSVImporter

    def nextURL(self):
        return absoluteURL(self.context, self.request)
