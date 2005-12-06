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

        def makeTardy(arrived):
            """Convert an absence to a tardy.

            `arrived` is a datetime.time.
            """


Colored backgrounds indicating attendance status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The realtime attendance form has colored backgrounds that indicate the following:

* student in school today (grey)
* student absent today (yellow)
* student absent with excuse (greenish)
* student in school earlier but subsequently gone with no excuse (red)

There is no background if a student's attendance hasn't been recorded yet.

    >>> def getColorForStudent(student):
    ...     ar = IDayAttendance(student).get(date)
    ...     if ar.isUnknown():
    ...         return 'transparent'
    ...     elif ar.isAbsent():
    ...         if ar.isExcused():
    ...             return 'greenish'
    ...         else:
    ...             return 'grey'
    ...     else: # present or tardy
    ...         for ar in ISectionAttendance(student).getAllForDay(date):
    ...             if ar.isAbsent() and not ar.isExcused():
    ...                 return 'red'
    ...         return 'grey'

Thus our ISectionAttendance interface gains a new method::

    class ISectionAttendance(Interface):
        ...

        def getAllForDay(date):
            """Return all recorded attendance records for a specific day."""

Note that there is no way to determine sections/datetimes from IAttendanceRecord
objects returned by getAllForDay -- YAGNI.


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

Old science fiction
~~~~~~~~~~~~~~~~~~~

XXX delete this

    >>> attendances.makeCalendar(first, last)
    <...ImmutableCalendar object ...>

Logging

    >>> logging.getLogger('schooltool.attendance').addHandler(...)
    >>> attendances.record(section_event, attendances.ABSENT)
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo was absent from Math

Vague thoughts: we need a method to extract the range of the current school day
(taking timezone into account)

...

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


    >>> attendances.getUnexplainedAttendances()
    [...]

    >>> attendances.getAttendancesForTerm(term)


Sparkline attendance graph
--------------------------

The real-time attendance form will have whisker sparkline__ graphs showing
attendance for the last 10 schooldays for each student.

__ http://sparkline.org/

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
    ...         color = 'black'
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

   +---------+------------------+--------------------+------+---------+-----+
   | section |                  |                    |      |         |     |
   | meets   | present during   | present during day | size | colour  | +/- |  
   | on this | section?         | (homeroom period)? |      |         |     |
   | day?    |                  |                    |      |         |     |
   +---------+------------------+--------------------+------+---------+-----+
   | yes     | unknown          | (does not matter)  | dot  | black   | n/a |
   | yes     | yes              | (does not matter)  | full | black   | +   |
   | yes     | no (explained)   | (does not matter)  | full | black   | -   |
   | yes     | no (unexplained) | yes                | full | red     | -   |
   | yes     | no (unexplained) | no                 | full | yelllow | -   |
   | no      | (not available)  | unknown            | dot  | black   | n/a |
   | no      | (not available)  | yes                | half | black   | +   |
   | no      | (not available)  | no (explained)     | half | black   | -   |
   | no      | (not available)  | no (unexplained)   | half | yellow  | -   |
   +---------+------------------+--------------------+------+---------+-----+

If this table does not match the list of rules above, consider the table
to be authoritative.


Another possible version of API
-------------------------------

The following code is another *science-fiction*, more WfMC'ish and less
dependent of workflow structure.

    >>> from schooltool.attendance.interface import IAttendanceItem

    >>> student = app['persons']['student00937']

    >>> ttcal = student.makeTimetableCalendar()
    >>> first = datetime.datetime(Y, M, D, tzinfo=UTC)
    >>> last = first + datetime.timedelta(days=1)
    >>> all_sections = list(ttcal.expand(first, last))
    >>> section_event = all_sections[0]

Set up logging:

    >>> logging.getLogger('schooltool.attendance').addHandler(...)

Try one:

    >>> attendance_item = IAttendanceItem(student, section_event)

    >>> activitie = attendance_item.getCurrentActivities()
    >>> activities
    [AttendanceActivity(Waiting for student)]

Try one of the activities:

    >>> activity = activities[0]

Make sure it's our job to process this activity:

    >>> my_role = Role("teacher") # mapping roles to performers...?
    >>> activity.performer.conforms(my_role)
    True

    >>> pprint_schema(activity.getSchema())
    student_seen = Bool(
        """Set to True if student was present when event started""",
        default=True)

    >>> activity.resolve(student_seen = False)

Application logic changes "status" to "Explaining absence":

    >>> activities = attendance_item.getCurrentActivities()
    >>> activities
    [AttendanceActivity(Explaining absence)]

Let's make an explanation (student should, but who cares?):

    >>> activity = activities[0]
    >>> pprint_schema(activity.getSchema())
    explanation = Text(
        """Why student is absent?""",
        default='')

    >>> activity.resolve(explanation = """I hate math""")

We can have more than one activity:

    >>> activities = attendance_item.getCurrentActivities()
    >>> activities
    [AttendanceActivity(Resolving explanation),
    AttendanceActivity(Overload explanation)]

What is that second one?

    >>> some_role = Role('Student's Parent')
    >>> activities[1].performer.conforms(some_role)
    True
    >>> activities[1].performer.conforms(my_role)
    False

Ok, it's not for us, so we do our job:

    >>> my_activity = activities[0]
    >>> my_activity.performer.conforms(my_role)
    True

    >>> pprint_schema(my_activity.getSchema())
    explanation = Text(
        """Explanation by student""",
        readonly = True)
    resolution = Choice(
        """Chose his destiny""",
        choices = ['forgive', 'make suffer!'],
        default = 'make suffer!')
    arguments = Text(
        """Support your decision with arguments""")

We have some data to consider (explanation made by student). We can use
different (and probably better) way to resolve activity.

    >>> content = my_activity.getData()
    >>> content.resolution = 'forgive'
    >>> content.arguments = 'I hate math myself'
    >>> my_activity.resolveWithData(content)

Is our student lucky guy?

    >>> attendance_item.getCurrentActivities()
    [AttendanceActivity(ExcusedAbsence)]

We want to show this as event:

    >>> attendance_item.getEvent()
    <...Event object ...>

If someone wants to look at our log:

    >>> print logging.getLogger('schooltool.attendance').dump()
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo was absent from Math
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo explained his absence at Math
    YYYY-MM-DD HH:MM:SS +ZZZZ: student Foo was forgiven absence at Math


