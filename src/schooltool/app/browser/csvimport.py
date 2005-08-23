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

from zope.security.proxy import removeSecurityProxy
from zope.app.container.interfaces import INameChooser
from zope.app.publisher.browser import BrowserView

from schooltool.person.person import Person

from schooltool import SchoolToolMessageID as _
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.app import SimpleNameChooser
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.section import Section
from schooltool.timetable import TimetableActivity
from schooltool.timetable.interfaces import ITimetables


class ImportErrorCollection(object):
    """A simple container for import errors.

    This class just holds errors that occur in the CSVImporter class so they
    can be dealt with by the CSVImportView class.
    """

    def __init__(self):
        self.generic = []
        self.fields = []

    def anyErrors(self):
        return bool(self.generic or self.fields)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__dict__)


class TimetableImportErrorCollection(object):

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


class InvalidCSVError(Exception):
    pass


class BaseCSVImportView(BrowserView):

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

        csvfile = self.request.get('csvfile', '')
        if csvfile:
            csvfile = csvfile.read()

        csvtext = self.request.get('csvtext', '')

        if not csvfile and not csvtext:
            self.errors.append(_('No data provided'))
            return

        if csvfile:
            try:
                unicode(csvfile, charset)
            except UnicodeError:
                self.errors.append(_('Could not convert data to Unicode'
                                     ' (incorrect charset?).'))
                return

        self.importer = self.importer_class(self.context, charset)
        ok = True
        if csvfile:
            ok = self.importer.importFromCSV(csvfile)
            if ok:
                self.success.append(_("CSV file imported successfully."))
            else:
                self.errors.append(_("Failed to import CSV file"))
                self._presentErrors(self.importer.errors)

        ok = True
        if csvtext:
            self.importer.charset = None
            ok = self.importer.importFromCSV(csvtext)
            if ok:
                self.success.append(_("CSV text imported successfully."))
            else:
                self.errors.append(_("Failed to import CSV text"))
                self._presentErrors(self.importer.errors)

    def _presentErrors(self, err):
        """Add any errors in our ErrorCollection to the view errors.
        """
        if err.generic:
            self.errors.extend(err.generic)

        if err.fields:
            self.errors.extend(err.fields)

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


class BaseCSVImporter(object):
    """A base class for CSV parsers and importers.

    Subclasses should define the createAndAdd method.
    """

    def __init__(self, container, charset=None):
        self.container = container
        self.errors = ImportErrorCollection()
        self.charset = charset
        self.chooser = SimpleNameChooser(container)

    def parseCSVRows(self, rows):
        """Parse rows (a list of strings) in CSV format.

        Returns a list of rows as lists.

        rows must be in the encoding specified during construction of
        BaseCSVImportView; the returned values are in unicode.

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
            error_msg = _("Error in CSV data, line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)
        except UnicodeError:
            error_msg = _("Conversion to unicode failed in line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)

    def importFromCSV(self, csvdata):
        """Import objects from CSV data.

        Should not throw exceptions, but will set self.*error attributes.
        Returns True on success.  If False is returned, it means that at least
        one of attributes of self.errors have been set, and that no changes to
        the database have been applied.
        """
        rows = self.parseCSVRows(csvdata.splitlines())
        if rows is None:
            return False

        for dry_run in [True, False]:

            for rowdata in rows:
                self.createAndAdd(rowdata, dry_run)

            if self.errors.anyErrors():
                assert dry_run, ("Something bad happened,"
                                 " aborting transaction.") # XXX
                return False

        return True

    def createAndAdd(self, obj, dry_run=True):
        """Create object and add to container.

        If dry_run is True, don't actually do anything, just validate the data.

        This should be defined in the subclass.
        """
        raise NotImplementedError("Please override this method in subclasses")


# XXX: This should be in the schooltool.timetable package.
class TimetableCSVImporter(object):
    """A timetable CSV parser and importer.

    You will most likely want to use the importFromCSV(csvdata) method.

    This class does not use exceptions for handling errors excessively
    because of the nature of error-checking: we want to gather many errors
    in one sweep and present them to the user at once.
    """

    def __init__(self, container, charset=None):
        # XXX It appears that our security declarations are inadequate,
        #     because things break without this removeSecurityProxy.
        self.app = getSchoolToolApplication()
        self.sections = removeSecurityProxy(container)
        self.persons = self.app['persons']
        self.errors = TimetableImportErrorCollection()
        self.charset = charset

    def importSections(self, sections_csv): # TODO: see importFromCSV
        """Import sections from CSV data.

        At the top of the file there should be a header row:

        timetable_schema_id, term_id

        Then an empty line should follow, and the remaining CSV data should
        consist of chunks like this:

        course_id, instructor_id
        day_id, period_id[, location_id]
        day_id, period_id[, location_id]
        ...
        ***
        student_id
        student_id
        ...

        """
        if '\n' not in sections_csv:
            self.errors.generic.append(_("No data provided"))
            raise InvalidCSVError()

        rows = self.parseCSVRows(sections_csv.splitlines())

        if rows[1]:
            self.errors.generic.append(_("Row 2 is not empty"))
            raise InvalidCSVError()

        self.importHeader(rows[0])
        if self.errors.anyErrors():
            raise InvalidCSVError()

        self.importChunks(rows[2:], dry_run=True)
        if self.errors.anyErrors():
            raise InvalidCSVError()

        self.importChunks(rows[2:], dry_run=False)
        if self.errors.anyErrors():
            raise AssertionError('something bad happened while importing CSV'
                                 ' data, aborting transaction.')

    def importChunks(self, rows, dry_run=True):
        """Import chunks separated by empty lines."""
        chunk_start = 0
        for i, row in enumerate(rows):
            if not row:
                if rows[chunk_start]:
                    self.importChunk(rows[chunk_start:i],
                                     chunk_start + 3, dry_run)
                chunk_start = i + 1
        if rows and rows[-1]:
            self.importChunk(rows[chunk_start:], chunk_start + 3, dry_run)

    def importChunk(self, rows, line, dry_run=True):
        """Import a chunk of data that describes a section.

        You should run this method with dry_run=True before trying the
        real thing, or you might get in trouble.
        """
        # TODO: split up this method
        course_id, instructor_id = rows[0]

        course = self.app['courses'].get(course_id, None)
        if course is None:
            self.errors.courses.append(course_id)

        instructor = self.persons.get(instructor_id, None)
        if instructor is None:
            self.errors.persons.append(instructor_id)

        invalid_location = object() # marker
        line_ofs = 1
        periods = []
        finished = False
        for row in rows[1:]:
            line_ofs += 1
            if row == ['***']:
                finished = True
                break
            elif len(row) == 2:
                day_id, period_id = row
                location_id = None
            elif len(row) == 3:
                day_id, period_id, location_id = row
            else:
                err_msg = _('Malformed line ${line_no} (it should contain a'
                            ' day id, a period id and optionally a location'
                            ' id)')
                err_msg.mapping = {'line_no': line + line_ofs - 1}
                self.errors.generic.append(err_msg)
                continue

            # check resource_id
            if location_id:
                try:
                    location = self.app['resources'][location_id]
                except KeyError:
                    if location_id not in self.errors.locations:
                        location = invalid_location
                        self.errors.locations.append(location_id)
            else:
                location = None

            # check day_id
            try:
                ttday = self.ttschema[day_id]
            except KeyError:
                if day_id not in self.errors.day_ids:
                    self.errors.day_ids.append(day_id)
                continue

            # check period_id
            if (period_id not in ttday.periods
                and period_id not in self.errors.periods):
                self.errors.periods.append(period_id)
                continue

            periods.append((day_id, period_id, location))

        if not finished or len(rows) == line_ofs:
            err_msg = _("Incomplete section description on line ${line}")
            err_msg.mapping = {'line': line}
            self.errors.generic.append(err_msg)
            return

        section = self.createSection(course, instructor, periods,
                                     dry_run=dry_run)
        self.importPersons(rows[line_ofs:], section, dry_run=dry_run)

    def createSection(self, course, instructor, periods, dry_run=True):
        """Create a section.

        `periods` is a list of tuples (day_id, period_id, location).
        `location` is a Resource object, or None, in which case no
        resource is booked.

        A title is generated from the titles of `course` and `instructor`.
        If an existing section with the same title is found, it is used instead
        of creating a new one.

        The created section is returned, or None if dry_run is True.
        """
        if dry_run:
            return None

        # Create or pick a section.
        section_title = '%s - %s' % (course.title, instructor.title)
        for sctn in self.app['sections'].values():
            # Look for an existing section with the same title.
            if sctn.title == section_title:
                section = sctn
                break
        else:
            # No existing sections with this title found, create a new one.
            section = Section(title=section_title)
            chooser = INameChooser(self.sections)
            section_name = chooser.chooseName('', section)
            self.sections[section_name] = section

        # Establish links to course and to teacher
        if course not in section.courses:
            section.courses.add(course)
        if instructor not in section.instructors:
            section.instructors.add(instructor)

        # Create a timetable
        timetables = ITimetables(section).timetables
        timetable_key = ".".join((self.term.__name__, self.ttschema.__name__))
        if timetable_key not in timetables.keys():
            tt = self.ttschema.createTimetable()
            timetables[timetable_key] = tt
        else:
            tt = timetables[timetable_key]

        # Add timetable activities.
        for day_id, period_id, location in periods:
            if location is not None:
                resources = (location, )
            else:
                resources = ()
            act = TimetableActivity(title=course.title, owner=section,
                                    resources=resources)
            tt[day_id].add(period_id, act)

        return section

    def importPersons(self, person_data, section, dry_run=True):
        """Import persons into a section."""
        for row in person_data:
            person_id = row[0]
            try:
                person = self.persons[person_id]
            except KeyError:
                if person_id not in self.errors.persons:
                    self.errors.persons.append(person_id)
            else:
                if not dry_run:
                    if person not in section.members:
                        section.members.add(person)

    def importHeader(self, row):
        """Read the header row of the CSV file.

        Sets self.term and self.ttschema.
        """
        if len(row) != 2:
            self.errors.generic.append(
                    _("The first row of the CSV file must contain"
                      " the term id and the timetable schema id."))
            return

        term_id, ttschema_id = row

        try:
            self.term = self.app['terms'][term_id]
        except KeyError:
            error_msg = _("The term ${term} does not exist.")
            error_msg.mapping = {'term': term_id}
            self.errors.generic.append(error_msg)

        try:
            self.ttschema = self.app['ttschemas'][ttschema_id]
        except KeyError:
            error_msg = _("The timetable schema ${schema} does not exist.")
            error_msg.mapping = {'schema': ttschema_id}
            self.errors.generic.append(error_msg)

    def parseCSVRows(self, rows):
        """Parse rows (a list of strings) in CSV format.

        Returns a list of rows as lists.  Trailing empty cells are discarded.

        rows must be in the encoding specified during construction of
        TimetableCSVImportView; the returned values are in unicode.

        If the provided data is invalid, self.errors.generic will be updated
        and InvalidCSVError will be returned.
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
            raise InvalidCSVError()
        except UnicodeError:
            error_msg = _("Conversion to unicode failed in line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)
            raise InvalidCSVError()

    def importFromCSV(self, csvdata):
        """Invoke importSections while playing with BaseCSVImportView nicely.

        Currently sb.BaseCSVImportView expects ImporterClass.importFromCSV
        return True on success, False on error.  It would be nicer if it
        caught InvalidCSVErrors instead.  When this refactoring is performed,
        this method may be removed and importSections can be renamed to
        importFromCSV.
        """
        try:
            self.importSections(csvdata)
        except InvalidCSVError:
            return False
        else:
            return True


class TimetableCSVImportView(BaseCSVImportView):
    """Timetable CSV import view."""

    __used_for__ = ISectionContainer

    importer_class = TimetableCSVImporter

    def _presentErrors(self, err):
        if err.generic:
            self.errors.extend(err.generic)

        # XXX: Shrug, this seems not very extensible.
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
