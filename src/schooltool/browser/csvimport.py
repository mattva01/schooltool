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

from zope.component import getUtility
from schooltool.browser import View, Template, ToplevelBreadcrumbsMixin
from schooltool.browser.auth import ManagerAccess
from schooltool.csvimport import CSVImporterBase, DataError
from schooltool.common import parse_date
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects, relate
from schooltool.interfaces import IApplication, IFacetFactory
from schooltool.membership import Membership, memberOf, belongsToParentGroup
from schooltool.teaching import Teaching
from schooltool.timetable import TimetableActivity
from schooltool.translation import ugettext as _
from schooltool.browser.widgets import SelectionWidget, TextWidget
from schooltool import uris

__metaclass__ = type


class CharsetMixin:

    def __init__(self, context):
        charsets = [('UTF-8', _('Unicode (UTF-8)')),
                    ('ISO-8859-1', _('Western (ISO-8859-1)')),
                    ('ISO-8859-15', _('Western (ISO-8859-15)')),
                    ('Windows-1252', _('Western (Windows-1252)')),
                    ('', _('Other (please specify)'))]
        self.charset_widget = SelectionWidget('charset', _('Charset'),
                                              charsets,
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
        persons_csv = request.args['persons.csv'][0]


        if not (groups_csv or resources_csv or persons_csv):
            self.error = _('No data provided.')
            return self.do_GET(request)

        try:
            for csv in [groups_csv, resources_csv, persons_csv]:
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
            if persons_csv:
                importer.importPersonsCsv(persons_csv.splitlines())
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
                factory = getUtility(IFacetFactory, facet_name)
            except KeyError:
                raise DataError(_("Unknown facet type: %s") % facet_name)
            facet = factory()
            FacetManager(group).setFacet(facet, name=factory.facet_name)
        self.logs.append(_('Imported group: %s') % name)
        return group.__name__

    def importPerson(self, name, surname, given_name, groups):
        title = ' '.join([given_name, surname])
        if not name:
            try:
                person = self.persons.new(title=title)
            except KeyError, e:
                raise DataError(_("Person already exists: %r") % name)
        else:
            try:
                person = self.persons.new(__name__=name, title=title)
            except KeyError, e:
                raise DataError(_("Person already exists: %r") % name)
            
        Membership(group=self.groups['root'], member=person)
        
        for group in groups.split():
            try:
                Membership(group=self.groups[group], member=person)
            except KeyError, e:
                raise DataError(_("No such group: %r") % group)
            except ValueError:
                raise DataError(_("Cannot add %r to %r") % (person, group))
        self.logs.append(_('Imported person: %s') % title)

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

    def importPersonInfo(self, name, surname, given_name, dob, comment):
        person = self.persons[name]
        infofacet = FacetManager(person).facetByName('person_info')

        try:
            infofacet.first_name = given_name
            infofacet.last_name = surname
        except ValueError:
            infofacet.first_name = ''
            infofacet.last_name = name        
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

    errors = None
    success = None

    def __init__(self, context):
        View.__init__(self, context)
        CharsetMixin.__init__(self, context)
        self.errors = []
        self.success = []

    def do_POST(self, request):
        try:
            charset = self.getCharset(request)
        except ValueError:
            return self.do_GET(request)

        timetable_csv = request.args['timetable.csv'][0]
        roster_txt = request.args['roster.txt'][0]

        if not (timetable_csv or roster_txt):
            self.errors.append(_('No data provided.'))
            return self.do_GET(request)

        try:
            unicode(timetable_csv, charset)
            roster_txt = unicode(roster_txt, charset)
        except UnicodeError:
            self.errors.append(_('Could not convert data to Unicode'
                                 ' (incorrect charset?).'))
            return self.do_GET(request)

        ok = True
        importer = TimetableCSVImporter(self.context, charset)
        if timetable_csv:
            ok = importer.importTimetable(timetable_csv)
            if ok:
                self.success.append(_("timetable.csv imported successfully."))
                request.appLog(_("School timetable imported"))
            else:
                self.errors.append(_("Failed to import timetable.csv"))
                self._presentErrors(importer.errors)
        if ok and roster_txt:
            ok = importer.importRoster(roster_txt)
            if ok:
                self.success.append(_("roster.txt imported successfully."))
                request.appLog(_("School timetable roster imported"))
            else:
                self.errors.append(("Failed to import roster.txt"))
                self._presentErrors(importer.errors)

        return self.do_GET(request)

    def _presentErrors(self, err):
        if err.generic:
            self.errors.extend(err.generic)


        for key, msg in [
            ('day_ids', _("Day ids not defined in selected schema: %s.")),
            ('periods', _("Periods not defined in selected days: %s.")),
            ('persons', _("Persons not found: %s.")),
            ('groups', _("Groups not found: %s.")),
            ('locations', _("Locations not found: %s.")),
            ('records', _("Invalid records: %s."))]:
            v = getattr(err, key)
            if v:
                values = ', '.join([repr(st) for st in v])
                self.errors.append(msg % values)


class ImportErrorCollection:

    def __init__(self):
        self.generic = []
        self.day_ids = []
        self.periods = []
        self.persons = []
        self.groups = []
        self.locations = []
        self.records = []

    def anyErrors(self):
        return bool(self.generic or self.day_ids or self.periods
                    or self.persons or self.groups
                    or self.locations or self.records)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__dict__)


class TimetableCSVImporter:
    """A timetable CSV parser and importer.

    Two externally useful methods are importTimetable and importRoster.
    """
    # Perhaps this class should be moved to schooltool.csvimport

    def __init__(self, app, charset=None):
        self.app = app
        self.groups = self.app['groups']
        self.persons = self.app['persons']
        self.errors = ImportErrorCollection()
        self.charset = charset
        self.cache = {}

    def importTimetable(self, timetable_csv):
        """Import timetables from CSV data.

        Should not throw exceptions, but will set self.*error attributes.
        Returns True on success.  If False is returned, it means that at least
        one of attributes of self.errors have been set, and no changes to the
        database have been applied.
        """
        rows = self.convertRowsToCSV(timetable_csv.splitlines())
        if rows is None:
            return False

        if len(rows[0]) != 2:
            self.errors.generic.append(
                    _("The first row of the CSV file should"
                      " contain the period id and the schema"
                      " of the timetable."))
            return False

        self.period_id, self.ttschema = rows[0]
        if self.ttschema not in self.app.timetableSchemaService.keys():
            self.errors.generic.append(
                _("The timetable schema %r does not exist." % self.ttschema))
            return False

        for dry_run in [True, False]:
            state = 'day_ids'
            for row_no, row in enumerate(rows[2:]):
                if row == [] or (len(row) == 1 and row[0] == ''):
                    state = 'day_ids'
                    continue
                elif state == 'day_ids':
                    day_ids = row
                    state = 'periods'
                    continue
                elif state == 'periods':
                    periods = row[1:]
                    self.validatePeriods(day_ids, periods)
                    state = 'content'
                    continue

                location, records = row[0], self.parseRecordRow(row[1:])
                if len(records) != len(periods):
                    self.errors.generic.append(
                            _("The number of cells %r (line %d) does"
                              " not match the number of periods %r."
                              % (row[1:], row_no + 3, periods)))
                    continue

                for period, record in zip(periods, records):
                    if record is not None:
                        subject, teacher = record
                        self.scheduleClass(period, subject, teacher,
                                           day_ids, location, dry_run=dry_run)
            if self.errors.anyErrors():
                assert dry_run, ("Something bad happened,"
                                 " aborting transaction.")
                return False
        return True

    def convertRowsToCSV(self, rows):
        """Convert rows (a list of strings) in CSV format to a list of lists.

        rows must be in the encoding specified during construction of
        TimetableCSVImportView; the returned values are in unicode.

        If the provided data is invalid, self.errors.generic will be updated
        and None will be returned.
        """
        result = []
        reader = csv.reader(rows)
        line = 0
        try:
            while True:
                line += 1
                values = reader.next()
                if self.charset:
                    values = [unicode(v, self.charset) for v in values]
                result.append(values)
        except StopIteration:
            return result
        except csv.Error:
            self.errors.generic.append(
                    _("Error in timetable CSV data, line %d" % line))
        except UnicodeError:
            self.errors.generic.append(
                    _("Conversion to unicode failed in line %d" % line))

    def parseRecordRow(self, records):
        """Parse records and return a list of tuples (subject, teacher).

        records is a list of strings.  If a string is empty, the result list
        contains None instead of a tuple in the corresponding place.

        If invalid entries are encountered, self.errors.records is modified
        and None is put in place of the malformed record.
        """
        result = []
        for record in records:
            if record.strip():
                parts = record.split("|", 1)
                if len(parts) != 2:
                    if record not in self.errors.records:
                        self.errors.records.append(record)
                    result.append(None)
                    continue
                subject, teacher = parts[0].strip(), parts[1].strip()
                result.append((subject, teacher))
            else:
                result.append(None)
        return result

    def validatePeriods(self, day_ids, periods):
        """Check if all periods are defined in the timetable schema."""
        tt = self.app.timetableSchemaService[self.ttschema]
        for day_id in day_ids:
            if day_id not in tt.keys():
                if day_id not in self.errors.day_ids:
                    self.errors.day_ids.append(day_id)
            else:
                valid_periods = tt[day_id].keys()
                for period in periods:
                    if (period not in valid_periods
                        and period not in self.errors.periods):
                        self.errors.periods.append(period)

    def _updateCache(self, container_name):
        """Update self.cache."""
        # I would be happy if this method lived in ApplicationObjectContainer
        objs = {}
        for obj in self.app[container_name].itervalues():
            objs[obj.title] = obj
        self.cache[container_name] = objs

    def findByTitle(self, container_name, title, error_list=None):
        """Find an object with provided title in a container.

        Raises KeyError if no object is found and error_list is not provided.
        Otherwise, adds the missing string to error_list (but does not create
        duplicates) and returns None.
        """
        objs = self.cache.get(container_name, {})
        if title not in objs:
            self._updateCache(container_name)
            objs = self.cache[container_name]
        obj = objs.get(title)
        if obj is not None:
            return obj
        else:
            if error_list is None:
                raise KeyError("Object %r not found" % title)
            else:
                if title not in error_list:
                    error_list.append(title)

    def clearTimetables(self):
        """Delete timetables of the period and schema we are dealing with."""
        for group in self.groups.itervalues():
            if (self.period_id, self.ttschema) in group.timetables.keys():
                del group.timetables[self.period_id, self.ttschema]

    def scheduleClass(self, period, subject, teacher,
                      day_ids, location, dry_run=False):
        """Schedule a class of subject during a given period.

        If dry_run is set, no objects are changed.
        """
        errors = False
        subject = self.findByTitle('groups', subject, self.errors.groups)
        teacher = self.findByTitle('persons', teacher, self.errors.persons)
        location = self.findByTitle('resources', location,
                                    self.errors.locations)
        if dry_run or not (subject and teacher and location):
            return # some objects were not found; do not process

        group_name = '%s - %s' % (subject.title, teacher.title)
        try:
            group = self.findByTitle('groups', group_name)
        except KeyError:
            group = self.groups.new(title=group_name)
            Membership(group=subject, member=group)

        if not teacher in getRelatedObjects(group, uris.URITeacher):
            relate(uris.URITeaching,
                   (teacher, uris.URITeacher), (group, uris.URITaught))

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
        """Import timetables from provided unicode data.

        Returns True on success, False (and filled self.error) on failure.
        """
        invalid = object()
        for dry_run in [True, False]:
            group = None
            for line in roster_txt.splitlines():
                line = line.strip()
                if group is None:
                    group = self.findByTitle('groups', line,
                                             self.errors.groups)
                    if group is None:
                        group = invalid
                    continue
                elif not line:
                    group = None
                    continue
                else:
                    person = self.findByTitle('persons', line,
                                              self.errors.persons)
                    if group is not invalid and person is not None:
                        if (self.app.restrict_membership
                            and not belongsToParentGroup(person, group)):
                            msg = _("%s does not belong to a parent group"
                                    " of %s") % (person.title, group.title)
                            self.errors.generic.append(msg)
                        else:
                            if not dry_run and not memberOf(person, group):
                                Membership(group=group, member=person)

            if self.errors.anyErrors():
                assert dry_run, ("Something bad happened,"
                                 " aborting transaction.")
                return False
        return True
