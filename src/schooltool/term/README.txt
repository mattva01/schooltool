=====================================
Terms and SchoolTool Timeflow Control
=====================================

Terms are the primary objects to control timeflow in SchoolTool. In SchoolTool
a term is defined as a time interval to organize academic school
administration. Typical examples include the academic year, semester,
trimester, and grading period, but not a break, school day or period.

  >>> from schooltool.term import interfaces, term

Term Types
----------

Term types are interfaces that describe the scope of the term. Those
interfaces provide a meta-interface called ``ITermType``. An example of a
term type is the academic year:

  >>> interfaces.ITermType.providedBy(interfaces.IAcademicYear)
  True

The academic year is SchoolTool's largest term type. Each school *must*
organize its program on an annual cycle.

Years are typically divided into two semesters or three trimesters.

  >>> interfaces.ITermType.providedBy(interfaces.ISemester)
  True

  >>> interfaces.ITermType.providedBy(interfaces.ITrimester)
  True

Within all of the term types above, some school systems define shorter grading
periods:

  >>> interfaces.ITermType.providedBy(interfaces.IGradingPeriod)
  True


Terms
-----

The term type interfaces are implemented by corresponding components known as
terms. Terms must define a title, first and last date.

The Academic Year
+++++++++++++++++

Let's have a look at the academic year first:

  >>> import datetime
  >>> year = term.AcademicYear(
  ...     u'2005/2006', datetime.date(2005, 8, 15), datetime.date(2006, 8, 14))

  >>> year
  AcademicYear

  >>> year.title
  u'2005/2006'
  >>> year.first
  datetime.date(2005, 8, 15)
  >>> year.last
  datetime.date(2006, 8, 14)

The academic year implements the ``IAcademicYear`` term type interface:

  >>> interfaces.IAcademicYear.providedBy(year)
  True

The term itself does not provide any other functionality. One extension of a
term is to provide the ``IDateRange`` API:

  >>> dates = interfaces.IDateRange(year)
  >>> datetime.date(2005, 11, 11) in dates
  True
  >>> list(dates)
  [datetime.date(2005, 8, 15), ..., datetime.date(2006, 8, 14)]

The academic year component is also a container. Initially, there are no
items:

  >>> year.keys()
  []

The term containment describes the sub-terms of a term. In the case of the
academic year, it can contain semesters and trimesters.

  >>> fall = term.Semester(
  ...     u'Fall 2005',
  ...     datetime.date(2005, 8, 31), datetime.date(2005, 12, 21))
  >>> year['fall'] = fall

  >>> spring = term.Semester(
  ...     u'Spring 2006',
  ...     datetime.date(2006, 1, 12), datetime.date(2006, 5, 19))
  >>> year['spring'] = spring

Note that the semesters *must* have a date range within the date range of the
academic year. If not, the addition fails:

  >>> year['summer'] = term.Semester(
  ...     u'Summer, 2006',
  ...     datetime.date(2006, 5, 24), datetime.date(2006, 9, 1))
  Traceback (most recent call last):
  ...
  ValueError: Date range outside of term.

Also, only certain term types can be added to the academic year. For example,
it makes no sense to add another academic year to the academic year itself:

  >>> year['2006_2007'] = term.AcademicYear(
  ...     u'2006/2007',
  ...     datetime.date(2006, 5, 24), datetime.date(2005, 5, 25))
  Traceback (most recent call last):
  ...
  ConstraintError:

Semesters and Trimesters
++++++++++++++++++++++++

We already added some semesters to our academic year. But currently there is
no telling (in the model) that the spring semester will come after the fall
semester. This can be done by setting the next attribute of the term:

  >>> fall.next = spring

Note that you can only assign terms of the same term type:

  >>> fall.next = year
  Traceback (most recent call last):
  ...
  ValueError: Next term does not have the right term type.

Also, the first term is marked using a flag:

  >>> fall.isFirst = True

Now, to complicate matters even further, some schools are on a semester *and*
timester schedule. In those cases it will be necessary to create the trimester
terms in parallel to the semesters:

  >>> triFall = term.Trimester(
  ...     u'Fall Trimester 2005',
  ...     datetime.date(2005, 9, 1), datetime.date(2005, 11, 30))
  >>> year['triFall'] = triFall
  >>> triFall.isFirst = True

  >>> triWinter = term.Trimester(
  ...     u'Winter Trimester 2006',
  ...     datetime.date(2005, 12, 1), datetime.date(2006, 2, 28))
  >>> year['triWinter'] = triWinter
  >>> triFall.next = triWinter

  >>> triSpring = term.Trimester(
  ...     u'Spring Trimester 2006',
  ...     datetime.date(2006, 3, 1), datetime.date(2006, 5, 31))
  >>> year['triSpring'] = triSpring
  >>> triWinter.next = triSpring

That's it. We now have parallel schedules for semesters and trimester.

Grading Periods
+++++++++++++++

In some middle schools, for example the US, grading periods are used to give
parents frequently feedback about their childrens performance. In some schools
the grading period is 2 weeks, in others 6 weeks. Let's create grading periods
for the fall semester.

  >>> period1 = term.GradingPeriod(
  ...     u'Grading Period 1',
  ...     datetime.date(2006, 9, 1), datetime.date(2006, 9, 30))
  >>> fall['period1'] = period1
  >>> period1.isFirst = True

  >>> period2 = term.GradingPeriod(
  ...     u'Grading Period 2',
  ...     datetime.date(2006, 10, 1), datetime.date(2006, 10, 31))
  >>> fall['period2'] = period2
  >>> period1.next = period2

  >>> period3 = term.GradingPeriod(
  ...     u'Grading Period 3',
  ...     datetime.date(2006, 11, 1), datetime.date(2006, 11, 30))
  >>> fall['period3'] = period3
  >>> period2.next = period3


Controlling Timeflow
--------------------

From an organizational point of view, the primary task of the term hierarchy
is to control the timeflow of the school and manage all time-driven
maintanance tasks.

  >>> control = interfaces.IEventControl(year)

Using the event control component, one can dispatch an events. Those events
must implement the ``ITermEvent`` interface:

  >>> from schooltool.term import event
  >>> yearSetup = event.SetUpTermEvent(year)

  >>> interfaces.ITermEvent.providedBy(yearSetup)
  True

Before we can send off the event, let's register a subscriber that listens to
all term events:

  >>> def recordTermEvent(event):
  ...     print event

  >>> import zope.component
  >>> zope.component.provideHandler(recordTermEvent, (interfaces.ITermEvent,))

Now we can dispatch the event:

  >>> control.dispatch(yearSetup)
  SetUpTermEvent(<AcademicYear u'2005/2006'>)

Once the event has been dispatched, it can be found in the term event log:

  >>> control.eventLog
  [SetUpTermEvent(<AcademicYear u'2005/2006'>)]

Note that you *cannot* dispatch the same event twice in a term:

  >>> control.dispatch(yearSetup)
  Traceback (most recent call last):
  ...
  ValueError: Events can only be dispatched once.

  >>> control.dispatch(event.SetUpTermEvent(year))
  Traceback (most recent call last):
  ...
  ValueError: Events can only be dispatched once.

  >>> class MySetUpTermEvent(event.SetUpTermEvent):
  ...     pass
  >>> control.dispatch(event.MySetUpTermEvent(year))
  Traceback (most recent call last):
  ...
  ValueError: Events can only be dispatched once.

Oftentimes creating the specific event is trivial. In those cases you simply
need to provide the event interface to dispatch a term event. For this method
to work, you have to setup an adapter from ``ITerm`` to the term event
interface:

  >>> zope.component.provideAdapter(event.BeginTermEvent)

Now we can dispatch the event type:

  >>> control.dispatchType(interfaces.IBeginTermEvent)
  BeginTermEvent(<AcademicYear u'2005/2006'>)

  >>> control.eventLog
  [SetUpTermEvent(<AcademicYear u'2005/2006'>),
   BeginTermEvent(<AcademicYear u'2005/2006'>)]

Furthermore, you can check whether a particular type of event has been
dispatched already:

  >>> control.wasDispatched(yearSetup)
  True

  >>> control.wasTypeDispatched(interfaces.ISetUpTermEvent)
  True
  >>> control.wasTypeDispatched(interfaces.IBeginTermEvent)
  True
  >>> control.wasTypeDispatched(interfaces.IEndTermEvent)
  False


Events cannot be called at arbitrary times. For example, it does not make
sense to start a term before having it setup. Those restrictions are
implemented using subscriptions providing the ``ITermEventCondition``
interface:

  >>> def doNotStartBeforeSetup(event):
  ...     control = interfaces.IEventControl(event.term)
  ...     if not control.wasTypeDispatched(interfaces.ISetUpTermEvent):
  ...         raise interfaces.TermEventConditionError(
  ...             'Terms must be setup before they can be started.')

  >>> zope.component.provideSubscriptionAdapter(
  ...     doNotStartBeforeSetup,
  ...     (interfaces.IBeginTermEvent,), interfaces.ITermEventCondition)

Let's now try to call the startup event for our fall semester before the
setup:

  >>> interfaces.IEventControl(fall).dispatchType(interfaces.IBeginTermEvent)
  Traceback (most recent call last):
  ...
  TermEventConditionError: Terms must be setup before they can be started.

There is a set of standard events that SchoolTool provides:

``SetUpTermEvent``

  Begin with the setup of the term. This mainly means that the term is
  available in the rest of the UI.

``BeginTermEvent``

  The term actually begins. It is the first day at which classes meet and all
  services provided during the term are turned on.

``EndTermEvent``

  The term actually ends. It is the last day at which classes meet and all
  services available during the term are turned off.

``CloseTermEvent``

  This event indicates the time after which data associated with the term
  cannot be easily changed anymore. For example, grades cannot be submitted by
  instructors anymore.

``TearDownTermEvent``

  Finish up any data management of the term. For example, archive any data
  that is related to the term.

SchoolTool provides term event conditions to enforce the order (as listed) of
those events.

Custom Events and Conditions
++++++++++++++++++++++++++++

Some schools will require more fine-grained events than the ones provided by
SchoolTool. In those cases you can write your own term event. Let's say, for
example, that you would like to send out a warning two weeks before the end of
a semester:

  >>> class ITwoWeekWarningEvent(interfaces.ITermEvent):
  ...     '''The semester will be over in two weeks.'''

  >>> import zope.interface
  >>> class TwoWeekWarningEvent(event.TermEvent):
  ...     zope.interface.implements(ITwoWeekWarning)

Furthermore, you want to make sure that the warning gets sent out no earlier
than two weeks before the end of the semester, so you also implement a
condition:

  >>> today = datetime.date(2005, 12, 6)
  >>> def giveWarningInTime(event):
  ...     if datetime.date.today() < event.term.last - datetime.timedelta(14):
  ...         raise interfaces.TermEventConditionError(
  ...             'The warning must be sent within two weeks '
  ...             'of the end of the semester.')

  >>> zope.component.provideSubscriptionAdapter(
  ...     giveWarningInTime, (ITwoWeekWarning,), interfaces.ITermEventCondition)

Let's now send out the warning:

  >>> control = interfaces.IEventControl(fall)
  >>> control.dispatch(TwoWeekWarningEvent(fall))
  TwoWeekWarningEvent(<Semester u'Fall'>)

Now, if the condition is not fulfilled, we get an error:

  >>> del control.eventLog[-1]
  >>> today = datetime.date(2005, 11, 31)

  >>> control.dispatch(TwoWeekWarningEvent(fall))
  Traceback (most recent call last):
  ...
  TermEventConditionError: The warning must be sent within two weeks ...


Setting Up the Year at FHS
--------------------------

* We need an efficient API for multiple evaluations.

* We need custom evaluation objects that keep track of the term and section being
  assessed.

Each course has a set of special requirements -- these are requirements that
will appear on the report cards & must be evaluated each semester or marking
period.  These special requirements should know the appropriate score system
needed to evaluate them.

There are also specific sets of requirements that are applied at the end of
the first and third marking periods that apply to every section ('completes
homework,' etc).

So, I would create a year, which wouldn't have any direct evaluations.  Create
a fall semester and a spring semester, and indicate that for those terms
teachers must evaluate the course's "special requirements" for each of those
semesters.

Then I would create two marking periods, covering the first half of each
semester, and indicate that for each of these terms each section should be
evaluated for the specific set of requirements described above.

When I trigger the term's 'start' event, each section's subscriber picks up
the event, and causes the section to ask the term what 'report requirements'
it has, if any for that term.  Those events are added in a special category to
the gradebook for the section.

Requirements may need to be wrapped to prevent name duplication.

When I set up a term, I indicate what info, if any, is reported each term.
