##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""This module is DEPRECATED. Don't use it!

$Id: type.py,v 1.13 2004/03/30 22:01:34 jim Exp $
"""
__metaclass__ = type # All classes are new style when run with Python 2.2+

import zope.interface
import types
from zope.interface import providedBy, implements, Interface
from zope.interface.interfaces import IInterface

class ITypeRegistry(Interface):
    """Type-specific registry

    This registry stores objects registered for objects that implement
    a required interface.
    """

    def register(interface, object):
        """Register an object for an interface.

        The interface argument may be None.  This effectively defines a
        default object.
        """

    def unregister(interface):
        """Remove the registration for the given interface

        If nothing is registered for the interface, the call is ignored.
        """

    def get(interface, default=None):
        """Return the object registered for the given interface.
        """

    def getAll(implements):
        """Get registered objects

        Return a sequence of all objects registered with interfaces
        that are extended by or equal to one or more interfaces in the
        given interface specification.

        Objects that match more specific interfaces of the specification
        come before those that match less specific interfaces, as per
        the interface resolution order described in the flattened() operation
        of IInterfaceSpecification.
        """

    def getAllForObject(object):
        """Get all registered objects for types that object implements.
        """

    def getTypesMatching(interface):
        """Get all registered interfaces matching the given interface

        Returns a sequence of all interfaces registered that extend
        or are equal to the given interface.
        """

    def __len__():
        """Returns the number of distinct interfaces registered.
        """

class TypeRegistry:

    implements(ITypeRegistry)

    # XXX This comment doesn't seem to be correct, because the mapping is
    # from interface -> object.  There are no tuples that I see.  Also,
    # I'm not sure what the last sentence is trying to say :-).

    # The implementation uses a mapping:
    #
    #  { (required, provided) -> (registered_provided, component) }
    #
    # Where the registered provides is what was registered and
    # provided may be some base interface

    def __init__(self, data=None):
        if data is None:
            data = {}

        self._reg = data

    def register(self, interface, object):
        if not (interface is None or IInterface.providedBy(interface)):
            if isinstance(interface, (type, types.ClassType)):
                interface = zope.interface.implementedBy(interface)
            else:
                raise TypeError(
                    "The interface argument must be an interface (or None)")
        
        self._reg[interface] = object
        
    def unregister(self, interface):
        if interface is None or IInterface.providedBy(interface):
            if interface in self._reg:
                del self._reg[interface]
        else:
            raise TypeError(
                "The interface argument must be an interface (or None)")

    def get(self, interface, default=None):
        """
        Finds a registered component that provides the given interface.
        Returns None if not found.
        """
        return self._reg.get(interface, default)

    def setdefault(self, interface, default=None):
        return self._reg.setdefault(interface, default)

    def getAll(self, interface_spec):
        result = []
        for interface in interface_spec.flattened():
            object = self._reg.get(interface)
            if object is not None:
                result.append(object)

        if interface_spec is not None:
            object = self._reg.get(None)
            if object is not None:
                result.append(object)

        return result

    def getAllForObject(self, object):
        # XXX This isn't quite right, since it doesn't take into
        # account implementation registries for objects that can't
        # have '__implements__' attributes.
        return self.getAll(providedBy(object))

    def getTypesMatching(self, interface):
        if interface is None:
            return self._reg.keys()

        result = []
        for k in self._reg:
            if k is None or k.extends(interface, False):
                result.append(k)
        return result

    def __len__(self):
        return len(self._reg)
