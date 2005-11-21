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

  >>> list(program.keys())
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

  >>> list(pyprogram.keys())
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
  >>> list(pyprogram.keys())
  [u'iter']

  >>> pyprogram.addBase(program)
  >>> list(pyprogram.keys())
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
  >>> list(yhs[u'program'].keys())
  [u'forloop']

  >>> yhs[u'program'][u'iter'] = requirement.Requirement(u'Create an iterator.')

  >>> list(yhs[u'program'].keys())
  [u'forloop', u'iter']

  >>> list(va[u'program'].keys())
  [u'forloop']

Another trickky case is when the basse is added later:

  >>> yhs = requirement.GroupRequirement(u'Yorktow HS')
  >>> yhs[u'program'] = requirement.GroupRequirement(u'Programming')
  >>> yhs[u'program'][u'iter'] = requirement.Requirement(u'Create an iterator.')

  >>> yhs.addBase(va)
  >>> list(yhs[u'program'].keys())
  [u'forloop', u'iter']

  >>> yhs[u'program'][u'iter']
  Requirement(u'Create an iterator.')

  >>> yhs[u'program'][u'forloop']
  InheritedRequirement(Requirement(u'Write a for loop.'))

We can also delete requirements from the groups. However, we should only be
able to delete locally defined requirements and not inherited ones:

  >>> del yhs[u'program'][u'iter']
  >>> list(yhs[u'program'].keys())
  [u'forloop']

  >>> del yhs[u'program'][u'forloop']
  Traceback (most recent call last):
  ...
  KeyError: u'forloop'