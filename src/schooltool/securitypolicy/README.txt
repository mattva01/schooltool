SchoolTool Security Policy
==========================

SchoolTool does not use the default Zope 3 security policy, but implements
a custom one.

The most important difference from the default policy is that we do not have
the three-tier group-role-permission model (i.e, a principal can belong to a
group, roles can be assigned to a group or a principal, and permissions can be
assigned to a role).  Instead, we have a two-tier crowd-permission model.

Notably local grants have also been removed, although it is easy to implement
similar functionality using crowds.

.. _Crowd:

Crowds
------

A crowd is somewhat like a group of principals.  While a group is an explicitly
enumerated set of principals (mathematically speaking, g={a,b,c,d}), a crowd is
a set of principals defined by a membership operation (mathematically speaking,
c={x | P(x)}.  The advantage of using crowds is that unlike groups, which are
static, crowds can also react to context objects.  For example, you could have
an 'owner' crowd which only includes the accessing principal if he is looking
at an object that 'belongs' to him.  Therefore, for different context objects
the same crowd could include different principals.


Implementing crowds
-------------------

In Python code, a crowd is an adapter which adapts a context object to
`ICrowd`. The `ICrowd` interface only includes one method:
``contains(principal)``. The context object is the object that we want to
access.  A crowd could look like this:

    >>> from schooltool.securitypolicy.crowds import Crowd
    >>> class OwnerCrowd(Crowd):
    ...     def contains(self, principal):
    ...         owner = self.context.owner
    ...         return owner == principal


Registering crowds
------------------

Crowds are registered in ZCML using the ``<crowd>`` directive, like this::

  <security:crowd
      name="owner"
      factory=".crowds.OwnerCrowd" />

(We are using the namespace http://schooltool.org/securitypolicy for the
security XML prefix.)

As you can see, the crowd is assigned an identifier which can later be used
in security declarations for objects.


Using crowds
------------

Just declaring a crowd is obviously not enough.  You also have to specify
which crowds have what permissions on which objects.  You can do this
in ZCML like this::

  <security:allow
      interface="schooltool.app.interfaces.ISchoolToolApplication"
      crowds="owner managers clerks"
      permission="schooltool.edit" />

The set of objects that should be adaptable by the crowds are specified by
interface.  The ``crowds`` attribute provides a list of crowd ids. If any of the
crowds includes the accessing principal, permission is granted, otherwise it is
denied.

You can have several ``<allow>`` directives for the same interface and
permission. In that case the lists of crowds will be summed.

In some cases it makes sense to provide a permission to a crowd no matter what
the context interface is.  In that case you can just leave the `interface`
attribute out, like this::

  <security:allow
      crowds="owner managers clerks"
      permission="schooltool.edit" />


Inheriting permissions
----------------------

It is sometimes not feasible to specify crowds for each and every object, and
the Zope3-style parent traversal would be handy.  This is particularly useful
for permissions on views, which typically have the context object as their
parent.  A limited form of such traversal has been implemented.

Basically, if no ``<allow>`` declaration (with an explicit interface) is found
for an object, the object's parent is taken (from the attribute `__parent__`).
If the parent does not have a matching ``<allow>`` declaration either, its
parent is taken, etc., until a matching declaration is found.  Note that at this
point the traversal upwards is not continued no matter whether the principal was
in the given crowds or not.

For example, imagine this structure::

  Application -> GroupContainer -> Group -> GroupView

Here, if one ``<allow>`` directive allowed access to the group container, but
another one disallowed access to the group, accessing `GroupView` would fail:

1. `GroupView` would be checked, no matching declarations would be found
2. Its parent `Group` would be checked, a matching declaration would be found.
3. The crowds in the declaration would be checked and access denied
4. There is no step 4.  Note that even though step 3 did not grant access,
   traversal to the parent is not continued.


Permission lookup order
-----------------------

Here is a brief summary of how a permission is checked:

1. All crowds for a permission (specified as ``<allow>`` directives without an
explicit interface) are checked.  If any one contains the principal, permit
access.

2. While an ``<allow>`` directive with an explicit interface is not found for the
context object, take the context's parent.

3. If the principal is in any of the crowds specified in the matching ``<allow>``
directive, permit access.

4. If neither of the previous steps permit access, deny.

(see ``schooltool.securitypolicy.policy.SchoolToolSecurityPolicy`` for the
implementation)
