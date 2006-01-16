===============
Requirement API
===============

Requirements are used to descibe an academic accomplishment.

  >>> from schooltool.requirement import interfaces, requirement

A requirement is a simple object:

  >>> forloop = requirement.Requirement(u'Write a for loop.')
  >>> forloop
  Requirement(u'Write a for loop.')

Commonly, requirements are grouped:

  >>> program = requirement.Requirement(u'Programming')
  >>> program
  Requirement(u'Programming')

Since grouping definitions implement the ``IContainer`` interface, we can
simply use the mapping interface to add other requirements:

  >>> program[u'forloop'] = forloop

The requirement is now available in the group:

  >>> sorted(program.keys())
  [u'forloop']

But the interesting part is the inheritance of requirements. Let's say
that the programming group above is defined as a requirement for any
programming class. Now we would like to extend that requirement to a Python
programming class:

  >>> pyprogram = requirement.Requirement(
  ...     u'Python Programming', program)
  >>> pyprogram[u'iter'] = requirement.Requirement(u'Create an iterator.')

So now the lookup of all requirements in ``pyprogram`` should be the generic and
python-specific requirements:

  >>> sorted(pyprogram.keys())
  [u'forloop', u'iter']

When looking at the requirements, one should be able to make the difference
between inherited and locally defined requirements:

  >>> pyprogram[u'iter']
  Requirement(u'Create an iterator.')

  >>> pyprogram[u'forloop']
  InheritedRequirement(Requirement(u'Write a for loop.'))

You can also inspect and manage the bases:

  >>> pyprogram.bases
  [Requirement(u'Programming')]

  >>> pyprogram.removeBase(program)
  >>> sorted(pyprogram.keys())
  [u'iter']

  >>> pyprogram.addBase(program)
  >>> sorted(pyprogram.keys())
  [u'forloop', u'iter']

Let's now look at a more advanced case. Let's say that the state of Virginia
requires all students to take a programming class that fulfills the
programming requirement:

  >>> va = requirement.Requirement(u'Virginia')
  >>> va[u'program'] = program

Now, Yorktown High School (which is in Virginia) teaches Python and thus
requires the Python requirement. However, Yorktown HS must still fulfill the
state requirement:

  >>> yhs = requirement.Requirement(u'Yorktow HS', va)
  >>> sorted(yhs[u'program'].keys())
  [u'forloop']

  >>> yhs[u'program'][u'iter'] = requirement.Requirement(u'Create an iterator.')

  >>> sorted(yhs[u'program'].keys())
  [u'forloop', u'iter']

  >>> sorted(va[u'program'].keys())
  [u'forloop']

Another tricky case is when the base is added later:

  >>> yhs = requirement.Requirement(u'Yorktow HS')
  >>> yhs[u'program'] = requirement.Requirement(u'Programming')
  >>> yhs[u'program'][u'iter'] = requirement.Requirement(u'Create an iterator.')

  >>> yhs.addBase(va)
  >>> sorted(yhs[u'program'].keys())
  [u'forloop', u'iter']

  >>> yhs[u'program'][u'iter']
  Requirement(u'Create an iterator.')

  >>> yhs[u'program'][u'forloop']
  InheritedRequirement(Requirement(u'Write a for loop.'))

We can also delete requirements from the groups. However, we should only be
able to delete locally defined requirements and not inherited ones:

  >>> del yhs[u'program'][u'iter']
  >>> sorted(yhs[u'program'].keys())
  [u'forloop']

  >>> del yhs[u'program'][u'forloop']
  Traceback (most recent call last):
  ...
  KeyError: u'forloop'


Overriding Requirements
~~~~~~~~~~~~~~~~~~~~~~~

Now let's have a look at a case where the more specific requirement overrides
the a sub-requirement of one of its bases. First we create a global
citizenship requirement that requires a person to be "good" globally.

  >>> citizenship = requirement.Requirement(u'Global Citizenship')
  >>> goodPerson = requirement.Requirement(u'Be a good person globally.')
  >>> citizenship['goodPerson'] = goodPerson

Now we create a local citizen requirement. Initially the local citizenship
inherits the "good person" requirement from the global citizenship:

  >>> localCitizenship = requirement.Requirement(
  ...     u'A Local Citizenship Requirement')
  >>> localCitizenship.addBase(citizenship)
  >>> print localCitizenship.values()
  [InheritedRequirement(Requirement(u'Be a good person globally.'))]

Now we override the "good person" requirement with a local one:

  >>> localGoodPerson = requirement.Requirement(u'Be a good person locally.')
  >>> localCitizenship['goodPerson'] = localGoodPerson
  >>> print localCitizenship.values()
  [Requirement(u'Be a good person locally.')]

This behavior is a design decision we made. But it is coherent with the
behavior of real inheritance and acquisition. Another policy might be that you
can never override a requirement like that and an error should occur. This is,
however, much more difficult, since adding bases becomes a very complex task
that would envolve complex conflict resolution.


Requirement Adapters
--------------------

Commonly we want to attach requirements to other objects such as
courses, sections and persons. This allows us to further refine the
requirements at various levels. Objects that have requirements associated with
them must provide the ``IHaveRequirement`` interface. Thus we first have to
implement an object that provides this interface.

  >>> import zope.interface
  >>> from zope.app import annotation
  >>> class Course(object):
  ...     zope.interface.implements(interfaces.IHaveRequirement,
  ...                               annotation.interfaces.IAttributeAnnotatable)
  ...     title = ""

  >>> course = Course()
  >>> course.title = u"Computer Science"

There exists an adapter from the ``IHaveRequirement`` interface to the
``IRequirement`` interface.

  >>> req = interfaces.IRequirement(course)
  >>> req
  Requirement(u'Computer Science')

The title of the course becomes the title of the requirement.  If we look at
the requirements, it is empty.

  >>> len(req)
  0
  >>> len(req.bases)
  0

If we want to add requirements to this course, there are two methods.  First we
can use inheritance as shown above:

  >>> req.addBase(yhs[u'program'])
  >>> sorted(req.keys())
  [u'forloop']
  >>> req[u'forloop']
  InheritedRequirement(InheritedRequirement(Requirement(u'Write a for loop.')))

Now if we add requirements to the Yorktown High School programming
requirements, they will show up as well.

  >>> yhs[u'program'][u'iter'] = requirement.Requirement(u'Create an iterator.')
  >>> sorted(req.keys())
  [u'forloop', u'iter']

The second method for adding requirements to the course is by directly adding
new requirements:

  >>> req[u'decorator'] = requirement.Requirement(u'Create a decorator!')
  >>> sorted(req.keys())
  [u'decorator', u'forloop', u'iter']
  >>> req[u'decorator']
  Requirement(u'Create a decorator!')


Score Systems
-------------

Score systems define the grading scheme of a group of or specific requirements.
Since scoring schemes vary widely among schools and even requirements, the
package provides two score system classes that can be used to create new
score systems.

The first class is designed for grades that are given as discrete values. For
example, if you want to be able to give the student a check, check plus, or
check minus, then you can create a scoresystem as follows:

  >>> from schooltool.requirement import scoresystem
  >>> check = scoresystem.DiscreteValuesScoreSystem(
  ...    u'Check', u'Check-mark score system',
  ...    ['+', 'v', '-'])

The first and second arguments of the constructor are the title and
description. The third argument is the list of grades that are allowed in the
score system. The grades **must** be sorted from the best to the worst. There
are a couple of methods associated with a score system. First, you can ask
whether a particular score is valid:

  >>> check.isValidScore('+')
  True
  >>> check.isValidScore('f')
  False

There is also a global "unscored" score that can be used when assigning
scores:

  >>> check.isValidScore(scoresystem.UNSCORED)
  True

The second method is there to check whether a score is a passing score.

  >>> check.isPassingScore('+') is None
  True

The result of this query is ``None``, because we have not defined a passing
score yet. This is optional, since not in every case the decision of whether
something is apassing score or not makes sense. If we initialize the score
system again -- this time providing a minimum passing grade -- the method will
provide more useful results:

  >>> from schooltool.requirement import scoresystem
  >>> check = scoresystem.DiscreteValuesScoreSystem(
  ...    u'Check', u'Check-mark score system',
  ...    ['+', 'v', '-'], 'v')
  >>> check
  <ScoreSystem u'Check'>

  >>> check.isPassingScore('+')
  True
  >>> check.isPassingScore('v')
  True
  >>> check.isPassingScore('-')
  False

Unscored returns a neutral result:

  >>> check.isPassingScore(scoresystem.UNSCORED) is None
  True

The package also provides some default score systems.

- A simple Pass/Fail score system:

  >>> scoresystem.PassFail
  <ScoreSystem u'Pass/Fail'>
  >>> scoresystem.PassFail.title
  u'Pass/Fail'
  >>> scoresystem.PassFail.PASS
  True
  >>> scoresystem.PassFail.FAIL
  False
  >>> scoresystem.PassFail.isValidScore(scoresystem.PassFail.PASS)
  True
  >>> scoresystem.PassFail.isPassingScore(scoresystem.PassFail.PASS)
  True
  >>> scoresystem.PassFail.isPassingScore(scoresystem.PassFail.FAIL)
  False

- The standard American letter score system:

  >>> scoresystem.AmericanLetterScoreSystem
  <ScoreSystem u'Letter Grade'>
  >>> scoresystem.AmericanLetterScoreSystem.title
  u'Letter Grade'
  >>> scoresystem.AmericanLetterScoreSystem.values
  ['A', 'B', 'C', 'D', 'F']
  >>> scoresystem.AmericanLetterScoreSystem.isValidScore('C')
  True
  >>> scoresystem.AmericanLetterScoreSystem.isValidScore('E')
  False
  >>> scoresystem.AmericanLetterScoreSystem.isPassingScore('D')
  True
  >>> scoresystem.AmericanLetterScoreSystem.isPassingScore('F')
  False

- The sxtended American letter score system:

  >>> scoresystem.ExtendedAmericanLetterScoreSystem
  <ScoreSystem u'Extended Letter Grade'>
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.title
  u'Extended Letter Grade'
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.values
  ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isValidScore('B-')
  True
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isValidScore('E')
  False
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isPassingScore('D-')
  True
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isPassingScore('F')
  False

The second score system class is the ranged values score system, which allows
you to define numerical ranges as grades. Let's say I have given a quiz that
has a maximum of 21 points:

  >>> quizScore = scoresystem.RangedValuesScoreSystem(
  ...     u'Quiz Score', u'Quiz Score System', 0, 21)
  >>> quizScore
  <ScoreSystem u'Quiz Score'>

Again, the first and second arguments are the title and description. The third
and forth arguments are the minum and maximum value of the numerical range. by
default the minimum value is 0, so I could have skipped that argument and just
provide a ``max`` keyword argument.

Practically any numerical value in the range between the minimum and maximum
value are valid scores:

  >>> quizScore.isValidScore(-1)
  False
  >>> quizScore.isValidScore(0)
  True
  >>> quizScore.isValidScore(13.43)
  True
  >>> quizScore.isValidScore(21)
  True
  >>> quizScore.isValidScore(21.1)
  False
  >>> quizScore.isValidScore(scoresystem.UNSCORED)
  True

Since we have not defined a minimum passing grade, we cannot get a meaningful
answer from the passing score evaluation:

  >>> quizScore.isPassingScore(13) is None
  True

Again, if we provide a passing score at the beginning, then those queries amke
sense:

  >>> quizScore = scoresystem.RangedValuesScoreSystem(
  ...     u'quizScore', u'Quiz Score System', 0, 21, 0.6*21) # 60%+ is passing

  >>> quizScore.isPassingScore(13)
  True
  >>> quizScore.isPassingScore(10)
  False
  >>> quizScore.isPassingScore(scoresystem.UNSCORED) is None
  True

The package provides only one default ranged values score system, the percent
score system:

  >>> scoresystem.PercentScoreSystem
  <ScoreSystem u'Percent'>
  >>> scoresystem.PercentScoreSystem.title
  u'Percent'
  >>> scoresystem.PercentScoreSystem.min
  0
  >>> scoresystem.PercentScoreSystem.max
  100

  >>> scoresystem.PercentScoreSystem.isValidScore(40)
  True
  >>> scoresystem.PercentScoreSystem.isValidScore(scoresystem.UNSCORED)
  True

  >>> scoresystem.PercentScoreSystem.isPassingScore(60)
  True
  >>> scoresystem.PercentScoreSystem.isPassingScore(59)
  False
  >>> scoresystem.PercentScoreSystem.isPassingScore(scoresystem.UNSCORED)

There is also an ``AbstractScoreSystem`` class that implements the title,
description and representation for you already. It is used for both of the
above types of score system. If you need to develop a score system that does
not fit into any of the two categories, you might want to develop one using
this abstract class.

Finally, I would like to talk a little bit more about the ``UNSCORED``
score. This global is not just a string, so that is will more efficiently
store in the ZODB:

  >>> scoresystem.UNSCORED
  UNSCORED
  >>> scoresystem.UNSCORED.__reduce__()
  'UNSCORED'
  >>> import pickle
  >>> len(pickle.dumps(scoresystem.UNSCORED))
  49


Evaluations
-----------

Evaluations provide a score for a single requirement for a single person. The
value of the evaluation depends on the score system. Evaluations are attached
to objects providing the ``IHaveEvaluations`` interface. In our use cases,
those objects are usually people.

  >>> class Person(object):
  ...     zope.interface.implements(interfaces.IHaveEvaluations,
  ...                               annotation.interfaces.IAttributeAnnotatable)
  ...     def __init__(self, name):
  ...         self.name = name
  ...
  ...     def __repr__(self):
  ...         return "%s(%r)" % (self.__class__.__name__, self.name)

  >>> student = Person(u'Sample Student')

Evaluations are made by an evaluator:

  >>> teacher = Person(u'Sample Teacher')

The evaluations for an evaluatable object can be accessed using the
``IEvaluations`` adapter:

  >>> evals = interfaces.IEvaluations(student)
  >>> evals
  <Evaluations for Person(u'Sample Student')>
  >>> from zope.app import zapi
  >>> zapi.getParent(evals)
  Person(u'Sample Student')

Initially, there are no evaluations available.

  >>> sorted(evals.keys())
  []

We now create a new evaluation.  When creating an evaluation, the following
arguments must be passed to the constructor:

 - ``requirement``
   The requirement should be a reference to a provider of the ``IRequirement``
   interface.

 - ``scoreSystem``
   The score system should be a reference to a provider of the ``IScoreSystem``
   interface.

 - ``value``
   The value is a data structure that represents a valid score for the given
   score system.

 - ``evaluator``
   The evaluator should be an object reference that represents the principal
   making the evaluation. This will usually be a ``Person`` instance.

For example, we would like to score the student's skill for writing iterators
in the programming class.

  >>> pf = scoresystem.PassFail
  >>> from schooltool.requirement import evaluation
  >>> ev = evaluation.Evaluation(req[u'iter'], pf, pf.PASS, teacher)
  >>> ev.requirement
  InheritedRequirement(Requirement(u'Create an iterator.'))
  >>> ev.scoreSystem
  <ScoreSystem u'Pass/Fail'>
  >>> ev.value
  True
  >>> ev.evaluator
  Person(u'Sample Teacher')
  >>> ev.time
  datetime.datetime(...)

The evaluation also has an ``evaluatee`` property, but since we have not
assigned the evaluation to the person, looking up the evaluatee raises an
value error:

  >>> ev.evaluatee
  Traceback (most recent call last):
  ...
  ValueError: Evaluation is not yet assigned to a evaluatee

Now that an evaluation has been created, we can add it to the student's
evaluations.

  >>> name = evals.addEvaluation(ev)
  >>> sorted(evals.values())
  [<Evaluation for Inhe...ent(Requirement(u'Create an iterator.')), value=True>]

Now that the evaluation is added, the evaluatee is also available:

  >>> ev.evaluatee
  Person(u'Sample Student')

Once several evaluations have been created, we can do some interesting queries.
To demonstrate this feature effectively, we have to create a new requirement
tree.

  >>> calculus = requirement.Requirement(u'Calculus')

  >>> calculus[u'int'] = requirement.Requirement(u'Integration')
  >>> calculus[u'int']['fourier'] = requirement.Requirement(
  ...     u'Fourier Transform')
  >>> calculus[u'int']['path'] = requirement.Requirement(u'Path Integral')

  >>> calculus[u'diff'] = requirement.Requirement(u'Differentiation')
  >>> calculus[u'diff'][u'partial'] = requirement.Requirement(
  ...     u'Partial Differential Equations')
  >>> calculus[u'diff'][u'systems'] = requirement.Requirement(u'Systems')

  >>> calculus[u'limit'] = requirement.Requirement(u'Limit Theorem')

  >>> calculus[u'fundamental'] = requirement.Requirement(
  ...     u'Fundamental Theorem of Calculus')

While our sample teacher teaches programming and differentiation, a second
teacher teaches integration.

  >>> teacher2 = Person(u'Mr. Elkner')

With that done (phew), we can create evaluations based on these requirements.

  >>> student2 = Person(u'Student Two')
  >>> evals = interfaces.IEvaluations(student2)

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'int'][u'fourier'], pf, pf.FAIL, teacher2))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'int'][u'path'], pf, pf.PASS, teacher2))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'diff'][u'partial'], pf, pf.FAIL, teacher))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'diff'][u'systems'], pf, pf.PASS, teacher))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'limit'], pf, pf.FAIL, teacher))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'fundamental'], pf, pf.PASS, teacher2))

So now we can ask for all evaluations for which the sample teacher is the
evaluator:

  >>> teacherEvals = evals.getEvaluationsOfEvaluator(teacher)
  >>> teacherEvals
  <Evaluations for Person(u'Student Two')>

  >>> [value for key, value in sorted(
  ...     teacherEvals.items(), key=lambda x: x[1].requirement.title)]
  [<Evaluation for Requirement(u'Limit Theorem'), value=False>,
   <Evaluation for Requirement(u'Partial Differential Equations'), value=False>,
   <Evaluation for Requirement(u'Systems'), value=True>]

As you can see, the query method returned another evaluations object having the
student as a parent.  It is very important that the evaluated object is not
lost.  The big advantage of returning an evaluations object is the ability to
perform chained queries:

  >>> result = evals.getEvaluationsOfEvaluator(teacher) \
  ...               .getEvaluationsForRequirement(calculus[u'diff'])
  >>> [value for key, value in sorted(
  ...     result.items(), key=lambda x: x[1].requirement.title)]
  [<Evaluation for Requirement(u'Partial Differential Equations'), value=False>,
   <Evaluation for Requirement(u'Systems'), value=True>]

By default, these queries search recursively through the entire subtree of the
requirement.  However, you can call turn off the recursion:

  >>> result = evals.getEvaluationsOfEvaluator(teacher) \
  ...               .getEvaluationsForRequirement(calculus, recurse=False)
  >>> sorted(result.values())
  [<Evaluation for Requirement(u'Limit Theorem'), value=False>]

Of course, the few query methods defined by the container are not sufficient in
all cases. In those scenarios, you can develop adapters that implement custom
queries. The package provides a nice abstract base query adapter that can be
used as follows:

  >>> class PassedQuery(evaluation.AbstractQueryAdapter):
  ...     def _query(self):
  ...         return [(key, eval)
  ...                 for key, eval in self.context.items()
  ...                 if eval.scoreSystem.isPassingScore(eval.value)]

  >>> result = PassedQuery(evals)().getEvaluationsOfEvaluator(teacher)
  >>> sorted(result.values())
  [<Evaluation for Requirement(u'Systems'), value=True>]


The ``IEvaluations`` API
~~~~~~~~~~~~~~~~~~~~~~~~

Contrary to what you might expect, the evaluations object is not a container,
but a mapping from requirement to evaluation. The key reference package is used
to create a hashable key for the requirement. The result is an object where we
can quickly lookup the evaluation for a given requirement, which is clearly
the most common form of query.

This section demonstrates the implementation of the ``IMapping`` API.

  >>> evals = evaluation.Evaluations(
  ...     [(calculus[u'limit'],
  ...       evaluation.Evaluation(calculus[u'limit'], pf, pf.PASS, teacher)),
  ...      (calculus[u'diff'],
  ...       evaluation.Evaluation(calculus[u'diff'], pf, pf.FAIL, teacher))]
  ...     )

- ``__getitem__(key)``

  >>> evals[calculus[u'limit']]
   <Evaluation for Requirement(u'Limit Theorem'), value=True>
  >>> evals[calculus[u'fundamental']]
  Traceback (most recent call last):
  ...
  KeyError: <schooltool.requirement.testing.KeyReferenceStub ...>

- ``__delitem__(key)``

  >>> del evals[calculus[u'limit']]
  >>> len(evals._btree)
  1
  >>> del evals[calculus[u'fundamental']]
  Traceback (most recent call last):
  ...
  KeyError: <schooltool.requirement.testing.KeyReferenceStub ...>

- ``__setitem__(key, value)``

  >>> evals[calculus[u'limit']] = evaluation.Evaluation(
  ...     calculus[u'limit'], pf, pf.PASS, teacher)
  >>> len(evals._btree)
  2

- ``get(key, default=None)``

  >>> evals.get(calculus[u'limit'])
   <Evaluation for Requirement(u'Limit Theorem'), value=True>
  >>> evals.get(calculus[u'fundamental'], default=False)
  False

- ``__contains__(key)``

  >>> calculus[u'limit'] in evals
  True
  >>> calculus[u'fundamental'] in evals
  False

- ``keys()``

  >>> sorted(evals.keys(), key = lambda x: x.title)
  [Requirement(u'Differentiation'), Requirement(u'Limit Theorem')]

- ``__iter__()``

  >>> sorted(iter(evals), key=lambda x: x.title)
  [Requirement(u'Differentiation'), Requirement(u'Limit Theorem')]

- ``values()``

  >>> sorted(evals.values(), key=lambda x: x.requirement.title)
  [<Evaluation for Requirement(u'Differentiation'), value=False>,
   <Evaluation for Requirement(u'Limit Theorem'), value=True>]

- ``items()``

  >>> sorted(evals.items(), key=lambda x: x[0].title)
  [(Requirement(u'Differentiation'),
    <Evaluation for Requirement(u'Differentiation'), value=False>),
   (Requirement(u'Limit Theorem'),
    <Evaluation for Requirement(u'Limit Theorem'), value=True>)]

- ``__len__()``

  >>> len(evals)
  2
