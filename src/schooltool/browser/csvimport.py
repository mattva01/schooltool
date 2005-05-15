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
"""
SchoolTool application views.

$Id$
"""

import csv
from zope.app.publisher.browser import BrowserView
from zope.app.container.interfaces import INameChooser
from schoolbell.relationship import getRelatedObjects, relate
from schoolbell.app.membership import Membership
from schooltool.interfaces import ISchoolToolApplication
from schooltool.app import Person, Section
from schooltool import SchoolToolMessageID as _
from schooltool.relationships import URIInstruction, URIInstructor, URISection
from schooltool.timetable import TimetableActivity
from zope.security.proxy import removeSecurityProxy


class TimetableCSVImportView(BrowserView):

    __used_for__ = ISchoolToolApplication

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.errors = []
        self.success = []

    def update(self):
        if "UPDATE_SUBMIT" not in self.request:
            return

        charset = self.getCharset()
        if charset is None:
            return

        timetable_csv = self.request['timetable.csv'] or ''
        if timetable_csv:
            timetable_csv = timetable_csv.read()
        roster_txt = self.request['roster.txt'] or ''
        if roster_txt:
            roster_txt = roster_txt.read()

        if not (timetable_csv or roster_txt):
            self.errors.append(_('No data provided'))
            return

        try:
            unicode(timetable_csv, charset)
            roster_txt = unicode(roster_txt, charset)
        except UnicodeError:
            self.errors.append(_('Could not convert data to Unicode'
                                 ' (incorrect charset?).'))
            return

        # XXX This removeSecurityProxy is here until we get proper security
        #     declarations for the various objects that TimetableCSVImporter
        #     touches (mostly timetable-related stuff).
        root = removeSecurityProxy(self.context)
        importer = TimetableCSVImporter(root, charset)
        ok = True
        if timetable_csv:
            ok = importer.importTimetable(timetable_csv)
            if ok:
                self.success.append(_("timetable.csv imported successfully."))
            else:
                self.errors.append(_("Failed to import timetable.csv"))
                self._presentErrors(importer.errors)
        if ok and roster_txt:
            ok = importer.importRoster(roster_txt)
            if ok:
                self.success.append(_("roster.txt imported successfully."))
            else:
                self.errors.append(("Failed to import roster.txt"))
                self._presentErrors(importer.errors)

    def _presentErrors(self, err):
        if err.generic:
            self.errors.extend(err.generic)

        for key, msg in [
            ('day_ids', _("Day ids not defined in selected schema: ${args}.")),
            ('periods', _("Periods not defined in selected days: ${args}.")),
            ('persons', _("Persons not found: ${args}.")),
            ('courses', _("Courses not found: ${args}.")),
            ('sections', _("Sections not found: ${args}.")),
            ('locations', _("Locations not found: ${args}.")),
            ('records', _("Invalid records: ${args}."))]:
            v = getattr(err, key)
            if v:
                values = ', '.join([unicode(st) for st in v])
                msg.mapping = {'args': values}
                self.errors.append(msg)

    def getCharset(self):
        """Return the charset (as a string) that was specified in the request.

        Updates self.errors and returns None if the charset was not specified
        or if it is invalid.
        """
        charset = self.request['charset']
        if charset == 'other':
            charset = self.request['other_charset']
        if not charset:
            self.errors.append(_("No charset specified"))
            return
        try:
            unicode(' ', charset)
        except LookupError:
            self.errors.append(_("Unknown charset"))
            return
        return charset


class ImportErrorCollection(object):

    def __init__(self):
        self.generic = []
        self.day_ids = []
        self.periods = []
        self.persons = []
        self.courses = []
        self.sections = []
        self.locations = []
        self.records = []

    def anyErrors(self):
        return bool(self.generic or self.day_ids or self.periods
                    or self.persons or self.courses or self.sections
                    or self.locations or self.records)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__dict__)


class TimetableCSVImporter(object):
    """A timetable CSV parser and importer.

    Two externally useful methods are importTimetable and importRoster.
    """
    # Perhaps this class should be moved to schooltool.csvimport

    def __init__(self, app, charset=None):
        self.app = app
        self.sections = self.app['sections']
        self.persons = self.app['persons']
        self.errors = ImportErrorCollection()
        self.charset = charset
        self.cache = {}

    def importTimetable(self, timetable_csv):
        """Import timetables from CSV data.

        Should not throw exceptions, but will set self.*error attributes.
        Returns True on success.  If False is returned, it means that at least
        one of attributes of self.errors have been set, and that no changes to
        the database have been applied.
        """
        rows = self.parseCSVRows(timetable_csv.splitlines())
        if rows is None:
            return False

        if len(rows[0]) != 2:
            self.errors.generic.append(
                    _("The first row of the CSV file must"
                      " contain the period id and the schema"
                      " of the timetable."))
            return False

        self.period_id, self.ttschema = rows[0]
        if self.ttschema not in self.app["ttschemas"].keys():
            error_msg = _("The timetable schema ${schema} does not exist.")
            error_msg.mapping = {'schema': self.ttschema}
            self.errors.generic.append(error_msg)
            return False

        for dry_run in [True, False]:
            state = 'day_ids'
            for row_no, row in enumerate(rows[2:]):
                if not row:
                    state = 'day_ids'
                    continue
                elif state == 'day_ids':
                    day_ids = row
                    state = 'periods'
                    continue
                elif state == 'periods':
                    if row[0]:
                        error_msg = _("The first cell on the period list row"
                                      " (${row_no}) should be empty.")
                        error_msg.mapping = {'row_no': row[0]}
                        self.errors.generic.append(error_msg)
                    periods = row[1:]
                    self.validatePeriods(day_ids, periods)
                    state = 'content'
                    continue

                location, records = row[0], self.parseRecordRow(row[1:])
                if len(records) > len(periods):
                    nice_row = ", ".join(row[1:])
                    nice_periods = ", ".join(periods)
                    error_msg = _("There are more records [${records}]"
                            " (line ${line_no}) than periods [${periods}].")
                    error_msg.mapping = {'records': nice_row,
                                         'line_no': row_no + 3,
                                         'periods': nice_periods}
                    self.errors.generic.append(error_msg)
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

    def parseCSVRows(self, rows):
        """Parse rows (a list of strings) in CSV format.

        Returns a list of rows as lists.

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
                values = [v.strip() for v in reader.next()]
                if self.charset:
                    values = [unicode(v, self.charset) for v in values]
                # Remove trailing empty cells.
                while values and not values[-1].strip():
                    del values[-1]
                result.append(values)
        except StopIteration:
            return result
        except csv.Error:
            error_msg = _("Error in timetable CSV data, line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)
        except UnicodeError:
            error_msg = _("Conversion to unicode failed in line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)

    def parseRecordRow(self, records):
        """Parse records and return a list of tuples (subject, teacher).

        records is a list of strings.

        If invalid entries are encountered, self.errors.records is modified
        and None is put in place of the malformed record.
        """
        result = []
        for record in records:
            if record:
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
        tt = self.app["ttschemas"][self.ttschema]
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
        """Maintain the internal mapping of titles to objects.

        This method maintains self.cache, which is a mapping from container
        names to dicts.  Each dict is a mapping from object titles to objects.

        The cache is an optimization so that we do not have to do a linear
        search every time we need to pick an object by title.
        """
        # I would be happy if this method lived in ApplicationObjectContainer
        objs = {}
        for obj in self.app[container_name].values():
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
                raise KeyError("Object %s not found" % title)
            else:
                if title not in error_list:
                    error_list.append(title)

    def clearTimetables(self):
        """Delete timetables of the period and schema we are dealing with."""
        for section in self.sections.values():
            key = ".".join((self.period_id, self.ttschema))
            if key in section.timetables.keys():
                del section.timetables[key]

    def scheduleClass(self, period, course_name, teacher,
                      day_ids, location, dry_run=False):
        """Schedule a class of course during a given period.

        If dry_run is set, no objects are changed.
        """
        errors = False
        course = self.findByTitle('courses', course_name, self.errors.courses)
        teacher = self.findByTitle('persons', teacher, self.errors.persons)
        location = self.findByTitle('resources', location,
                                    self.errors.locations)
        if dry_run or not (course and teacher and location):
            return # some objects were not found; do not process

        section_name = '%s - %s' % (course.title, teacher.title)
        try:
            section = self.findByTitle('sections', section_name)
        except KeyError:
            section = Section(title=section_name)
            chooser = INameChooser(self.sections)
            section_name = chooser.chooseName('', section)
            self.sections[section_name] = section
            course.sections.add(section)

        if not teacher in section.instructors:
            section.instructors.add(teacher)

        # Create the timetable if it does not exist yet.
        timetable_key = ".".join((self.period_id, self.ttschema))
        if timetable_key not in section.timetables.keys():
            tt = self.app["ttschemas"][self.ttschema]
            section.timetables[timetable_key] = tt
        else:
            tt = section.timetables[timetable_key]

        # Add a new activity to the timetable
        act = TimetableActivity(title=course.title, owner=section,
                                resources=(location, ))
        for day_id in day_ids:
            tt[day_id].add(period, act)

    def importRoster(self, roster_txt):
        """Import timetables from provided unicode data.

        Returns True on success, False (and filled self.error) on failure.
        """
        invalid = object()
        for dry_run in [True, False]:
            section = None
            for line in roster_txt.splitlines():
                line = line.strip()
                if section is None:
                    section = self.findByTitle('sections', line,
                                               self.errors.sections)
                    if section is None:
                        section = invalid
                    continue
                elif not line:
                    section = None
                    continue
                else:
                    person = self.findByTitle('persons', line,
                                              self.errors.persons)
                    if section is not invalid and person is not None:
                        if (not dry_run and person not in section.learners):
                            section.learners.add(person)

            if self.errors.anyErrors():
                assert dry_run, ("Something bad happened,"
                                 " aborting transaction.")
                return False
        return True
