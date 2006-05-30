SchoolTool Security Policy
==========================

SchoolTool does not use the default Zope 3 security policy, but implements
a custom one.

The most important difference from the default policy is that we do not have
the three-tier group-role-permission model (i.e, a principal can belong to a
group, roles can be assigned to a group or a principal, and permissions can be
assigned to a role).  Instead, we have a two-tier crowd-permission model.

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

In Python code, a crowd is an adapter which adapts a context object to ICrowd.
The ICrowd interface only includes one method: contains(principal).
The context object is the object that we want to access.  A crowd could look
like this:

    >>> from schooltool.securitypolicy.crowds import Crowd
    >>> class OwnerCrowd(Crowd):
    ...     #adapts(IOwnedObject)
    ...     def contains(self, principal):
    ...         owner = self.context.owner
    ...         return owner == principal


Registering crowds
------------------

Crowds are registered in ZCML using the <crowd> directive, like this:

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
in ZCML like this:

  <security:allow
      interface="schooltool.app.interfaces.ISchoolToolApplication"
      crowds="owner managers clerks"
      permission="schooltool.edit" />

The set of objects that should be adaptable by the crowds are specified by
interface.  The `crowds` attribute provides a list of crowds to be checked
against.  If any of the crowds includes the accessing principal, permission
is granted, otherwise it is denied.

TODO: no interface specified


Inheriting permissions
----------------------

TODO
