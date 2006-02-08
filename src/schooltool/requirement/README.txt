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

Finally, requirements are ordered containers, which means that you can change
the order of the dependency requirements. Let's first create a new
requirements structure:

  >>> physics = requirement.Requirement(u'Physics')
  >>> physics[u'thermo'] = requirement.Requirement(u'Thermodynamics')
  >>> physics[u'mech'] = requirement.Requirement(u'Mechanics')
  >>> physics[u'rel'] = requirement.Requirement(u'Special Relativity')
  >>> physics[u'elec'] = requirement.Requirement(u'Electromagnetism')

  >>> college_physics = requirement.Requirement(u'College Physics', physics)
  >>> college_physics[u'quant'] = requirement.Requirement(u'Quantum Mechanics')

Now let's have a look at the original order:

  >>> physics.keys()
  [u'thermo', u'mech', u'rel', u'elec']

The ordered container interface provides a fairly low level -- but powerful --
method to change the order:

  >>> physics.updateOrder([u'mech', u'elec', u'thermo', u'rel'])
  >>> physics.keys()
  [u'mech', u'elec', u'thermo', u'rel']

The requirement interface provides another high-level method for sorting. It
allows you to specify a new position for a given name:

  >>> physics.changePosition(u'elec', 2)
  >>> physics.keys()
  [u'mech', u'thermo', u'elec', u'rel']

  >>> physics.changePosition(u'rel', 1)
  >>> physics.keys()
  [u'mech', u'rel', u'thermo', u'elec']

Now, the order of physics requirement purposefully does not change the order
of the college physics requirement and vice versa:

  >>> college_physics.keys()
  [u'thermo', u'mech', u'rel', u'elec', u'quant']

  >>> college_physics.changePosition(u'mech', 0)
  >>> college_physics.changePosition(u'elec', 2)
  >>> college_physics.changePosition(u'quant', 3)
  >>> college_physics.keys()
  [u'mech', u'thermo', u'elec', u'quant', u'rel']

  >>> physics.keys()
  [u'mech', u'rel', u'thermo', u'elec']

There are many more high-level ordering functions that could be provided. But
we wanted to keep the ``IRequirement`` interface a simple as possible and the
idea is that you can implement adapters that use the ``updateOrder()`` method
to provide high-level ordering APIs if desired.


Overriding Requirements
~~~~~~~~~~~~~~~~~~~~~~~

Now let's have a look at a case where the more specific requirement overrides
the a dependency requirement of one of its bases. First we create a global
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


Complex Inheritance Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__Note__: You probably want to skip this section, if you read this file for
          the first time. It is not important for your understanding of the
          package.

Requirement inheritance can be very complex. The following section tests for
those complex cases and ensures that they are working correctly. Let's first
setup a 3-level requirement path:

  >>> animal = requirement.Requirement(u'Animal')
  >>> dog = requirement.Requirement(u'Dog', animal)
  >>> hound = requirement.Requirement(u'Hound', dog)

  >>> animal.keys()
  []
  >>> dog.keys()
  []
  >>> hound.keys()
  []

  >>> animal[u'categories'] = requirement.Requirement(u'Categories')

  >>> animal.keys()
  [u'categories']
  >>> dog.keys()
  [u'categories']
  >>> hound.keys()
  [u'categories']

Now, one of the tricky parts is to get the key management done correctly, when
a base higher-up is added or removed.

  >>> lifeform = requirement.Requirement(u'Lifeform')
  >>> lifeform[u'characteristics'] = requirement.Requirement(u'Characteristics')

  >>> animal.addBase(lifeform)
  >>> lifeform.keys()
  [u'characteristics']
  >>> animal.keys()
  [u'categories', u'characteristics']
  >>> dog.keys()
  [u'categories', u'characteristics']
  >>> hound.keys()
  [u'categories', u'characteristics']

  >>> animal.removeBase(lifeform)
  >>> lifeform.keys()
  [u'characteristics']
  >>> animal.keys()
  [u'categories']
  >>> dog.keys()
  [u'categories']
  >>> hound.keys()
  [u'categories']

Another case is where you have multiple bases and two or more bases have a
requirement with the same name. In this case the name should still be only
listed once and the first listed base's value is chosen.

  >>> mamal = requirement.Requirement(u'Mamal')
  >>> mamal[u'categories'] = requirement.Requirement(u'Categories')

  >>> dog.addBase(mamal)
  >>> dog.keys()
  [u'categories']
  >>> hound.keys()
  [u'categories']

  >>> dog.values()
  [InheritedRequirement(Requirement(u'Categories'))]
  >>> dog[u'categories'].original is animal[u'categories']
  True
  >>> dog[u'categories'].original is mamal[u'categories']
  False

  >>> dog.removeBase(animal)
  >>> dog.keys()
  [u'categories']
  >>> hound.keys()
  [u'categories']

  >>> dog.values()
  [InheritedRequirement(Requirement(u'Categories'))]
  >>> dog[u'categories'].original is animal[u'categories']
  False
  >>> dog[u'categories'].original is mamal[u'categories']
  True

Finally, let's make sure that when getting a value, it is wrapped with
inherited requirement wrappers for every level of inheritance:

  >>> mamal[u'categories']
  Requirement(u'Categories')
  >>> dog[u'categories']
  InheritedRequirement(Requirement(u'Categories'))
  >>> hound[u'categories']
  InheritedRequirement(InheritedRequirement(Requirement(u'Categories')))

A simple helper function is used to unwrap requirements:

  >>> requirement.unwrapRequirement(mamal[u'categories'])
  Requirement(u'Categories')
  >>> requirement.unwrapRequirement(dog[u'categories'])
  Requirement(u'Categories')
  >>> requirement.unwrapRequirement(hound[u'categories'])
  Requirement(u'Categories')


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

  >>> from decimal import Decimal
  >>> from schooltool.requirement import scoresystem
  >>> check = scoresystem.DiscreteValuesScoreSystem(
  ...    u'Check', u'Check-mark score system',
  ...    [('+', Decimal(1)), ('v', Decimal(0)), ('-', Decimal(-1))])

The first and second arguments of the constructor are the title and
description. The third argument is a list that really represents a mapping
from the score to the numerical equivalent. Providing a numerical value is
necessary to conduct automated statistics and grade computations. Also, we are
purposefully not passing in a dictionary, so that the order of the items is
retained, which is important for user interface purposes. There are a handful
of methods associated with a score system. First, you can ask whether a
particular score is valid:

  >>> check.isValidScore('+')
  True
  >>> check.isValidScore('f')
  False

There is also a global "unscored" score that can be used when assigning
scores:

  >>> check.isValidScore(scoresystem.UNSCORED)
  True

Next, you can ask the score system to tell you the numerical value for a given
score:

  >>> check.getNumericalValue('+')
  Decimal("1")

Again, the unscored score returns a ``None`` result:

  >>> check.getNumericalValue(scoresystem.UNSCORED) is None
  True

We can also ask for the fractional value of a score. This is based on the
range of scores:

  >>> check.getFractionalValue('+')
  Decimal("1")
  >>> check.getFractionalValue('v')
  Decimal("0.5")
  >>> check.getFractionalValue('-')
  Decimal("0")

When a user inputs a grade, it is always a string value. Thus there is a
method that allows us to convert unicode string representations of the score
to a valid score.

  >>> check.fromUnicode('+')
  '+'
  >>> check.fromUnicode('f')
  Traceback (most recent call last):
  ...
  ValidationError: 'f' is not a valid score.

Empty strings are converted to the unscored score:

  >>> check.fromUnicode('') is scoresystem.UNSCORED
  True

The fourth method is there to check whether a score is a passing score.

  >>> check.isPassingScore('+') is None
  True

The result of this query is ``None``, because we have not defined a passing
score yet. This is optional, since not in every case the decision of whether
something is a passing score or not makes sense. If we initialize the score
system again -- this time providing a minimum passing grade -- the method will
provide more useful results:

  >>> from schooltool.requirement import scoresystem
  >>> check = scoresystem.DiscreteValuesScoreSystem(
  ...    u'Check', u'Check-mark score system',
  ...    [('+', Decimal(1)), 
  ...     ('v', Decimal(0)), 
  ...     ('-', Decimal(-1))], 
  ...     minPassingScore='v')
  >>> check
  <DiscreteValuesScoreSystem u'Check'>

  >>> check.isPassingScore('+')
  True
  >>> check.isPassingScore('v')
  True
  >>> check.isPassingScore('-')
  False

Unscored returns a neutral result:

  >>> check.isPassingScore(scoresystem.UNSCORED) is None
  True

Finally, you can query the score system for the best score:

  >>> check.getBestScore() is None
  True

You receive ``None``, because you did not specify a maximum score yet. You
might think that this is unnecessary, since you specified numerical values,
but sometimes two scores might have the same numerical values and explicit is
better than implicit anyways:

  >>> from schooltool.requirement import scoresystem
  >>> check = scoresystem.DiscreteValuesScoreSystem(
  ...    u'Check', u'Check-mark score system',
  ...    [('+', Decimal(1)), ('v', Decimal(0)), ('-', Decimal(-1))],
  ...    bestScore='+', minPassingScore='v')

  >>> check.getBestScore()
  '+'

The package also provides some default score systems. Since those score
systems are global ones, they reduce very efficiently for pickling.

- A simple Pass/Fail score system:

  >>> scoresystem.PassFail
  <GlobalDiscreteValuesScoreSystem u'Pass/Fail'>
  >>> scoresystem.PassFail.__reduce__()
  'PassFail'
  >>> scoresystem.PassFail.title
  u'Pass/Fail'
  >>> scoresystem.PassFail.scores
  [(u'Pass', Decimal("1")), (u'Fail', Decimal("0"))]
  >>> scoresystem.PassFail.isValidScore('Pass')
  True
  >>> scoresystem.PassFail.isPassingScore('Pass')
  True
  >>> scoresystem.PassFail.isPassingScore('Fail')
  False
  >>> scoresystem.PassFail.getBestScore()
  u'Pass'
  >>> scoresystem.PassFail.fromUnicode(u'Pass')
  u'Pass'
  >>> scoresystem.PassFail.getNumericalValue(u'Pass')
  Decimal("1")
  >>> scoresystem.PassFail.getFractionalValue(u'Pass')
  Decimal("1")
  >>> scoresystem.PassFail.getFractionalValue(u'Fail')
  Decimal("0")

- The standard American letter score system:

  >>> scoresystem.AmericanLetterScoreSystem
  <GlobalDiscreteValuesScoreSystem u'Letter Grade'>
  >>> scoresystem.AmericanLetterScoreSystem.__reduce__()
  'AmericanLetterScoreSystem'
  >>> scoresystem.AmericanLetterScoreSystem.title
  u'Letter Grade'
  >>> scoresystem.AmericanLetterScoreSystem.scores
  [('A', Decimal("4")), ('B', Decimal("3")), ('C', Decimal("2")), 
   ('D', Decimal("1")), ('F', Decimal("0"))]
  >>> scoresystem.AmericanLetterScoreSystem.isValidScore('C')
  True
  >>> scoresystem.AmericanLetterScoreSystem.isValidScore('E')
  False
  >>> scoresystem.AmericanLetterScoreSystem.isPassingScore('D')
  True
  >>> scoresystem.AmericanLetterScoreSystem.isPassingScore('F')
  False
  >>> scoresystem.AmericanLetterScoreSystem.getBestScore()
  'A'
  >>> scoresystem.AmericanLetterScoreSystem.fromUnicode('B')
  'B'
  >>> scoresystem.AmericanLetterScoreSystem.getNumericalValue('B')
  Decimal("3")
  >>> scoresystem.AmericanLetterScoreSystem.getFractionalValue('B')
  Decimal("0.75")
  >>> scoresystem.AmericanLetterScoreSystem.getFractionalValue('F')
  Decimal("0")
 
- The extended American letter score system:

  >>> scoresystem.ExtendedAmericanLetterScoreSystem
  <GlobalDiscreteValuesScoreSystem u'Extended Letter Grade'>
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.__reduce__()
  'ExtendedAmericanLetterScoreSystem'
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.title
  u'Extended Letter Grade'
  >>> [s for s, v in scoresystem.ExtendedAmericanLetterScoreSystem.scores]
  ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isValidScore('B-')
  True
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isValidScore('E')
  False
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isPassingScore('D-')
  True
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.isPassingScore('F')
  False
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.getBestScore()
  'A+'
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.fromUnicode('B-')
  'B-'
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.getNumericalValue('B')
  Decimal("3.0")
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.getFractionalValue('A')
  Decimal("1")
  >>> scoresystem.ExtendedAmericanLetterScoreSystem.getFractionalValue('A+')
  Decimal("1")

The second score system class is the ranged values score system, which allows
you to define numerical ranges as grades. Let's say I have given a quiz that
has a maximum of 21 points:

  >>> quizScore = scoresystem.RangedValuesScoreSystem(
  ...     u'Quiz Score', u'Quiz Score System', Decimal(0), Decimal(21))
  >>> quizScore
  <RangedValuesScoreSystem u'Quiz Score'>

Again, the first and second arguments are the title and description. The third
and forth arguments are the minum and maximum value of the numerical range. by
default the minimum value is 0, so I could have skipped that argument and just
provide a ``max`` keyword argument.

Practically any numerical value in the range between the minimum and maximum
value are valid scores:

  >>> quizScore.isValidScore(Decimal(-1))
  False
  >>> quizScore.isValidScore(Decimal(0))
  True
  >>> quizScore.isValidScore(Decimal("13.43"))
  True
  >>> quizScore.isValidScore(Decimal(21))
  True
  >>> quizScore.isValidScore(Decimal("21.1"))
  False
  >>> quizScore.isValidScore(scoresystem.UNSCORED)
  True

Clearly, for this type of score system, the numerical value always equals the
score itself:

  >>> quizScore.getNumericalValue(Decimal(20))
  Decimal("20")
  >>> quizScore.getNumericalValue(Decimal('20.1'))
  Decimal("20.1")

We can also determine the fractional value:

  >>> quizScore.getFractionalValue(Decimal(20))
  Decimal("0.9523809523809523809523809524")
  >>> quizScore.getFractionalValue(Decimal(0))
  Decimal("0")

We can also convert any unicode input to a score.

  >>> quizScore.fromUnicode('20')
  Decimal("20")
  >>> quizScore.fromUnicode('20.1')
  Decimal("20.1")

Note that non-integer values will always be converted to the decimal type,
since float does not have an exact precision. Since the best score for the
ranged value score system is well-defined by the maximum value, we can get a
answer any time:

  >>> quizScore.getBestScore()
  Decimal("21")

Since we have not defined a minimum passing grade, we cannot get a meaningful
answer from the passing score evaluation:

  >>> quizScore.isPassingScore(Decimal(13)) is None
  True

Again, if we provide a passing score at the beginning, then those queries make
sense:

  >>> quizScore = scoresystem.RangedValuesScoreSystem(
  ...     u'quizScore', u'Quiz Score System', 
  ...     Decimal(0), Decimal(21), Decimal("0.6")*21) # 60%+ is passing

  >>> quizScore.isPassingScore(Decimal(13))
  True
  >>> quizScore.isPassingScore(Decimal(10))
  False
  >>> quizScore.isPassingScore(scoresystem.UNSCORED) is None
  True

Let's also try a ranged system that doesn't start at 0:

  >>> quizScore = scoresystem.RangedValuesScoreSystem(
  ...     u'quizScore', u'Score System that does not start at zero', 
  ...     Decimal(5), Decimal(10))
  >>> quizScore.getFractionalValue(Decimal(5))
  Decimal("0")
  >>> quizScore.getFractionalValue(Decimal(10))
  Decimal("1")
  >>> quizScore.getFractionalValue(Decimal("7.5"))
  Decimal("0.5")

The package provides two default ranged values score system, the percent
score system,

  >>> scoresystem.PercentScoreSystem
  <GlobalRangedValuesScoreSystem u'Percent'>
  >>> scoresystem.PercentScoreSystem.__reduce__()
  'PercentScoreSystem'
  >>> scoresystem.PercentScoreSystem.title
  u'Percent'
  >>> scoresystem.PercentScoreSystem.min
  Decimal("0")
  >>> scoresystem.PercentScoreSystem.max
  Decimal("100")

  >>> scoresystem.PercentScoreSystem.isValidScore(Decimal(40))
  True
  >>> scoresystem.PercentScoreSystem.isValidScore(scoresystem.UNSCORED)
  True

  >>> scoresystem.PercentScoreSystem.isPassingScore(Decimal(60))
  True
  >>> scoresystem.PercentScoreSystem.isPassingScore(Decimal(59))
  False
  >>> scoresystem.PercentScoreSystem.isPassingScore(scoresystem.UNSCORED)

  >>> scoresystem.PercentScoreSystem.getBestScore()
  Decimal("100")
  >>> scoresystem.PercentScoreSystem.fromUnicode('42')
  Decimal("42")
  >>> scoresystem.PercentScoreSystem.getNumericalValue(Decimal(42))
  Decimal("42")
  >>> scoresystem.PercentScoreSystem.getFractionalValue(Decimal(42))
  Decimal("0.42")

and the "100 points" score system:

  >>> scoresystem.HundredPointsScoreSystem
  <GlobalRangedValuesScoreSystem u'100 Points'>
  >>> scoresystem.HundredPointsScoreSystem.__reduce__()
  'HundredPointsScoreSystem'
  >>> scoresystem.HundredPointsScoreSystem.title
  u'100 Points'
  >>> scoresystem.HundredPointsScoreSystem.min
  Decimal("0")
  >>> scoresystem.HundredPointsScoreSystem.max
  Decimal("100")

  >>> scoresystem.HundredPointsScoreSystem.isValidScore(Decimal(40))
  True
  >>> scoresystem.HundredPointsScoreSystem.isValidScore(scoresystem.UNSCORED)
  True

  >>> scoresystem.HundredPointsScoreSystem.isPassingScore(Decimal(60))
  True
  >>> scoresystem.HundredPointsScoreSystem.isPassingScore(Decimal(59))
  False
  >>> scoresystem.HundredPointsScoreSystem.isPassingScore(scoresystem.UNSCORED)

  >>> scoresystem.HundredPointsScoreSystem.getBestScore()
  Decimal("100")
  >>> scoresystem.HundredPointsScoreSystem.fromUnicode('42')
  Decimal("42")
  >>> scoresystem.HundredPointsScoreSystem.getNumericalValue(Decimal(42))
  Decimal("42")
  >>> scoresystem.HundredPointsScoreSystem.getFractionalValue(Decimal(42))
  Decimal("0.42")

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
  >>> ev = evaluation.Evaluation(req[u'iter'], pf, 'Pass', teacher)
  >>> ev.requirement
  InheritedRequirement(Requirement(u'Create an iterator.'))
  >>> ev.scoreSystem
  <GlobalDiscreteValuesScoreSystem u'Pass/Fail'>
  >>> ev.value
  'Pass'
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
  [<Evaluation for In...nt(Requirement(u'Create an iterator.')), value='Pass'>]

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
  ...     calculus[u'int'][u'fourier'], pf, 'Fail', teacher2))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'int'][u'path'], pf, 'Pass', teacher2))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'diff'][u'partial'], pf, 'Fail', teacher))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'diff'][u'systems'], pf, 'Pass', teacher))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'limit'], pf, 'Fail', teacher))

  >>> evals.addEvaluation(evaluation.Evaluation(
  ...     calculus[u'fundamental'], pf, 'Pass', teacher2))

So now we can ask for all evaluations for which the sample teacher is the
evaluator:

  >>> teacherEvals = evals.getEvaluationsOfEvaluator(teacher)
  >>> teacherEvals
  <Evaluations for Person(u'Student Two')>

  >>> [value for key, value in sorted(
  ...     teacherEvals.items(), key=lambda x: x[1].requirement.title)]
  [<Evaluation for Requirement(u'Limit Theorem'), value='Fail'>,
   <Evaluation for Requirement(u'Partial Differential Equations'), value='Fail'>,
   <Evaluation for Requirement(u'Systems'), value='Pass'>]

As you can see, the query method returned another evaluations object having the
student as a parent.  It is very important that the evaluated object is not
lost.  The big advantage of returning an evaluations object is the ability to
perform chained queries:

  >>> result = evals.getEvaluationsOfEvaluator(teacher) \
  ...               .getEvaluationsForRequirement(calculus[u'diff'])
  >>> [value for key, value in sorted(
  ...     result.items(), key=lambda x: x[1].requirement.title)]
  [<Evaluation for Requirement(u'Partial Differential Equations'), value='Fail'>,
   <Evaluation for Requirement(u'Systems'), value='Pass'>]

By default, these queries search recursively through the entire subtree of the
requirement.  However, you can call turn off the recursion:

  >>> result = evals.getEvaluationsOfEvaluator(teacher) \
  ...               .getEvaluationsForRequirement(calculus, recurse=False)
  >>> sorted(result.values())
  [<Evaluation for Requirement(u'Limit Theorem'), value='Fail'>]

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
  [<Evaluation for Requirement(u'Systems'), value='Pass'>]


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
  ...       evaluation.Evaluation(calculus[u'limit'], pf, 'Pass', teacher)),
  ...      (calculus[u'diff'],
  ...       evaluation.Evaluation(calculus[u'diff'], pf, 'Fail', teacher))]
  ...     )

- ``__getitem__(key)``

  >>> evals[calculus[u'limit']]
  <Evaluation for Requirement(u'Limit Theorem'), value='Pass'>
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
  ...     calculus[u'limit'], pf, 'Pass', teacher)
  >>> len(evals._btree)
  2

- ``get(key, default=None)``

  >>> evals.get(calculus[u'limit'])
   <Evaluation for Requirement(u'Limit Theorem'), value='Pass'>
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
  [<Evaluation for Requirement(u'Differentiation'), value='Fail'>,
   <Evaluation for Requirement(u'Limit Theorem'), value='Pass'>]

- ``items()``

  >>> sorted(evals.items(), key=lambda x: x[0].title)
  [(Requirement(u'Differentiation'),
    <Evaluation for Requirement(u'Differentiation'), value='Fail'>),
   (Requirement(u'Limit Theorem'),
    <Evaluation for Requirement(u'Limit Theorem'), value='Pass'>)]

- ``__len__()``

  >>> len(evals)
  2
