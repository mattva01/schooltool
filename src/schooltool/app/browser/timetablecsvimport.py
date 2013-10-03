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
SchoolTool timetable csv import.

XXX: This should be in the schooltool.timetable package.
"""
import csv
import pprint

from zope.container.interfaces import INameChooser
from zope.proxy import sameProxiedObjects
from zope.traversing.browser.absoluteurl import absoluteURL

import schooltool.skin.flourish.page
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.csvimport import BaseCSVImportView
from schooltool.course.interfaces import ICourseContainer
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.section import Section
from schooltool.app.browser.csvimport import FlourishBaseCSVImportView
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.term.interfaces import ITermContainer
from schooltool.term.term import getNextTerm
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.interfaces import IScheduleContainer
from schooltool.timetable.timetable import SelectedPeriodsSchedule
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


class TimetableImportErrorCollection(object):

    def __init__(self):
        self.generic = []
        self.day_ids = []
        self.periods = []
        self.persons = []
        self.courses = []
        self.sections = []
        self.records = []

    def anyErrors(self):
        return bool(self.generic or self.day_ids or self.periods
                    or self.persons or self.courses or self.sections
                    or self.records)

    def __str__(self):
        return '%s:\n%s' % (
            self.__class__.__name__,
            pprint.pformat(self.__dict__))

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__dict__)


class TimetableCSVImporter(object):
    """A timetable CSV parser and importer.

    You will most likely want to use the importFromCSV(csvdata) method.

    This class does not use exceptions for handling errors excessively
    because of the nature of error-checking: we want to gather many errors
    in one sweep and present them to the user at once.
    """

    app = None
    schoolyear = None
    persons = None
    errors = None
    charset = None

    terms = None

    def __init__(self, schoolyear, charset=None):
        self.app = ISchoolToolApplication(None)
        self.schoolyear = schoolyear
        self.persons = self.app['persons']
        self.errors = TimetableImportErrorCollection()
        self.charset = charset

    def importFromCSV(self, sections_csv):
        """Import sections from CSV data.

        At the top of the file there should be a header row:

        term
        -or-
        first term, last term

        Then an empty line should follow, and the remaining CSV data should
        consist of chunks like this:

        course_id, instructor_id
        timetable_id
        day_id, period_id
        day_id, period_id
        timetable_id
        day_id, period_id
        ...
        ***
        student_id
        student_id
        ...

        """
        if '\n' not in sections_csv:
            self.errors.generic.append(_("No data provided"))
            return False

        rows = self.parseCSVRows(sections_csv.splitlines())

        if rows[1]:
            self.errors.generic.append(_("Row 2 is not empty"))
            return False

        self.importHeader(rows[0])
        if self.errors.anyErrors():
            return False

        self.importChunks(rows[2:], dry_run=True)
        if self.errors.anyErrors():
            return False

        self.importChunks(rows[2:], dry_run=False)
        if self.errors.anyErrors():
            return False
        return True

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

    def listTerms(self):
        first, last = self.terms
        result = [first]
        next = getNextTerm(first)
        while (next is not None and
               not sameProxiedObjects(result[-1], next)):
            result.append(next)
            next = getNextTerm(next)
        return result

    def importChunk(self, rows, line, dry_run=True):
        """Import a chunk of data that describes a section.

        You should run this method with dry_run=True before trying the
        real thing, or you might get in trouble.
        """
        terms = self.listTerms()
        row = rows[0]
        if len(row) not in (2, 2 + len(terms)):
            err_msg = _('Wrong section header on line ${line_no} (it should contain a'
                        ' course id, an instructor id and optional SchoolTool '
                        'section IDs for each of the terms)',
                        mapping={'line_no': line})
            return

        section_ids = None
        if len(row) == 2:
            course_id, instructor_id = row[:2]
        else:
            course_id = row[0]
            instructor_id = row[1]
            section_ids = row[2:]

        course = ICourseContainer(self.schoolyear).get(course_id, None)
        if course is None:
            self.errors.courses.append(course_id)

        instructor = self.persons.get(instructor_id, None)
        if instructor is None:
            self.errors.persons.append(instructor_id)

        line_ofs = 1
        finished = False

        timetables = ITimetableContainer(self.schoolyear)
        timetable = None
        periods = {}

        for row in rows[1:]:
            line_ofs += 1
            if row == ['***']:
                finished = True
                break

            if len(row) == 1:
                tt = timetables.get(row[0])
                if tt is None:
                    err_msg = _("Malformed line ${line_no}"
                                " (it should contain either a timetable id or"
                                " day id and a period id)",
                                mapping={'line_no': line + line_ofs - 1})
                    self.errors.generic.append(err_msg)
                    continue
                timetable = tt
                continue
            elif len(row) == 2:
                day_id, period_id = row
            else:
                err_msg = _("Malformed line ${line_no}"
                            " (it should contain either a timetable id or"
                            " day id and a period id)",
                            mapping={'line_no': line + line_ofs - 1})
                self.errors.generic.append(err_msg)
                continue

            if timetable is None:
                err_msg = _("Timetable id must be specified before"
                            " day id and a period id"
                            " at at line ${line_no}",
                            mapping={'line_no': line + line_ofs - 1})
                continue

            # check day_id
            ttday = None
            for day in timetable.periods.templates.values():
                if day.title == day_id:
                    ttday = day
                    break

            if ttday is None:
                errkey = (timetable.__name__, day_id)
                if errkey not in self.errors.day_ids:
                    self.errors.day_ids.append(errkey)
                continue

            ttperiod = None
            for period in ttday.values():
                if period.title == period_id:
                    ttperiod = period
                    break

            # check period_id
            if ttperiod is None:
                errkey = (timetable.__name__, day_id, period_id)
                if period_id not in self.errors.periods:
                    self.errors.periods.append(errkey)
                    continue

            if timetable.__name__ not in periods:
                periods[timetable.__name__] = []
            periods[timetable.__name__].append(period)

        if not finished:
            err_msg = _("Incomplete section description on line ${line}",
                        mapping = {'line': line})
            self.errors.generic.append(err_msg)
            return
        if len(rows) == line_ofs:
            err_msg = _("No students in section (line ${line})",
                        mapping = {'line': line + line_ofs})
            self.errors.generic.append(err_msg)
            return


        sections = []
        for n, term in enumerate(terms):
            section_container = ISectionContainer(term)
            section_id = None
            if section_ids is not None:
                section_id = section_ids[n]
            if (section_id is not None and
                section_id in section_container):
                section = section_container[section_id]
                self.updateSection(
                    section, term, course, instructor, periods,
                    dry_run=dry_run)
            else:
                section = self.createSection(
                    term, course, instructor, periods,
                    section_id=section_id,
                    dry_run=dry_run)
            self.importPersons(rows[line_ofs:], section, dry_run=dry_run)
            if section is not None:
                sections.append(section)
        if not self.errors.anyErrors():
            for n, section in enumerate(sections[:-1]):
                section.next = sections[n+1]

    def createSection(self, term, course, instructor, periods,
                      section_id=None, dry_run=True):
        """Create a section.

        `periods` is a list of tuples (day_id, period_id).

        A title is generated from the titles of `course` and `instructor`.
        If an existing section with the same title is found, it is used instead
        of creating a new one.

        The created section is returned, or None if dry_run is True.
        """
        if dry_run:
            return None

        sections = ISectionContainer(term)

        section = Section()
        chooser = INameChooser(sections)
        auto_name = chooser.chooseName('', section)
        section.title = u"%s (%s)" % (course.title, auto_name)
        if section_id is None:
            section_id = auto_name
        sections[section_id] = section

        # Establish links to course and to teacher
        if course not in section.courses:
            section.courses.add(course)
        if instructor not in section.instructors:
            section.instructors.add(instructor)

        timetable_container = ITimetableContainer(self.schoolyear)
        timetables = [timetable_container[ttid]
                      for ttid in sorted(periods)]
        schedules = IScheduleContainer(section)
        for timetable in timetables:
            selected = periods[timetable.__name__]
            schedule = SelectedPeriodsSchedule(
                timetable, term.first, term.last,
                title=timetable.title, timezone=timetable.timezone)
            for period in selected:
                schedule.addPeriod(period)
            schedules[timetable.__name__] = schedule

        return section

    def updateSection(self, section, term, course, instructor, periods,
                      dry_run=True):
        """Create a section.

        `periods` is a list of tuples (day_id, period_id).

        A title is generated from the titles of `course` and `instructor`.
        If an existing section with the same title is found, it is used instead
        of creating a new one.

        The created section is returned, or None if dry_run is True.
        """
        if dry_run:
            return None

        # Establish links to course and to teacher
        for c in list(section.courses):
            if c is not course:
                section.remove(c)
        if course not in section.courses:
            section.courses.add(course)
        for i in list(section.instructors):
            if i is not instructor:
                section.instructor.remove(i)
        if instructor not in section.instructors:
            section.instructors.add(instructor)

        timetable_container = ITimetableContainer(self.schoolyear)
        timetables = [timetable_container[ttid]
                      for ttid in sorted(periods)]
        schedules = IScheduleContainer(section)
        for timetable in timetables:
            selected = periods[timetable.__name__]
            schedule = None
            for s in schedules.values():
                if sameProxiedObjects(s.timetable, timetable):
                    schedule = s
                    break
            if schedule is None:
                schedule = SelectedPeriodsSchedule(
                    timetable, term.first, term.last,
                    title=timetable.title, timezone=timetable.timezone)
                for period in selected:
                    schedule.addPeriod(period)
                schedules[timetable.__name__] = schedule
            else:
                for period in schedule.periods:
                    if period not in selected:
                        schedule.removePeriod(period)
                for period in selected:
                    schedule.addPeriod(period)

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

    def findTerm(self, title):
        terms = ITermContainer(self.schoolyear)
        for term in terms.values():
            if term.title == title:
                return term
        return None

    def importHeader(self, row):
        """Read the header row of the CSV file.

        Sets self.terms
        """
        if len(row) < 1 or len(row) > 2:
            self.errors.generic.append(
                    _("The first row of the CSV file must contain"
                      " the term or first and last terms for sections."))
            return

        first = self.findTerm(row[0])

        if first is None:
            error_msg = _("The term ${term} does not exist.",
                          mapping={'term': row[0]})
            self.errors.generic.append(error_msg)
            return

        if len(row) == 1:
            last = first
        else:
            last = self.findTerm(row[1])
            if last is None:
                error_msg = _("The term ${term} does not exist.",
                              mapping={'term': row[1]})
                self.errors.generic.append(error_msg)
                return

        if first.first >= last.last:
                error_msg = _("First term ${first} starts after"
                              " last term ${last}.",
                              mapping={'first': row[0],
                                       'last': row[1]})
                self.errors.generic.append(error_msg)
                return

        self.terms = (first, last)


    def parseCSVRows(self, rows):
        """Parse rows (a list of strings) in CSV format.

        Returns a list of rows as lists.  Trailing empty cells are discarded.

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
            error_msg = _("Error in timetable CSV data, line ${line_no}",
                          mapping={'line_no': line})
            self.errors.generic.append(error_msg)
            return
        except UnicodeError:
            error_msg = _("Conversion to unicode failed in line ${line_no}",
                          mapping={'line_no': line})
            self.errors.generic.append(error_msg)
            return


class TimetableCSVImportView(BaseCSVImportView):
    """Timetable CSV import view."""

    __used_for__ = ISectionContainer

    importer_class = TimetableCSVImporter

    def _presentErrors(self, err):
        if err.generic:
            self.errors.extend(err.generic)

        for key, msg in [
            ('day_ids', _("Day ids not defined in selected schema: ${args}.")),
            ('periods', _("Periods not defined in selected days: ${args}.")),
            ('persons', _("Persons not found: ${args}.")),
            ('courses', _("Courses not found: ${args}.")),
            ('sections', _("Sections not found: ${args}.")),
            ('records', _("Invalid records: ${args}."))]:
            v = getattr(err, key)
            if v:
                values = ', '.join([unicode(st) for st in v])
                msg = _(msg, mapping={'args': values})
                self.errors.append(msg)


class FlourishTimetableCSVImportView(FlourishBaseCSVImportView,
                                     TimetableCSVImportView,
                                     ActiveSchoolYearContentMixin):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    def nextURL(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='sections')

    @property
    def title(self):
        return _('Sections for ${schoolyear}',
                 mapping={'schoolyear': self.schoolyear.title})


class ImportSectionsLinkViewlet(flourish.page.LinkViewlet,
                                ActiveSchoolYearContentMixin):

    @property
    def url(self):
        link = self.link
        if not link:
            return None
        return "%s/%s" % (absoluteURL(self.schoolyear, self.request),
                          self.link)
