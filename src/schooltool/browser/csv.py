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
Web-application views for managing SchoolTool data in CSV format.

$Id$
"""

import datetime

from schooltool.browser import View, Template
from schooltool.clients.csvclient import CSVImporterBase  # XXX Foreign import
from schooltool.component import traverse, FacetManager
from schooltool.interfaces import IApplication
from schooltool.membership import Membership
from schooltool.translation import ugettext as _


class CSVImportView(View):

    __used_for__ = IApplication

    template = Template('www/csvimport.pt')

    error = u""
    success = False

    def do_POST(self, request):
        groups_csv = resources_csv = None
        if 'groups.csv' in request.args:
            groups_csv = request.args['groups.csv'][0]

        if groups_csv is None and resources_csv is None:
            self.error = _('No files provided')
            return self.do_GET(request)

        importer = CSVImporterZODB(self.context)
        if groups_csv is not None:
            importer.importGroupsCsv(groups_csv.splitlines())

        request.appLog(_("CSV data imported"))
        self.success = True
        return self.do_GET(request)


class CSVImporterZODB(CSVImporterBase):
    """A CSV importer that works directly with the database."""

    def __init__(self, root):
        self.groups = root['groups']
        self.persons = root['persons']
        self.resources = root['resources']

    def importGroup(self, name, title, parents, facets):
        group = self.groups.new(__name__=name, title=title)
        for parent in parents.split():
            other = traverse(self.groups, parent) # XXX TODO exceptions
            Membership(group=other, member=group)
            # TODO: facets
        return group.__name__

    def importPerson(self, title, parent, groups, teaching=False):
        person = self.persons.new(title=title)
        # TODO: process other arguments
        return person.__name__

    def importResource(self, title, groups):
        resource = self.resources.new(title=title)
        for group in groups.split():
            other = traverse(self.groups, group) # XXX TODO exceptions
            Membership(group=other, member=resource)
        return resource.__name__

    def importPersonInfo(self, name, title, dob, comment):
        person = self.persons[name]
        infofacet = FacetManager(person).facetByName('person_info')

        infofacet.first_name, infofacet.last_name = title.split(None, 1)

        # XXX error checking
        date_elements = [int(el) for el in dob.split('-')]
        infofacet.dob = datetime.date(*date_elements)
        infofacet.comment = comment


