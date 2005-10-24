========================
Student Level Management
========================

Students, a special kind of ``Person``, during their academic career in a
school will progress through a number of levels (or grades or standings) until
they graduate. This package provides the basic level-support for
SchoolTool.

    >>> import schooltool.level.level
    >>> from schooltool import level


Level Management
----------------

The first task of any school manager is to setup the levels for the
school. So, given a schooltool application

    >>> from schooltool.testing import setup
    >>> st = setup.createSchoolToolApplication()

with a manager group, which is setup during database instantiation,

    >>> from schooltool.group.group import Group
    >>> st['groups']['manager'] = Group(u'Manager', u'Manager Group.')

we can inspect the defined levels:

    >>> list(st['levels'].keys())
    []

As expected, this list is empty at the beginning. Let's now say that our
school X has an US elementary and middle school. Let's start with the
elementary school:

    >>> st['levels']['level1'] = level.level.Level('1st Grade', isInitial=True)

We also passed in the flag ``isInitial`` as true, since this is the first
level a student completes in elementary school. Now let's repeat this step for
the remaining levels:

    >>> st['levels']['level2'] = level.level.Level('2nd Grade', isInitial=True)
    >>> st['levels']['level1'].nextLevel = st['levels']['level2']

    >>> st['levels']['level3'] = level.level.Level('3rd Grade')
    >>> st['levels']['level2'].nextLevel = st['levels']['level3']

    >>> st['levels']['level4'] = level.level.Level('4th Grade')
    >>> st['levels']['level3'].nextLevel = st['levels']['level4']

    >>> st['levels']['level5'] = level.level.Level('5th Grade')
    >>> st['levels']['level4'].nextLevel = st['levels']['level5']

    >>> st['levels']['level6'] = level.level.Level('6th Grade')
    >>> st['levels']['level5'].nextLevel = st['levels']['level6']

In the code above we also linked the levels together by assigning the
``nextLevel`` attribute of each level. Level 6 does not have any next level,
because the student graduates from elementary school at this time. Since it is
a bit tedious to setup levels in this order, it is better to setup the levels
from the last to the first. We will do that for the middle school:

    >>> st['levels']['level8'] = level.level.Level('8th Grade')
    >>> st['levels']['level7'] = level.level.Level(
    ...     '7th Grade', isInitial=True, nextLevel=st['levels']['level8'])

As you can see the level constructor can also accept a ``nextLevel`` argument
that can be used to immediately specify the next level. Once the levels are
setup, one can validate the level graphs:

    >>> st['levels'].validate()

If the function simply returns, no issues were found, which is the case here.


Validating Level Graphs
-----------------------

Let's quickly explore what happens, if the validation method finds some
problems. In those cases errors will be raised.

The first error the method will catch is a looping level graph. In those cases
following the levels will result in a loop, so that a student can never
graduate:

    >>> levels = level.level.LevelContainer()

    >>> levels['level2'] = level.level.Level('2nd Grade')
    >>> levels['level1'] = level.level.Level(
    ...     '1st Grade', isInitial=True, nextLevel=levels['level2'])

So far so good, ...

    >>> levels.validate()

... but now we add the fatal connection:

    >>> levels['level2'].nextLevel = levels['level1']
    >>> levels.validate()
    Traceback (most recent call last):
    ...
    LevelLoopError: Loop-Closing Level: level2

The duplicated level is also stored in the error as ``duplicate``.

The second type of error occurs, if a level is not connected to a graph.

    >>> levels = level.level.LevelContainer()

    >>> levels['level2'] = level.level.Level('2nd Grade')
    >>> levels['level1'] = level.level.Level(
    ...     '1st Grade', isInitial=True, nextLevel=levels['level2'])

We now add third and fourth levels that are not an initial levels and are not
next levels either:

    >>> levels['level3'] = level.level.Level('3rd Grade')
    >>> levels['level5'] = level.level.Level('5th Grade')

    >>> levels.validate()
    Traceback (most recent call last):
    ...
    DisconnectedLevelsError: level3, level5

The disconnected levels are accessible from the ``levels`` attribute of the
exception.


The Level Vocabulary
--------------------

The module also provides a level vocabulary. This allows us to provide UIs
that let you select one or more levels. For the vocabulary to work, we have to
register a schooltool application object as the current site:

    >>> from zope.app.testing import setup
    >>> sm = setup.createSiteManager(st, setsite=True)

Now we can create

    >>> vocab = level.level.LevelVocabulary()

and use the vocabulary:

    >>> st['levels']['level3'] in vocab
    True

    >>> len(vocab)
    8

    >>> term = vocab.getTerm(st['levels']['level3'])
    >>> term.value
    <Level '3rd Grade'>
    >>> term.title
    '3rd Grade'
    >>> term.token
    u'level3'
    >>> vocab.getTerm(None)
    Traceback (most recent call last):
    ...
    LookupError: None

    >>> term = vocab.getTermByToken(u'level3')
    >>> term.value
    <Level '3rd Grade'>
    >>> term.title
    '3rd Grade'
    >>> term.token
    u'level3'
    >>> vocab.getTermByToken('empty')
    Traceback (most recent call last):
    ...
    LookupError: empty

    >>> pprint(list(iter(vocab)))
    [<LevelTerm token='level1' title='1st Grade'>,
     <LevelTerm token='level2' title='2nd Grade'>,
     <LevelTerm token='level3' title='3rd Grade'>,
     <LevelTerm token='level4' title='4th Grade'>,
     <LevelTerm token='level5' title='5th Grade'>,
     <LevelTerm token='level6' title='6th Grade'>,
     <LevelTerm token='level7' title='7th Grade'>,
     <LevelTerm token='level8' title='8th Grade'>]


Student Promotion Workflow
--------------------------

There are three outcomes for a student from a level:

  - Passed: In that case the student will progress to the next level. If there
            is no next level, the student will graduate.

  - Failed: The student will have to repeat the level. (This is a bit
            oversimplified, but will suffice for now. In many schools a level
            cannot be repeated indefinitely and in colleges the concept of
            failing a level does not exist at all.)

  - Withdrawn: In some cases students leave the school for variety of reasons:
               relocation, drop-out, transfer.

Thus, the resulting workflow for completing a single level would look as
follows::

                                           +----------+     +----------+
                            +------------> |   Pass   | --> | Graduate | --> E
                            |              +----------+     +----------+
                            V
        +--------+     +----------+        +----------+
  S --> | Enroll | --> | Complete | <----> |   Fail   |
        +--------+     +----------+        +----------+
                            |
                            |              +----------+
                            +------------> | Withdraw | --> E
                                           +----------+

The Process Definition
~~~~~~~~~~~~~~~~~~~~~~

This workflow is described by the file `promotion.xpdl` and can be loaded into
a process definition as follows:

   >>> from zope.wfmc import xpdl
   >>> import os
   >>> package = xpdl.read(open(os.path.join(this_directory,
   ...                                       'promotion.xpdl')))

The package only defines one process definition, our permission process:

   >>> pd = package['promotion']

Let's now inspect the the process definition some more to ensure it is
correct. First let's make sure that all activities are there:

    >>> pprint(pd.activities) #doctest:+ELLIPSIS
    {'complete': <ActivityDefinition u'Complete Level'>,
     'enroll': <ActivityDefinition u'Enroll'>,
     'fail': <ActivityDefinition u'Fail'>,
     'graduate': <ActivityDefinition u'Graduate'>,
     'pass': <ActivityDefinition u'Pass'>,
     'withdraw': <ActivityDefinition u'Withdraw'>}

Let's now examine every activity to ensure that all applications are correctly
defined:

    >>> pprint([(id, showApplications(act, pd))
    ...         for id, act in pd.activities.items()])
    [('enroll',
      [<Application u'Write Record': (student, level) --> ()>,
       <Application u'Select Initial Level': () --> (level)>,
       <Application u'Update Status': (student) --> ()>]),
     ('complete',
      [<Application u'Set Level Outcome': () --> (outcome)>]),
     ('graduate',
      [<Application u'Update Status': (student) --> ()>]),
     ('withdraw',
      [<Application u'Update Status': (student) --> ()>,
       <Application u'Write Record': (student, level) --> ()>]),
     ('pass',
      [<Application u'Write Record': (student, level) --> ()>,
       <Application u'Progress to Next Level': (level) --> (level)>]),
     ('fail',
      [<Application u'Write Record': (student, level) --> ()>])]

Next we have a look at the transitions:

    >>> pprint(pd.transitions)
    [TransitionDefinition(from=u'enroll', to=u'complete'),
     TransitionDefinition(from=u'complete', to=u'pass'),
     TransitionDefinition(from=u'complete', to=u'fail'),
     TransitionDefinition(from=u'complete', to=u'withdraw'),
     TransitionDefinition(from=u'pass', to=u'graduate'),
     TransitionDefinition(from=u'pass', to=u'complete'),
     TransitionDefinition(from=u'fail', to=u'complete')]

Note that the order of some of those transitions is important, since
transitions are checked in the order they are listed.

Finally, let's make sure that the participants are available as well:

    >>> pd.participants
    {'manager': Participant(u'Manager')}


Integrating the workflow into SchoolTool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we have loaded and verified the process definition, we have to hook
it into schooltool. This is done via the integration, which will provide
actual implementations of the participants and applications (known as work
items). Here we choose the adapter integration, which will look up
participants and work items via the adapter registry:

    >>> from zope.wfmc.adapter import integration
    >>> pd.integration = integration

Note that until now, we have not needed any SchoolTool-specific code, which
means that in theory the process definition can be used by various
systems. With the registration of the adapters we now hook it up specifically
for SchoolTool:

    >>> import zope.component
    >>> import zope.wfmc.interfaces
    >>> from schooltool.level import promotion

    >>> zope.component.provideAdapter(promotion.Manager,
    ...                               provides=zope.wfmc.interfaces.IParticipant,
    ...                               name='promotion.manager')

    >>> zope.component.provideAdapter(promotion.ProgressToNextLevel,
    ...                               name='promotion.progressToNextLevel')
    >>> zope.component.provideAdapter(promotion.SelectInitialLevel,
    ...                               provides=zope.wfmc.interfaces.IWorkItem,
    ...                               name='promotion.selectInitialLevel')
    >>> zope.component.provideAdapter(promotion.SetLevelOutcome,
    ...                               provides=zope.wfmc.interfaces.IWorkItem,
    ...                               name='promotion.setLevelOutcome')
    >>> zope.component.provideAdapter(promotion.UpdateStatus,
    ...                               name='promotion.updateStatus')
    >>> zope.component.provideAdapter(promotion.WriteRecord,
    ...                               name='promotion.writeRecord')

We also need to set up an adapter to retrieve current work items for the
manager group

    >>> from schooltool.group.interfaces import IGroup
    >>> from schooltool.level import interfaces
    >>> zope.component.provideAdapter(promotion.getManagerWorkItems,
    ...                               adapts=(IGroup,),
    ...                               provides=interfaces.IManagerWorkItems)

and one adapter to access and manage the academic record of the student:

    >>> from schooltool.level import record
    >>> zope.component.provideAdapter(record.AcademicRecord)


Testing the Workflow Process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We are almost ready now to run through the academic career of a student. The
only task left is to

  o get the `manager` group, which will complete all the work items:

    >>> manager = st['groups']['manager']

  o create a student which attends the school:

    >>> from schooltool.person import person
    >>> st['persons']['student'] = person.Person('student', 'Mr. Student')
    >>> student = st['persons']['student']

  o register an event listener, so that we can see the flow through the process:

    >>> def log_workflow(event):
    ...     print event

    >>> import zope.event
    >>> zope.event.subscribers.append(log_workflow)

  o register the process definition as a utility:

    >>> zope.component.provideUtility(pd, name='promotion')

Now we can create a process from our process definition by simply calling it:

    >>> proc = pd()

You then start the process by calling the method ``start()``. The arguments to
this method are the values of the formal input parameters of the process
definition:

    # Arguments: student, level, outcome
    >>> proc.start(student, None, None)
    ProcessStarted(Process(u'promotion'))
    Transition(None, Activity(u'promotion.enroll'))
    ActivityStarted(Activity(u'promotion.enroll'))
    WorkItemFinished(u'writeRecord')
    WorkItemFinished(u'updateStatus')

If we now look at the student's academic record, we will see that the student
is now marked as enrolled and the academic history shows an entry as well:

    >>> rec = level.interfaces.IAcademicRecord(student)
    >>> rec.status
    'Enrolled'
    >>> rec.history #doctest:+ELLIPSIS
    [HistoricalRecord('Enrolled' at ...)]

The manager group should also have some work items:

    >>> work = level.interfaces.IManagerWorkItems(manager)
    >>> work.values() #doctest:+ELLIPSIS
    [<schooltool.level.promotion.SelectInitialLevel object at ...>]

We can now select the work item and pass in the initial level. The student will
start at the first grade:

    >>> item = list(work.values())[-1]
    >>> item.finish(st['levels']['level1'])
    WorkItemFinished(u'selectInitialLevel')
    ActivityFinished(Activity(u'promotion.enroll'))
    Transition(Activity(u'promotion.enroll'), Activity(u'promotion.complete'))
    ActivityStarted(Activity(u'promotion.complete'))

Now the student is completing the first class.

    >>> proc.workflowRelevantData.level
    <Level '1st Grade'>

S/he passes the class easily:

    >>> list(work.values()) #doctest:+ELLIPSIS
    [<schooltool.level.promotion.SetLevelOutcome object at ...>]

    >>> item = list(work.values())[-1]
    >>> item.finish('pass')
    WorkItemFinished(u'setLevelOutcome')
    ActivityFinished(Activity(u'promotion.complete'))
    Transition(Activity(u'promotion.complete'), Activity(u'promotion.pass'))
    ActivityStarted(Activity(u'promotion.pass'))
    WorkItemFinished(u'writeRecord')
    WorkItemFinished(u'progressToNextLevel')
    ActivityFinished(Activity(u'promotion.pass'))
    Transition(Activity(u'promotion.pass'), Activity(u'promotion.complete'))
    ActivityStarted(Activity(u'promotion.complete'))

As we can see, the workflow went to the `Pass` activity and completed several
workitems. We have a new entry in the history

    >>> rec.history[-1] #doctest:+ELLIPSIS
    HistoricalRecord('Passed' at ...)

    >>> rec.history[-1].description
    u'Passed level "1st Grade"'

and the student is now in the second grade:

    >>> proc.workflowRelevantData.level
    <Level '2nd Grade'>

In second grade, however, s/he has troubles and fails.

    >>> list(work.values()) #doctest:+ELLIPSIS
    [<schooltool.level.promotion.SetLevelOutcome object at ...>]

    >>> item = list(work.values())[-1]
    >>> item.finish('fail')
    WorkItemFinished(u'setLevelOutcome')
    ActivityFinished(Activity(u'promotion.complete'))
    Transition(Activity(u'promotion.complete'), Activity(u'promotion.fail'))
    ActivityStarted(Activity(u'promotion.fail'))
    WorkItemFinished(u'writeRecord')
    ActivityFinished(Activity(u'promotion.fail'))
    Transition(Activity(u'promotion.fail'), Activity(u'promotion.complete'))
    ActivityStarted(Activity(u'promotion.complete'))

Thus, the record is not as positive:

    >>> rec.history[-1] #doctest:+ELLIPSIS
    HistoricalRecord('Failed' at ...)

    >>> rec.history[-1].description
    u'Failed level "2nd Grade"'

    >>> proc.workflowRelevantData.level
    <Level '2nd Grade'>

But after that she is fine again until s/he graduates elementary school:

    >>> list(work.values())[-1].finish('pass') #doctest:+ELLIPSIS
    WorkItemFinished(u'setLevelOutcome')
    ...
    ActivityStarted(Activity(u'promotion.complete'))

    >>> list(work.values())[-1].finish('pass') #doctest:+ELLIPSIS
    WorkItemFinished(u'setLevelOutcome')
    ...
    ActivityStarted(Activity(u'promotion.complete'))

    >>> list(work.values())[-1].finish('pass') #doctest:+ELLIPSIS
    WorkItemFinished(u'setLevelOutcome')
    ...
    ActivityStarted(Activity(u'promotion.complete'))

    >>> list(work.values())[-1].finish('pass') #doctest:+ELLIPSIS
    WorkItemFinished(u'setLevelOutcome')
    ...
    ActivityStarted(Activity(u'promotion.complete'))

    >>> list(work.values())[-1].finish('pass')
    WorkItemFinished(u'setLevelOutcome')
    ActivityFinished(Activity(u'promotion.complete'))
    Transition(Activity(u'promotion.complete'), Activity(u'promotion.pass'))
    ActivityStarted(Activity(u'promotion.pass'))
    WorkItemFinished(u'writeRecord')
    WorkItemFinished(u'progressToNextLevel')
    ActivityFinished(Activity(u'promotion.pass'))
    Transition(Activity(u'promotion.pass'), Activity(u'promotion.graduate'))
    ActivityStarted(Activity(u'promotion.graduate'))
    WorkItemFinished(u'updateStatus')
    ActivityFinished(Activity(u'promotion.graduate'))
    ProcessFinished(Process(u'promotion'))

As you can see above, after the student passed the final level in elementary
school, s/he graduated:

    >>> rec.status
    'Graduated'

This also completed the process. Now our student enters middle school, which
requires a new process:

    >>> proc.start(student, None, None)
    ProcessStarted(Process(u'promotion'))
    Transition(None, Activity(u'promotion.enroll'))
    ActivityStarted(Activity(u'promotion.enroll'))
    WorkItemFinished(u'writeRecord')
    WorkItemFinished(u'updateStatus')

    >>> item = list(work.values())[-1]
    >>> item.finish(st['levels']['level7'])
    WorkItemFinished(u'selectInitialLevel')
    ActivityFinished(Activity(u'promotion.enroll'))
    Transition(Activity(u'promotion.enroll'), Activity(u'promotion.complete'))
    ActivityStarted(Activity(u'promotion.complete'))

However, after a few months the family is moving and the student withdraws
from the school:

    >>> list(work.values())[-1].finish('withdraw')
    WorkItemFinished(u'setLevelOutcome')
    ActivityFinished(Activity(u'promotion.complete'))
    Transition(Activity(u'promotion.complete'), Activity(u'promotion.withdraw'))
    ActivityStarted(Activity(u'promotion.withdraw'))
    WorkItemFinished(u'updateStatus')
    WorkItemFinished(u'writeRecord')
    ActivityFinished(Activity(u'promotion.withdraw'))
    ProcessFinished(Process(u'promotion'))

    >>> rec.status
    'Withdrawn'

    >>> rec.history[-1] #doctest:+ELLIPSIS
    HistoricalRecord('Withdrawn' at ...)

    >>> rec.history[-1].description
    u'Withdrew before or during level "7th Grade"'

    >>> rec.history[-1].user
    '<unknown>'

Cleanup:

    >>> zope.event.subscribers.pop() #doctest: +ELLIPSIS
    <function log_workflow at ...>


Process Storage Management
--------------------------

Now we know how the promotion workflow functions, but where is it stored? A
subscriber to the ``IProcessStarted`` event stores the process usign the
academic record API. Using a stub implementation for the workflow process and
the event,

    >>> student = person.Person('student', 'Mr. Student')

    >>> class Process(object):
    ...     process_definition_identifier = 'schooltool.promotion'
    ...     student = None
    ...     def __getattr__(self, name):
    ...         return self
    >>> process = Process()
    >>> process.student = student

    >>> class Event(object):
    ...     pass
    >>> event = Event()
    >>> event.process = process

we can assign the process to a student:

    >>> promotion.addProcessToStudent(event)
    >>> interfaces.IAcademicRecord(student).levelProcess is process
    True

The process is removed from the student using a ``IProcessFinished`` event
subscriber:

    >>> promotion.removeProcessFromStudent(event)
    >>> interfaces.IAcademicRecord(student).levelProcess is None
    True
