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
from schooltool.browser.auth import ManagerAccess
from schooltool.clients.csvclient import CSVImporterBase, DataError
from schooltool.common import to_unicode, parse_date
from schooltool.component import traverse, FacetManager, getFacetFactory
from schooltool.interfaces import IApplication
from schooltool.membership import Membership
from schooltool.teaching import Teaching
from schooltool.translation import ugettext as _


class CSVImportView(View):

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template('www/csvimport.pt')

    error = u""
    success = False

    def do_POST(self, request):
        groups_csv = to_unicode(request.args['groups.csv'][0])
        resources_csv = to_unicode(request.args['resources.csv'][0])
        teachers_csv = to_unicode(request.args['teachers.csv'][0])
        pupils_csv = to_unicode(request.args['pupils.csv'][0])

        if not (groups_csv or resources_csv or pupils_csv or teachers_csv):
            self.error = _('No data provided')
            return self.do_GET(request)

        importer = CSVImporterZODB(self.context)

        try:
            if groups_csv:
                importer.importGroupsCsv(groups_csv.splitlines())
            if resources_csv:
                importer.importResourcesCsv(resources_csv.splitlines())
            if teachers_csv:
                importer.importPersonsCsv(teachers_csv.splitlines(),
                                          'teachers', teaching=True)
            if pupils_csv:
                importer.importPersonsCsv(pupils_csv.splitlines(),
                                          'pupils', teaching=False)
        except DataError, e:
            self.error = unicode(e)
            return self.do_GET(request)

        request.appLog(_("CSV data imported")) # TODO: More verbose logging.
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
            other = traverse(self.groups, parent) # XXX exceptions
            Membership(group=other, member=group)
        for facet_name in facets.split():
            factory = getFacetFactory(facet_name)
            facet = factory() # XXX exceptions
            FacetManager(group).setFacet(facet, name=factory.facet_name)
        return group.__name__

    def importPerson(self, title, parent, groups, teaching=False):
        person = self.persons.new(title=title)
        if parent:
            Membership(group=self.groups[parent], member=person)

        if not teaching:
            for group in groups.split():
                Membership(group=self.groups[group], member=person)
        else:
            for group in groups.split():
                Teaching(teacher=person, taught=self.groups[group])

        return person.__name__

    def importResource(self, title, groups):
        resource = self.resources.new(title=title)
        for group in groups.split():
            other = traverse(self.groups, group) # XXX exceptions
            Membership(group=other, member=resource)
        return resource.__name__

    def importPersonInfo(self, name, title, dob, comment):
        person = self.persons[name]
        infofacet = FacetManager(person).facetByName('person_info')

        # XXX B0rks when title is one word.
        infofacet.first_name, infofacet.last_name = title.split(None, 1)

        infofacet.dob = parse_date(dob)
        infofacet.comment = comment
