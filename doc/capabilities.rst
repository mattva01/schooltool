=========================
Capability based security
=========================

Glossary
--------

:capability:
  A wrapper around an object that intercepts access to attributes, and
  either allows access or forbids access.
  A capability also needs to ensure that (except in special cases) any
  attributes returned from the object are also wrapped with capabilities.

:capability tag:
  A string that represents a "class" of capability.
  This isn't a python class, but rather a classification.

Abstract model
--------------

A capabilities based system works like this:

1. A request comes into the system
2. The system inspects the request, and chooses a root capability.
   Any value returned from that root capability will also be a capability.

There are N webs of capabilities. Each web has a root. The webs may overlap
or be interconnected.
There are no principals or permissions or roles or groups. Different requests
may get different points of access into the interconnected web, depending on
the nature of the request.


Concrete model
--------------

This differs from the abstract model:

* We categorise requests into Principals. Usually this is done by looking at
  the authentication data of the request.
* There is just one root object. Different principals have access to
  different capabilities of the root object.
* There is just one "core" web of objects. Objects are associated with
  capabilities, either by the object instance, or by an object's class, or
  from a principal.
* Accessing a capability will return either a capability or a "rock".
  A rock is an immutable object that needs no capability.

The capabilities available for an object are categorised by a "capability
tag". This is a string that represents the ability to do something.
In a typical system, capability tags represent combinations of
Create, Retrieve, Update, Delete. So, the available tags are
  C R U D CR CU CD RU RD UD CRU CRD CUD RUD CRUD.
In practice, the most commonly useful tags are
  R CR CRU CRUD
However, I can think of particular systems where each of the possible tags
is useful.

A request comes into the system. The system matches the request to a
Principal. The system chooses an appropriate capability for the root object,
based on the capabilities available on the root object and the principal,
and the tags owned by the principal that are pertinent to the root object.


Dangling references
-------------------

There is a danger of dangling references. This is unimportant in the case of
capabilities stored on objects. This is handled when capabilities are stored
on the principal because in schooltool capabilities are installed in a
principal as a consequence of relationships, and are removed when the
relationship is broken.


Attribute access
----------------

Let's say we have an object O that is wrapped in a capability CO.
I want to get an attribute named 'foo' from CO.

1. Client code says: myfoo = CO.foo
2. CO either allows or forbids access to 'foo'.
   If access is forbidden, CO raises ForbiddenAttribute.
3. CO gets 'foo' from O: V = O.foo
4. If the type(V) is in the list of Rocks, CO returns V.
   The type Capability is in the list of Rocks.
5. Otherwise, CO must get a capability for V. This might be a
   capability that already exists and already wraps V.
   It might be a factory that creates an appropriate capability for V.
   CO searches for an appropriate capability. If it finds one, this is
   returned. Otherwise...
   What to do otherwise? Perhaps return an Incapable Capability for V.
   Perhaps raise some kind of error.


The search
----------

A capability can be looked for

  - on the principal, and things implied by the principal such as roles,
    groups, facets, etc.
  - on the returned value itself
  - looked up by the returned value's type in a registry

Let's call the capability that was accessed by client code (and is responsible
for ensuring that a returned value is wrapped) the "mediating capability".

The mediating capability can influence which of returned object's capabilities
is chosen, through a table on the mediating capability:

:predicate: capability tag

(Note, the table is on the mediating capability, not on the mediating
capability's object.)

Thus, we can get a different capability by getting the same returned value
from one capability or from another:

  CO ---> x <--- CP

  CO.name = Cx1
  CP.name = Cx2

This can be thought of as a way of allowing, say, CP to "upgrade" access on
x if you already have a higher level of access on CP.



We have capability CO, object O, return value V.
We also have principal P, and a name "Name".

O may have a capabilities table. This is a table of

:capability tag: capability

A capability tag is a string. It is a bit like a permission, in permissions
based systems. However, it serves a different purpose here.
Typical capability tags in a RESTful system are based on the actions Create,
Retrieve, Update and Delete.

There is notionally a "current tag".

CO can provide a different tag than the current one, depending on the
Name, perhaps the type of object returned, or its interfaces.

:predicate: capability tag

Let's say I have an object that represents a collection of Registration Groups
in a school. A registration group is a group of pupils that need to meet
up with their tutor twice a day to have their attendance registered.
The Registration Groups Collection contains Registration Groups, which in
turn contain Pupils.

   RGC --->* RG --->* Pupil

Let's say I get the Retrieve capability of RGC. That capability's nextobject
tags table says:

:predicate: capability tag
:any: R

Now, let's say that I instead get the Retrieve+Update (RU) capability of RGC.
That capability's nextobject tags table says:

:predicate: capability tag
:Value implements IRegistrationGroup: RU
:any: R

So, any next object returned from RGS that implements IRegistrationGroup will
have its RU tag used. Any other object will have its R tag used.

If the returned object has no tag matching the tag chosen, another tag is
chosen.

The predicate may have included something about what name was used to get
the object. For example, __getitem__, getRelationships, etc.


When a request comes in, and traversal is started, the request is used to
determine an appropriate start object and start tag.
The start object is usually the root object. The start tag will be the same
for most users, but will be different for the super-user.


Storing objects
---------------

When we add a capability-wrapped object to a container, do we store the
capability, or do we store the underlying object?

The capability to add something to a group does either one or the other.
So, you might have a powerful capability that allows a container to remove
that capability from the object for you. You might have a less powerful
capability that can be stored as is, but not removed.

Also, a particularly special container's capability may be able to remove
capabilities for storage.


Dealing with descriptors
------------------------

When you call a method on an object, you are actually doing two things:

1. retrieving an attribute from the object
2. calling the descriptor that you get back

For example, consider this class:

  class Foo(object):
      def bar(self):
          return Foo()

Now, let's say we have an object f and a capability cf.

>>> f = Foo()
>>> cf = Capability(Foo)

When I call cf.bar(), I need to have cf provide a special kind of proxy for
the bound method that f.bar returns. This special proxy needs to remember
that it came from cf so that cf's nextobject tags table can still be used.
To avoid holding onto too many references, the special proxy should just take
cf's tags table.
