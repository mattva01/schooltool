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

from schooltool.browser import View, Template
from schooltool.browser.auth import ManagerAccess
from schooltool.csvimport import CSVImporterBase, DataError
from schooltool.common import parse_date
from schooltool.component import FacetManager, getFacetFactory
from schooltool.interfaces import IApplication
from schooltool.membership import Membership
from schooltool.teaching import Teaching
from schooltool.translation import ugettext as _
from schooltool.browser.widgets import SelectionWidget, TextWidget


class CSVImportView(View):

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template('www/csvimport.pt')

    error = u""
    success = False

    charsets = [('UTF-8', _('Unicode (UTF-8)')),
                ('ISO-8859-1', _('Western (ISO-8859-1)')),
                ('ISO-8859-15', _('Western (ISO-8859-15)')),
                ('Windows-1252', _('Western (Windows-1252)')),
                ('', _('Other (please specify)'))]

    def __init__(self, context):
        View.__init__(self, context)
        self.charset_widget = SelectionWidget('charset', _('Charset'),
                                              self.charsets,
                                              validator=self.validate_charset)
        self.other_charset_widget = TextWidget('other_charset',
                                               _('Specify other'),
                                               validator=self.validate_charset)

    def validate_charset(self, charset):
        if not charset:
            return
        try:
            unicode(' ', charset)
        except LookupError:
            raise ValueError(_('Unknown charset'))

    def do_POST(self, request):
        self.charset_widget.update(request)
        self.charset_widget.require()
        if self.charset_widget.error:
            return self.do_GET(request)

        self.other_charset_widget.update(request)
        if not self.charset_widget.value:
            if self.other_charset_widget.value == "":
                # Force a "field is required" error if value is ""
                self.other_charset_widget.setRawValue(None)
            self.other_charset_widget.require()
        if self.other_charset_widget.error:
            return self.do_GET(request)

        charset = self.charset_widget.value or self.other_charset_widget.value

        groups_csv = request.args['groups.csv'][0]
        resources_csv = request.args['resources.csv'][0]
        teachers_csv = request.args['teachers.csv'][0]
        pupils_csv = request.args['pupils.csv'][0]

        if not (groups_csv or resources_csv or pupils_csv or teachers_csv):
            self.error = _('No data provided.')
            return self.do_GET(request)

        try:
            unicode(groups_csv, charset)
            unicode(resources_csv, charset)
            unicode(teachers_csv, charset)
            unicode(pupils_csv, charset)
        except UnicodeError:
            self.error = _('Could not convert data to Unicode'
                           ' (incorrect charset?).')
            return self.do_GET(request)

        importer = CSVImporterZODB(self.context, charset)

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

        self.success = True
        request.appLog(_("CSV data import started"))
        for log_entry in importer.logs:
            request.appLog(log_entry)
        request.appLog(_("CSV data import finished successfully"))

        return self.do_GET(request)


class CSVImporterZODB(CSVImporterBase):
    """A CSV importer that works directly with the database."""

    def __init__(self, app, charset):
        self.groups = app['groups']
        self.persons = app['persons']
        self.resources = app['resources']
        self.logs = []
        self.charset = charset

    def recode(self, value):
        return unicode(value, self.charset)

    def importGroup(self, name, title, parents, facets):
        group = self.groups.new(__name__=name, title=title)
        for parent in parents.split():
            other = self.groups[parent]
            Membership(group=other, member=group)
        for facet_name in facets.split():
            try:
                factory = getFacetFactory(facet_name)
            except KeyError:
                raise DataError(_("Unknown facet type: %s") % facet_name)
            facet = factory()
            FacetManager(group).setFacet(facet, name=factory.facet_name)
        self.logs.append(_('Imported group: %s') % name)
        return group.__name__

    def importPerson(self, title, parent, groups, teaching=False):
        person = self.persons.new(title=title)
        if parent:
            try:
                Membership(group=self.groups[parent], member=person)
            except KeyError:
                raise DataError(_("Invalid group: %s") % parent)

        try:
            if not teaching:
                for group in groups.split():
                    Membership(group=self.groups[group], member=person)
                self.logs.append(_('Imported person: %s') % title)
            else:
                for group in groups.split():
                    Teaching(teacher=person, taught=self.groups[group])
                self.logs.append(_('Imported person (teacher): %s') % title)
        except KeyError:
            raise DataError(_("Invalid group: %s") % group)

        return person.__name__

    def importResource(self, title, groups):
        resource = self.resources.new(title=title)
        for group in groups.split():
            try:
                other = self.groups[group]
            except KeyError:
                raise DataError(_("Invalid group: %s") % group)
            Membership(group=other, member=resource)
        self.logs.append(_('Imported resource: %s') % title)
        return resource.__name__

    def importPersonInfo(self, name, title, dob, comment):
        person = self.persons[name]
        infofacet = FacetManager(person).facetByName('person_info')

        try:
            infofacet.first_name, infofacet.last_name = title.split(None, 1)
        except ValueError:
            infofacet.first_name = ''
            infofacet.last_name = title

        if dob:
            infofacet.date_of_birth = parse_date(dob)
        else:
            infofacet.date_of_birth = None
        infofacet.comment = comment
        self.logs.append(_('Imported person info for %s (%s %s, %s)')
                         % (name, infofacet.first_name, infofacet.last_name,
                            infofacet.date_of_birth))
