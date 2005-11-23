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

  >>> program = requirement.GroupRequirement(u'Programming')
  >>> program
  GroupRequirement(u'Programming')

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

  >>> pyprogram = requirement.GroupRequirement(
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
  [GroupRequirement(u'Programming')]

  >>> pyprogram.removeBase(program)
  >>> sorted(pyprogram.keys())
  [u'iter']

  >>> pyprogram.addBase(program)
  >>> sorted(pyprogram.keys())
  [u'forloop', u'iter']

Let's now look at a more advanced case. Let's say that the state of Virginia
requires all students to take a progrramming class that fulfills the
programming requirement:

  >>> va = requirement.GroupRequirement(u'Virginia')
  >>> va[u'program'] = program

Now, Yorktown High School (which is in Virginia) teaches Python and thus
requires the Python requirement. However, Yorktown HS must still fulfill the
state requirement:

  >>> yhs = requirement.GroupRequirement(u'Yorktow HS', va)
  >>> sorted(yhs[u'program'].keys())
  [u'forloop']

  >>> yhs[u'program'][u'iter'] = requirement.Requirement(u'Create an iterator.')

  >>> sorted(yhs[u'program'].keys())
  [u'forloop', u'iter']

  >>> sorted(va[u'program'].keys())
  [u'forloop']

Another trickky case is when the basse is added later:

  >>> yhs = requirement.GroupRequirement(u'Yorktow HS')
  >>> yhs[u'program'] = requirement.GroupRequirement(u'Programming')
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
  GroupRequirement(u'Computer Science')

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
