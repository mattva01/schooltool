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

import csv

from schooltool.browser import View, Template, ToplevelBreadcrumbsMixin
from schooltool.browser.auth import ManagerAccess
from schooltool.csvimport import CSVImporterBase, DataError
from schooltool.common import parse_date
from schooltool.component import FacetManager, getFacetFactory, relate
from schooltool.interfaces import IApplication
from schooltool.membership import Membership
from schooltool.teaching import Teaching
from schooltool.timetable import TimetableActivity
from schooltool.translation import ugettext as _
from schooltool.browser.widgets import SelectionWidget, TextWidget
from schooltool.uris import URIMembership, URIMember, URIGroup

__metaclass__ = type


class CharsetMixin:

    charsets = [('UTF-8', _('Unicode (UTF-8)')),
                ('ISO-8859-1', _('Western (ISO-8859-1)')),
                ('ISO-8859-15', _('Western (ISO-8859-15)')),
                ('Windows-1252', _('Western (Windows-1252)')),
                ('', _('Other (please specify)'))]

    def __init__(self, context):
        self.charset_widget = SelectionWidget('charset', _('Charset'),
                                              self.charsets,
                                              validator=self.validate_charset)
        self.other_charset_widget = TextWidget('other_charset',
                                               _('Specify other charset'),
                                               validator=self.validate_charset)

    def getCharset(self, request):
        """Return the charset (as a string) that was specified in request.

        Uses the widgets charset_widget and other_charset_widget.
        Raises ValueError if the charset is missing or invalid.
        """
        self.charset_widget.update(request)
        if self.charset_widget.error:
            raise ValueError("No charset specified")

        if not self.charset_widget.value:
            self.other_charset_widget.update(request)
            if self.other_charset_widget.value == "":
                # Force a "field is required" error if value is ""
                self.other_charset_widget.setRawValue(None)
            self.other_charset_widget.require()
            if self.other_charset_widget.error:
                raise ValueError("No charset specified")
        return (self.charset_widget.value or self.other_charset_widget.value)

    def validate_charset(self, charset):
        if not charset:
            return
        try:
            unicode(' ', charset)
        except LookupError:
            raise ValueError(_('Unknown charset'))


class CSVImportView(View, CharsetMixin, ToplevelBreadcrumbsMixin):
    """A view for importing SchoolTool objects in CSV format."""

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template('www/csvimport.pt')

    error = u""
    success = False

    def __init__(self, context):
        View.__init__(self, context)
        CharsetMixin.__init__(self, context)

    def do_POST(self, request):
        try:
            charset = self.getCharset(request)
        except ValueError:
            return self.do_GET(request)

        groups_csv = request.args['groups.csv'][0]
        resources_csv = request.args['resources.csv'][0]
        teachers_csv = request.args['teachers.csv'][0]
        pupils_csv = request.args['pupils.csv'][0]

        if not (groups_csv or resources_csv or pupils_csv or teachers_csv):
            self.error = _('No data provided.')
            return self.do_GET(request)

        try:
            for csv in [groups_csv, resources_csv, teachers_csv, pupils_csv]:
                unicode(csv, charset)
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
                                          'teachers')
            if pupils_csv:
                importer.importPersonsCsv(pupils_csv.splitlines(),
                                          'pupils')
        except DataError, e:
            self.error = _("Import failed: %s") % e
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
        try:
            group = self.groups.new(__name__=name, title=title)
        except KeyError, e:
            raise DataError(_("Group already exists: %r") % name)

        for path in parents.split():
            try:
                parent = self.groups[path]
            except KeyError:
                raise DataError(_("No such group: %s") % path)
            try:
                Membership(group=parent, member=group)
            except ValueError, e:
                raise DataError(_("Cannot add %s to group %s") %
                                (group, parent))

        for facet_name in facets.split():
            try:
                factory = getFacetFactory(facet_name)
            except KeyError:
                raise DataError(_("Unknown facet type: %s") % facet_name)
            facet = factory()
            FacetManager(group).setFacet(facet, name=factory.facet_name)
        self.logs.append(_('Imported group: %s') % name)
        return group.__name__

    def importPerson(self, title, parent, groups, teaches=None):
        try:
            person = self.persons.new(title=title)
        except KeyError, e:
            raise DataError(_("Person already exists: %r") % name)

        if parent:
            try:
                Membership(group=self.groups[parent], member=person)
            except KeyError:
                raise DataError(_("Invalid group: %s") % parent)
        Membership(group=self.groups['root'], member=person)
        for group in groups.split():
            try:
                Membership(group=self.groups[group], member=person)
            except KeyError, e:
                raise DataError(_("No such group: %r") % group)
            except ValueError:
                raise DataError(_("Cannot add %r to %r") % (person, group))
        self.logs.append(_('Imported person: %s') % title)
        if teaches:
            for group in teaches.split():
                try:
                    Teaching(teacher=person, taught=self.groups[group])
                except KeyError, e:
                    raise DataError(_("No such group: %r") % group)
                except ValueError:
                    raise DataError(_("Cannot add %r as a teacher for %r")
                                    % (person, group))

        return person.__name__

    def importResource(self, title, groups):
        resource = self.resources.new(title=title)
        for group in groups.split():
            try:
                other = self.groups[group]
            except KeyError:
                raise DataError(_("Invalid group: %s") % group)
            try:
                Membership(group=other, member=resource)
            except ValueError:
                raise DataError(_("Cannot add %r to %r") % (person, group))
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


class TimetableCSVImportView(View, CharsetMixin, ToplevelBreadcrumbsMixin):
    """View to upload the school timetable as CSV."""

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template("www/timetable-csvupload.pt")

    error = None
    success = None

    def __init__(self, context):
        View.__init__(self, context)
        CharsetMixin.__init__(self, context)

    def do_POST(self, request):
        try:
            charset = self.getCharset(request)
        except ValueError:
            return self.do_GET(request)

        timetable_csv = request.args['timetable.csv'][0]
        roster_txt = request.args['roster.txt'][0]

        if not (timetable_csv or roster_txt):
            self.error = _('No data provided.')
            return self.do_GET(request)

        try:
            # TODO timetable_csv = unicode(timetable_csv, charset) ?
            unicode(timetable_csv, charset)
            roster_txt = unicode(roster_txt, charset)
        except UnicodeError:
            self.error = _('Could not convert data to Unicode'
                           ' (incorrect charset?).')
            return self.do_GET(request)

        importer = TimetableCSVImporter()
        try:
            if timetable_csv:
                self.importTimetable(timetable_csv)
            if roster_txt:
                self.importRoster(roster_txt)
        except DataError, e:
            self.error = _("Import failed: %s") % e
            return self.do_GET(request)

        # TODO: log import
        return self.do_GET(request)


class TimetableCSVImporter:
    """A timetable CSV parser and importer.

    Two externally useful methods are importTimetable and importRoster.
    """
    # Perhaps this class should be moved to schooltool.csvimport

    def __init__(self, app):
        self.app = app
        self.groups = self.app['groups']
        self.persons = self.app['persons']

    def importTimetable(self, timetable_csv):
        """Import timetables from CSV data.

        May throw various exceptions (to be improved).
        """
        if not timetable_csv:
            return # XXX Should we complain?
        reader = csv.reader(timetable_csv.splitlines())
        try:
            rows = list(reader)
        except csv.Error, e:
            raise ValueError("Invalid CSV")

        self.period_id, self.ttschema = rows[0]
        state = 'day_ids'
        for row in rows[2:]:
            if not row:
                state = 'day_ids'
                continue
            elif state == 'day_ids':
                day_ids = row
                state = 'periods'
                continue
            elif state == 'periods':
                periods = row[1:]
                for period in periods:
                    pass # TODO: check existence of periods

                state = 'content'
                continue

            location, records = row[0], self.parseRecordRow(row[1:])

            for period, record in zip(periods, records):
                if record is not None:
                    subject, teacher = record
                    self.scheduleClass(period, subject, teacher,
                                       day_ids, location)

    def parseRecordRow(self, records):
        """Parse records and return a list of tuples (subject, teacher).

        records is a list of strings.  If a string is empty, the result list
        contains None instead of a tuple in the corresponding place.

        TODO: error handling
        """
        result = []
        for record in records:
            if record:
                # TODO: introduce a better separator than a space
                record = record.split(" ", 1)
                result.append(tuple(record))
            else:
                result.append(None)
        return result

    def findByTitle(self, container, title):
        """Find an object with provided title in a container.

        Raises KeyError if no object is found.
        """
        # TODO Speed this up by constructing a dict once
        for obj in container.itervalues():
            if obj.title == title:
                return obj
        else:
            raise KeyError("Object %r not found" % title)

    def clearTimetables(self):
        """Delete timetables of the period and schema we are dealing with."""
        for group in self.groups.itervalues():
            if (self.period_id, self.ttschema) in group.timetables.keys():
                del group.timetables[self.period_id, self.ttschema]

    def scheduleClass(self, period, subject, teacher, day_ids, location):
        """Schedule a class of subject during a given period."""
        try: # TODO: nicer error handling
            subject = self.findByTitle(self.groups, subject)
        except KeyError:
            raise ValueError('Group %r not found' % subject)
        try:
            teacher = self.findByTitle(self.persons, teacher)
        except KeyError:
            raise ValueError('Person %r not found' % teacher)
        # TODO: should we check that teacher has role URITeacher for group?

        location = self.findByTitle(self.app['resources'], location)

        group_name = '%s - %s' % (subject.title, teacher.title)
        try:
            group = self.findByTitle(self.groups, group_name)
        except KeyError:
            group = self.groups.new(title=group_name)
            # TODO: set up teaching and membership relationships

        # Create the timetable if it does not exist yet.
        if (self.period_id, self.ttschema) not in group.timetables.keys():
            tt = self.app.timetableSchemaService[self.ttschema]
            group.timetables[self.period_id, self.ttschema] = tt
        else:
            tt = group.timetables[self.period_id, self.ttschema]

        # Add a new activity to the timetable
        act = TimetableActivity(title=subject.title, owner=group,
                                resources=(location, ))
        for day_id in day_ids:
            tt[day_id].add(period, act)

    def importRoster(self, roster_txt):
        """Import timetables from provided unicode data."""
        group = None
        for line in roster_txt.splitlines():
            if group is None:
                group = self.findByTitle(self.groups, line)
                continue
            elif not line:
                group = None
                continue
            else:
                person = self.findByTitle(self.persons, line)
                relate(URIMembership, (person, URIMember), (group, URIGroup))
