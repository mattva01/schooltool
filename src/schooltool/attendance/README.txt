===================
Attendance Tracking
===================


Definitions
-----------

"Absence" is when a student fails to show up during a period.

"Day absence" is when a student fails to show up during the homeroom period for
a particular day.

"Section absence" is when a student fails to show up during a regular period.

"Tardy" is when a student shows up late.

"Presence" is when a student shows up on time.

"Attendance incident" is either an absence or a tardy.

Attendance incidents can be either explained or unexplained.  We'll use the
terms "explained" and "unexplained" instead of excused and unexcused, because
the workflow may be resolved by an explanation that is not a valid excuse.


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

TODO: write some science fiction code here
