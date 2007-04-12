The Design of the Demographics Package
======================================

Not a doctest
-------------

This document is not a doctest. This has a reason: the demographics
functionality does not contain a lot of algorithmic or API-heavy code,
but is mostly an exercise in integration of existing packages without
the introduction of much that is new in the way of APIs.

What the demographics package does
----------------------------------

The demographics package takes care of person-specific data, for
example information about the name of the person (INameInfo), or
contact information for a person. These different informational
aspects are presented in a menu of "tabs" on the top of the screen
when viewing or editing a person.

The demographics package has facilities to display this information in
a browsable, batched table form.

The demographics package also has a facility to index this information
so that it can be searched. Search results can be browsed.

Design
------

The person class is subclassed from
``demographics.person.person.Person``. New data is added to the person
class using dumb data objects that implement schemas. These data
objects need to have a location, as they will have their own views
attached to them. This is managed in
``schooltool.demographics.person``.  The schemas are defined in
``schooltool.demographics.interfaces``.

Formlib-driven edit and display forms are hooked up to the dumb data
classes. This is managed in
``schooltool.demographics.browser.personform``.

The container (IPersonContainer) has attached to it with a
``zc.table`` driven view. This view defines the columns visible in the
table (including sortability of such columns). This is arranged in
``schooltool.demographics.browser.table``.

The container also has a search page attached to it. The catalog and
its indexes are defined in ``schooltool.demographics.utility``. Also
there is the implementation of the ``ISearch`` interface, which
provides the data that is cataloged. The search screen itself is in
``schooltool.demographics.browser.table``.

Customizability
---------------

The demographics package tries to be friendly to customization. If a
customization of schooltool wants to install a different Person
subclass, it can do so by setting up a different PersonFactory
utility. See ``utility.py`` for how the demographics package does it.

Tricky bits
-----------

In general some of the tricky bits have to do with the rendering of
things in the context of the parent, not the attribute. This is a
drawback of the composition approach in this case. The
``actualContext`` method on views -- informs the view code to use a
different context object for the rendering of the action menu (usually
``__parent__``).

The ``schooltool.demographics.browser.personform.AttributeMenu`` not
only shows the menu in the context of the parent object, but also
creates different relative links for each different object that's
participating in the menu (in this case, different persons). It also
highlights the menu we're currently looking at.

The add form in ``schooltool.demographics.browser.personform`` is
based on the add form in ``schooltool.person.browser``, but adds an
extra required field to it (last_name).

In defense of composition
-------------------------

The demographics package chooses subclassing and composition to add
new information items to person objects. Compared to a strategy using
annotations, or a strategy using a single object implementing multiple
schemas (INameInfo, ISchoolData, etc) this has various benefits and
drawbacks. Advantages of the attribute strategy are:

* It supports extensibility and customizability using subclassing. A
  subclass can create a new person object with different or added
  attributes. This is a familiar Python pattern. 

* Annotations allow doing this without subclassing. If the same
  information needs to be added multiple times to a person object
  (which is the case for contact information, which exists for both
  parents and three emergencies), this becomes more cumbersome than
  with the use of attributes.

* It's easy to reuse both data storage *and* views in subclasses
  without having to re-register views in ZCML, as the views are on the
  attributes. Annotations allow the reuse of data storage but views
  would need to be reregistered.

* There is less chance of nameclashes than if Person object
  implemented all the interfaces directly.

* Attributes allow for high-speed access without the need for an
  adapter looking as is the case for annotations. This can be
  important to reduce overhead in tabular presentation of thousands of
  persons. (is verified by eyeball-test only)

* Annotations are attractive as no existing code needs to be changed
  to store new data on an object. Taking into account the presentation
  of this information in tabular browsing, or the indexing of this
  information in a catalog, implies a lot of knowledge of this data
  needs to exist in the codebase anyway. This means the benefits of
  using annotations in part go away.

Of course there are also valid arguments to be made for the use of
annotations, or for the storage of all the attributes on the person
object itself. It is as usual in software a matter of tradeoffs. In my
(Martijn's) opinion however, given these arguments, the attributes
approach seems a reasonable one to at least try out in the
demographics package.
