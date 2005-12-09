===================
Attendance Tracking
===================


Definitions
-----------

An "absence" is when a student fails to show up during a period.

A "day absence" is when a student fails to show up during the homeroom period
for a particular day.

A "section absence" is when a student fails to show up for the scheduled
meeting of a section.

A "tardy" is when a student shows up late.

A "presence" is when a student shows up on time.

An "attendance incident" is either an absence or a tardy.

Attendance incidents can be either "explained" or "unexplained".  We'll use the
terms explained and unexplained instead of excused and unexcused, because the
workflow may be resolved by an explanation that is not a valid excuse.


Basic workflow
--------------

- If a student is not in attendance, create an "unexplained" absence at the
  beginning of the section/day.

- If the student arrives late, the absence becomes an unexplained tardy.

- The absence or tardy can be advanced to "explained" by actions by clerks,
  school administrators or (in some cases) teachers, thus ending the workflow.

The workflow of attendance incidents (absences, tardies) will be modeled by
WFMC workflows, so they will be clearly defined and (relatively) easy to modify
to fit specific business processes.


Use cases
---------

- Realtime class attendance: a web form to allow one to take attendance during
  class.  This form lets teachers create section absences, and convert absences
  to tardies.  Presences are also recorded.

- Homeroom class attendance: a web form to allow one to take attendance during
  the homeroom period.  This form lets teachers create day absences.  Presences
  are also recorded.

- Logging: attendance-related transaction must be logged to an 'attendance.log'
  file in a simple text log format.

- Student attendance in the calendar view: lets users see absences/tardies as
  read-only events in a student's calendar.  Also indicated whether the
  absences/tardies are explained or not.

- Sparkline plot for day/section absence during the last 10 days.

- List of unexplained attendance incidents for a student for both days and periods.

- List of all attendance incidents for a student for a single term (i.e. date range).

- Modification of attendance workflow status, whatever that means.


API
---

The following code is *science-fiction*, that is, it doesn't work yet, but instead
represents our thoughts about the API should look like

Realtime class attendance
~~~~~~~~~~~~~~~~~~~~~~~~~

The user can create section absences for each student in a section.  Presences
are also recorded.

    >>> from schooltool.attendance.interface import ISectionAttendance

    >>> section = app['sections']['sec00213']
    >>> for student in section.students:
    ...     is_present = student.__name__ not in request['absent']
    ...     ISectionAttendance(student).record(section, datetime, is_present)

The form lets teachers convert absences to tardies

    >>> for student in section.students:
    ...     is_present = student.__name__ not in request['absent']
    ...     attendance_record = ISectionAttendance(student).get(section, datetime)
    ...     if is_present and attendance_record.isAbsent():
    ...         arrived = parse_time(request['arrived.%s' % student.__name__])
    ...         attendance_record.makeTardy(arrived=arrived)

The form displays the current attendance status as well.

    >>> for student in section.students:
    ...     attendance_record = ISectionAttendance(student).get(section, datetime)
    ...     absent_checked[student.__name__] = attendance_record.isAbsent()

The following API emerges::

    class ISectionAttendance(Interface):
        """A set of all student's section attendance records."""

        def get(section, datetime):
            """Return the attendance record for a specific section meeting.

            Always succeeds, but the returned attendance record may be
            "unknown".
            """

        def record(section, datetime, present):
            """Record the student's absence or presence.

            You can only record the absence or presence once for a given
            (section, datetime) pair.
            """

    class IAttendanceRecord(Interface):
        """A single attendance record for a day/section."""

        status = Attribute("""Attendance status (UNKNOWN, PRESENT, ABSENT, TARDY.""")

        def isUnknown(): """True if status == UNKNOWN."""
        def isPresent(): """True if status == PRESENT."""
        def isAbsent():  """True if status == ABSENT."""
        def isTardy():   """True if status == TARDY."""

        def isExplained():
            """Is the absence/tardy explained?

            Meaningless (i.e. raises some exception) when status ==
            UNKNOWN or PRESENT.
            """

        def makeTardy(arrived):
            """Convert an absence to a tardy.

            `arrived` is a datetime.time.

            Meaningless (i.e. raises some exception) when status != ABSENT.
            """


Colored backgrounds indicating attendance status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The realtime attendance form has colored backgrounds that indicate the following:

* student in school today (grey)
* student absent today (yellow)
* student absent with excuse (greenish)
* student in school earlier but subsequently gone with no excuse (red)

Let's specify this more precisely:

* grey -- there are no recorded absences/tardies for today (neither day, nor
  section absences)
* yellow -- there is at least one unexcused absence/tardy for today, and
  there are no recorded presences for today
* greenish -- there is at least one excused absence/tardy for today, there are
  no unexcused absences/tardies nor recorded presences for today
* red -- there are both recorded presences and recorded unexcused absences for
  today
* There is no background if a student's attendance hasn't been recorded yet.

Implementation:

    >>> def getColorForStudent(student):
    ...     records = [IDayAttendance(student).get(date)]
    ...     records.extend(ISectionAttendance(student).getAllForDay(date))
    ...     records = [ar for ar in records if not ar.isUnknown()]
    ...     was_present = False
    ...     was_absent = False
    ...     was_absent_without_excuse = False
    ...     for ar in records:
    ...         if ar.isPresent():
    ...             was_present = True
    ...         else:
    ...             was_absent = True
    ...             if not ar.isExcused():
    ...                 was_absent_without_excuse = True
    ...     if was_present and was_absent_without_excuse:
    ...         return 'red'
    ...     elif was_absent_without_excuse:
    ...         return 'yellow'
    ...     elif was_absent:
    ...         return 'greenish'
    ...     elif was_present:
    ...         return 'grey'
    ...     else:
    ...         return 'transparent'

Thus our ISectionAttendance interface gains a new method::

    class ISectionAttendance(Interface):
        ...

        def getAllForDay(date):
            """Return all recorded attendance records for a specific day."""


Sparkline attendance graph
--------------------------

The real-time attendance form will have whisker sparkline__ graphs showing
attendance for the last 10 schooldays for each student.

__ http://sparkline.org/

- Successful attendance during days when the section has met are designated by
  a full length positive black line.

- Attendance on days the section does not meet are indicated by a half-length
  black line.

- Non-attendance on days the section does not meet is indicated by a
  half-length descending grey (excused) or yellow (unexcused) line.

- Non-attendance on days when the section meets is indicated by a full length
  black (excused) or yellow (unexcused) line.

- Non-attendance in days when the section met and the student was in school are
  designated by full length red whiskers, until they are excused (black).

This is complicated.  Let's show a table:

   +---------+------------------+--------------------+------+---------+-----+
   | section |                  |                    |      |         |     |
   | meets   | present during   | present during day | size | colour  | +/- |
   | on this | section?         | (homeroom period)? |      |         |     |
   | day?    |                  |                    |      |         |     |
   +=========+==================+====================+======+=========+=====+
   | yes     | unknown          | (does not matter)  | dot  | black   | n/a |
   +---------+------------------+--------------------+------+---------+-----+
   | yes     | yes              | (does not matter)  | full | black   | `+` |
   +---------+------------------+--------------------+------+---------+-----+
   | yes     | no (explained)   | (does not matter)  | full | black   | `-` |
   +---------+------------------+--------------------+------+---------+-----+
   | yes     | no (unexplained) | yes                | full | red     | `-` |
   +---------+------------------+--------------------+------+---------+-----+
   | yes     | no (unexplained) | no                 | full | yelllow | `-` |
   +---------+------------------+--------------------+------+---------+-----+
   | no      | (not available)  | unknown            | dot  | black   | n/a |
   +---------+------------------+--------------------+------+---------+-----+
   | no      | (not available)  | yes                | half | black   | `+` |
   +---------+------------------+--------------------+------+---------+-----+
   | no      | (not available)  | no (explained)     | half | black   | `-` |
   +---------+------------------+--------------------+------+---------+-----+
   | no      | (not available)  | no (unexplained)   | half | yellow  | `-` |
   +---------+------------------+--------------------+------+---------+-----+

I *assume* tardy is the treated as absent, i.e. you look at whether the
incident is explained or not.

If the section meets more than once on a given day, take the "worst" of the
outcomes.

If this table does not match the list of rules above, consider the table
to be authoritative.

    >>> section_calendar = ITimetables(section).makeCalendar()
    >>> def worst_section_presence(date):
    ...     """Return the "worst" section presence on a given date."""
    ...     records = [ar for ar in ISectionAttendance(student).getAllForDay(date)
    ...                if ar.section == section]
    ...     for ar in records:
    ...         if (ar.isAbsent() or ar.isTardy()) and not ar.isExplained():
    ...             return ar
    ...     for ar in records:
    ...         if ar.isAbsent() or ar.isTardy():
    ...             return ar
    ...     for ar in records:
    ...         if ar.isPresent():
    ...             return ar
    ...     return UnknownAttendanceRecord()

It appears that an attendance record needs to know about its section.

    >>> def data_point(date):
    ...     day_start = datetime.combine(date, time(0)) # XXX timezone
    ...     day_end = day_start + datetime.timedelta(1)
    ...     section_meets_on_this_day = bool(section_calendar.expand(day_start, day_end))
    ...     section_presence = worst_section_presence(section, date)
    ...     day_presence = IDayAttendance(student).get(date)
    ...     if section_meets_on_this_day:
    ...         if section_presence.isUnknown():
    ...             return 'black dot'
    ...         elif section_presence.isPresent():
    ...             return 'black positive full line'
    ...         elif section_presence.isExplained():
    ...             return 'black negative full line'
    ...         elif day_presence.isPresent():
    ...             return 'red negative full line'
    ...         else:
    ...             return 'yellow negative full line'
    ...     else:
    ...         if day_presence.isUnknown():
    ...             return 'black dot'
    ...         elif day_presence.isPresent():
    ...             return 'black positive half line'
    ...         elif day_presence.isExplained():
    ...             return 'black negative half line'
    ...         else:
    ...             return 'yellow negative half line'

**XXX** We also need some way to get the last 10 schooldays

**XXX** So should ISectionAttendance.record and get take a date or a datetime?

  **Ignas**: it depends. Do we want to identify the exact time of an
  attendance event or not.  If we only care that you missed Petersons
  class on thursday - date, if we care about intricate cases like:

    Peterson has two math lessons with 6 A on the same day, John is
    present in the first one, yet has a headache and is excused to go
    home, so he gets an "excused abscence" for the second lesson.

  As our system allows scheduling same section more than once for a
  day we should have a way to uniquely identify those two records
  which would mean storing a datetime or (IMHO better: date,
  period_id, section_id) because we would use the datetime to identify
  the period anyway.

| **XXX** We stumble on timezones once again -- at what time does a school day start?
|         And by "at what time", I mean "at 00:00 in which timezone"?

Homeroom class attendance
~~~~~~~~~~~~~~~~~~~~~~~~~

Homeroom class attendance form deals with day absences.

    >>> section = app['sections']['sec00213']
    >>> for student in section.students:
    ...     is_present = student.__name__ not in request['absent']
    ...     IDayAttendance(student).record(date, is_present)

API::

    class IDayAttendance(Interface):
        """A set of all student's day attendance records."""

        def get(date):
            """Return the attendance record for a specific day.

            Always succeeds, but the returned attendance record may be
            "unknown".
            """

        def record(date):
            """Record the student's absence or presence.

            You can only record the absence or presence once for a given date.
            """

Logging
~~~~~~~

All attendance related events appear in a log file

    >>> logging.getLogger('schooltool.attendance').addHandler(...)
    >>> IDayAttendance(student).record(section, datetime, False)
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo was absent from Math
    >>> IDayAttendance(student).get(section, datetime).makeTardy(time)
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo was late for Math

    >>> del logging.getLogger('schooltool.attendance').handlers[:]


Attendance events in a student's calendar
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The calendar view will have to include two more calendars in its getCalendars() method:

    >>> daily_absences = IDayAttendance(student).makeCalendar(start, end)
    >>> section_absences = ISectionAttendance(student).makeCalendar(start, end)

Daily absences will contain all-day events for all absences and tardies.
Section absences will contain regular events for all absences and tardies.

| **XXX** So ISectionAttendance.record should record both dtstart and duration?
| Unless we are satisfied with zero-length events at the beginning of a section.


List of pending attendance incidents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"Attendance" should appear as a action while viewing a student.  The
attendance view should show a list of pending unexcused attendance
incidents, for both days and periods.

    >>> for ar in IDayAttendance(student):
    ...     if not ar.isPresent() and not ar.isExplained():
    ...         print "Explain why you weren't present on %s" % ar.date
    >>> for ar in ISectionAttendance(student):
    ...     if not ar.isPresent() and not ar.isExplained():
    ...         print "Explain why you missed %s on %s" % (ar.section.title, ar.date)

New API, for both IDayAttendance and ISectionAttendance::

        def __iter__():
            """Return all recorded attendance records.

            (This means that none of the returned records will be in
            the UNKNOWN state.)
            """

We also need two new interfaces::

    class IDayAttendance(IAttendanceRecord):
        """A single attendance record for a day."""

        date = Attribute("""The date of this record.""")


    class ISectionAttendance(IAttendanceRecord):
        """A single attendance record for a section."""

        section = Attribute("""The section object.""")

        date = Attribute("""The date of this record.""")

**XXX** so, what do we store here?

- date (breaks if a section meets twice on the same day)
- datetime (then makeCalendar is unclear)
- datetime + duration
- date + (timetable/period id)   <-- this is probably the right one


Summary of attendance per term
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The attendance view should show [...] a summary of absences and
tardies by term.  The user can click on a term for a list of all
absences and tardies per term.

The summary is just the number of absences and tardies.  The list shows the
time, date and class for each attendance incident.

We need to count the number of absences/tardies in a given time period

    >>> day_attendances = IDayAttendance(student).filter(term.first, term.last)
    >>> section_attendances = ISectionAttendance(student).filter(term.first, term.last)
    >>> attendances = day_attendances + section_attendances
    >>> n_absences = len(ar for ar in attendances if ar.isAbsent())
    >>> n_tardies = len(ar for ar in attendances if ar.isTardy())

We also need to know for each attendance incident the date/time and section.

Workflow status modification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the haziest part of the whole spec.  All we know is "If the
user has the proper access, he or she can modify the workflow status
of unresolved incidents from the attendance view."

Stab in the dark:

* we want to attach explainations to absence records

    >>> ar.addExplanation("The dog ate my homework")
    >>> ar.addExplanation("I vas very sick from drinking bloo^H^H^H^Hjuice")
    >>> print ar.explanations
    ["The dog ...", "I vas very sick..."]

* we want to resolve pending absences as excused

    >>> ar.excuse()

* we want to reject an explanation

     >>> ar.reject()

