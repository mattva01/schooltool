Relationships
=============

Overview
--------

Relationships are a way to establish a link between two relatively
independent objects.  The primary advantage of using relationships is
that when one object is deleted and its links are removed, the other
object's side of the link is removed as well, so no dangling references
remain.


Some facts:

* valencies are constraints that relationships may exist

* links are traversable, semantics provided by a role

* roles are described by URIs

* URIs don't have a strong concept of implication / extension like
  interfaces do, so we'll agree not to use that for now.

* Relationships may imply a facet. For example, a person who is the Tutor
  of a registration class will receive a RegistrationClassTutor facet.

* Events are issued on creating and breaking a relationship. These
  events are used for the management of facets, but can be used for
  other things as well.


Glossary
--------

:Link:
An object that reflects one side of a relationship.

:Relationship:
An object that has two links which have references to participating
objects.

:URI:
An interface that is derived from SpecificURI.
