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

- Summary of all attendance incidents for a student for a single term.


API
---

The following code is *science-fiction*, that is, it doesn't work yet, but instead
represents our thoughts about the API should look like

    >>> from schooltool.attendance.interface import IAttendances

    >>> student = app['persons']['student00937']
    >>> attendances = IAttendances(student)

    >>> ttcal = student.makeTimetableCalendar()
    >>> first = datetime.datetime(Y, M, D, tzinfo=UTC)
    >>> last = first + datetime.timedelta(days=1)
    >>> all_sections = list(ttcal.expand(first, last))
    >>> section_event = all_sections[0]

Try one:

    >>> attendances.get(section_event) == attendances.UNKNOWN
    True

    >>> attendances.record(section_event, attendances.ABSENT)
    >>> attendances.get(section_event) == attendances.ABSENT
    True

    >>> attendances.record(section_event, attendances.TARDY)
    >>> attendances.get(section_event) == attendances.TARDY
    True

    >>> attendances.record(section_event, attendances.PRESENT)
    >>> attendances.get(section_event) == attendances.PRESENT
    True

    >>> attendances.makeCalendar(first, last)
    <...ImmutableCalendar object ...>

Logging

    >>> logging.getLogger('schooltool.attendance').addHandler(...)
    >>> attendances.record(section_event, attendances.ABSENT)
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo was absent from Math

Vague thoughts: we need a method to extract the range of the current school day
(taking timezone into account)

On second thought attendance should be an object, not an enum

    >>> attendances.get(section_event)
    Attendance(UNKNOWN)

    >>> attendances.record(section_event, attendances.ABSENT)
    >>> attendances.get(section_event)
    Attendance(ABSENT)

    >>> attendances.record(section_event, attendances.TARDY)
    >>> attendances.get(section_event)
    Attendance(TARDY)

    >>> attendances.get(section_event).explained
    False
    >>> attendances.get(section_event).explaination is None
    True

    >>> attendances.get(section_event).explain(u"Sick")
    >>> attendances.get(section_event).explained
    True
    >>> attendances.get(section_event).explaination
    u"Sick"
    >>> attendances.get(section_event).explaination_date
    datetime.datetime(...)

Day attendance is recorded the same way, by taking a homeroom_period_event.

    >>> attendances.getUnexplainedAttendances()
    [...]

    >>> attendances.getAttendancesForTerm(term)


Sparkline attendance graph
--------------------------

The real-time attendance form will have whisker "sparkline" (see
http://sparkline.org/) graphs showing attendance for the last 10 days for each
student.

- Successful attendance during days when the section has met are designated by
  a full length positive black line. 

    >>> homeroom_event = ???
    >>> the_section = app['sections']['some_section']
    >>> events = the_section.getMeetingEventsForDay(a_date)
    >>> if events and attendance.get(events[0]).state == PRESENT:
    ...    length = 'full'
    ...    color = 'black'

- Attendance on days the section does not meet are indicated by a half-length
  black line.

    >>> if not events and attendance.get(homeroom_event).state == PRESENT:
    ...     length = 'half'
    ...     color = 'black'

- Non-attendance on days the section does not meet is indicated by a
  half-length descending grey (excused) or yellow (unexcused) line.

    >>> if not events and attendance.get(homeroom_event).state != PRESENT:
    ...     length = 'half'
    ...     if attendance.get(homeroom_event).explained:
    ...         color = 'grey'
    ...     else:
    ...         color = 'yellow'

- Non-attendance on days when the section meets is indicated by a full length
  black (excused) or yellow (unexcused) line.

    >>> if events and attendance.get(events[0]).state != PRESENT:
    ...     length = 'full'
    ...     if attendance.get(events[0]).explained:
    ...         color = 'grey'
    ...     else:
    ...         color = 'yellow'

- Non-attendance in days when the section met and the student was in school are
  designated by full length red whiskers, until they are excused (black).

    >>> if events and attendance.get(events[0]).state != PRESENT:
    ...     length = 'full'
    ...     if attendance.get(homeroom_event).state == PRESENT:
    ...         if attendance.get(events[0]).explained:
    ...             color = 'black'
    ...         else:
    ...             color = 'red'

This is complicated.  Let's show a table:

   +----------------+-------------------------+---------------------+--------------+
   | section meets? | present during section? | present during day? | bar          |
   +----------------+-------------------------+---------------------+--------------+
   | yes            | yes                     | (does not matter)   | full black   |
   | yes            | no (explained)          | (does not matter)   | full black   |
   | yes            | no (unexplained)        | yes                 | full red     |
   | yes            | no (unexplained)        | no                  | full yelllow |
   | no             | (not available)         | yes                 | half black   |
   | no             | (not available)         | no (explained)      | half grey    |
   | no             | (not available)         | no (unexplained)    | half yellow  |
   +----------------+-------------------------+---------------------+--------------+

The table above does not indicate what to show in the following cases:

   +----------------+-------------------------+---------------------+--------------+
   | section meets? | present during section? | present during day? | bar          |
   +----------------+-------------------------+---------------------+--------------+
   | yes            | unknown                 | (does it matter?)   |              |
   | no             | (not available)         | unknown             |              |
   +----------------+-------------------------+---------------------+--------------+

