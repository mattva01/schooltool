===============
System metaphor
===============

* xp version is that when working on this for a particular school system,
  that school system should be the metaphor.

* when working on the framework, we need a different kind of metaphor
  to help communicate the design and its decisions to other programmers.
  this metaphor is "the Internet", or rather, certain parts and aspects
  of it.

  We're interested in the smart "ends" and the generic "middle".
  See "A World of Ends"


==================
Recurring patterns
==================

Containment / locations
-----------------------

Using __parent__ and __name__ to express a location
(see zope.app.interfaces.ILocation).

Using __getitem__ and keys() and iterkeys() to express containment.
