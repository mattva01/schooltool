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

#The following tests inheritence when a sub requirement in a base is under
#the same key as an uninherited sub requirement
#
#  >>> citinzenship = requirement.Requirement(u'Global Citizenship')
#  >>> goodPerson = requirement.Requirement(u'Be a good person globally.')
#  >>> citinzenship['goodPerson'] = goodPerson
#
#  >>> localCitizenship = requirement.Requirement(u'A Local Citizenship Requirement')
#  >>> localCitizenship.addBase(citinzenship)
#  >>> print localCitizenship.values()
#  <BLANKLINE>
#  ...Requirement(u'Be a good person globally.')...
#
#  >>> localGoodPerson = requirement.Requirement(u'Be a good person locally.')
#  >>> localCitizenship['goodPerson'] = localGoodPerson
#  >>> print localCitizenship.values()
#  <BLANKLINE>
#  ...Requirement(u'Be a good person globally.')...


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
package provides an abstract score system class.  Below is an example
implementation for a simple pass/fail score system.

  >>> from schooltool.requirement import scoresystem
  >>> class PassFail(scoresystem.AbstractScoreSystem):
  ...     PASS = True
  ...     FAIL = False
  ...     def isPassingScore(self, score):
  ...         return bool(score)
  ...
  ...     def isValidScore(self, score):
  ...         return score in [self.PASS, self.FAIL, scoresystem.UNSCORED]
  ...
  ...     def __repr__(self):
  ...         return '%s(%r)' % (self.__class__.__name__, self.title)

The part of the interface that must be implemented is the ``isPassingScore()``
and ``isValidScore`` methods. The latter method must always return ``True`` for
the ``UNSCORED`` value. The ``AbstractScoreSystem`` class already fulfills the
other requirements of the ``IScoreSystem`` interface.

  >>> pf = PassFail(u'Simple Pass/Fail Score System')
  >>> pf.title
  u'Simple Pass/Fail Score System'
  >>> pf.description is None
  True

We can now check whether a particular score is a pass or fail:

  >>> pf.isPassingScore(1)
  True
  >>> pf.isPassingScore(0)
  False

Furthermore, we can test whether a score conforms to the score system.

  >>> pf.isValidScore(PassFail.PASS)
  True
  >>> pf.isValidScore(scoresystem.UNSCORED)
  True
  >>> pf.isValidScore('pass')
  False



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

  >>> from schooltool.requirement import evaluation
  >>> ev = evaluation.Evaluation(req[u'iter'], pf, PassFail.PASS, teacher)
  >>> ev.requirement
  InheritedRequirement(Requirement(u'Create an iterator.'))
  >>> ev.scoreSystem
  PassFail(u'Simple Pass/Fail Score System')
  >>> ev.value
  True
  >>> ev.evaluator
  Person(u'Sample Teacher')
  >>> ev.time
  datetime.datetime(...)

Now that an evaluation has been created, we can add it to the student's
evaluations.

  >>> name = evals.addEvaluation(ev)
  >>> sorted(evals.values())
  [<Evaluation for Inhe...ent(Requirement(u'Create an iterator.')), value=True>]

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

  >>> name = evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'int'][u'fourier'], pf, PassFail.FAIL, teacher2))

  >>> name = evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'int'][u'path'], pf, PassFail.PASS, teacher2))

  >>> name = evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'diff'][u'partial'], pf, PassFail.FAIL, teacher))

  >>> name = evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'diff'][u'systems'], pf, PassFail.PASS, teacher))

  >>> name = evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'limit'], pf, PassFail.FAIL, teacher))

  >>> name = evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'fundamental'], pf, PassFail.PASS, teacher2))

So now we can ask for all evaluations for which the sample teacher is the
evaluator:

  >>> teacherEvals = evals.getEvaluationsOfEvaluator(teacher)
  >>> teacherEvals
  <Evaluations for Person(u'Student Two')>

  >>> [value for name, value in sorted(teacherEvals.items())]
  [<Evaluation for Requirement(u'Partial Differential Equations'), value=False>,
   <Evaluation for Requirement(u'Systems'), value=True>,
   <Evaluation for Requirement(u'Limit Theorem'), value=False>]

As you can see, the query method returned another evaluations object having the
student as a parent.  It is very important that the evaluated object is not
lost.  The big advantage of returning an evaluations object is the ability to
perform chained queries:

  >>> result = evals.getEvaluationsOfEvaluator(teacher) \
  ...               .getEvaluationsForRequirement(calculus[u'diff'])
  >>> [value for name, value in sorted(result.items())]
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
  ...         return [(name, eval)
  ...                 for name, eval in self.context.items()
  ...                 if eval.scoreSystem.isPassingScore(eval.value)]

  >>> result = PassedQuery(evals)().getEvaluationsOfEvaluator(teacher)
  >>> sorted(result.values())
  [<Evaluation for Requirement(u'Systems'), value=True>]
