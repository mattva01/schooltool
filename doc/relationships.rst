Relationships
=============

Overview
--------

XXX This "overview" is a mess!

* relationships create arbitrary links between objects

* valencies are constraints that relationships may exist

* never see a relationship as such, only links
XXX Fragment.

* links are traversable, semantics given by a role

* roles described by URIs. In python, interfaces that extend SpecificURI.
XXX Fragment.

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

:Relationship:

:URI:

:Interface:

:SpecificURI:
