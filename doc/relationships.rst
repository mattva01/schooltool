Relationships
=============

Overview
--------

* relationships making arbitrary links between objects

* constraints that relationships shall / should exist

* never see a relationship as such, only links

* links are traversable, semantics given by a role

* roles described by URIs. In python, interfaces that extend SpecificURI.

* URIs don't have a strong concept of implication / extension like interfaces
  do, so we'll agree not to use that for now.

* Relationships may imply a facet. For example, a person who is the Tutor
  of a registration class will receive a RegistratonClassTutor facet.

* Events are issued on making and breaking a relationship. These events are
  used for the management of facets, but can be used for other things.

(Idea: make event interfaces be SpecificURIs also perhaps.)

Glossary
--------

:Link:

:Relationship:

:URI:

:Interface:

:SpecificURI:
