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

$Id: implementor.py,v 1.9 2004/03/30 22:01:34 jim Exp $
"""
__metaclass__ = type # All classes are new style when run with Python 2.2+

from zope.interface import Interface, implements
from zope.interface.interfaces import IInterface


class IImplementorRegistry(Interface):
    """Implementor registry

    This registry stores objects registered to implement (or help
    implement) an interface. For example, this registry could be used
    to register utilities.

    The objects registered here don't need to be implementors. (They
    might just be useful to implementation.) What's important is that
    they are registered according to a provided interface.

    """

    def register(provide, object):
        """Register an object for a required and provided interface.

        There are no restrictions on what the object might be.
        Any restrictions (e.g. callability, or interface
        implementation) must be enforced by higher-level code.

        The require argument may be None.

        """

    def get(provides, default=None):
        """Return a registered object

        The registered object is one that was registered that provides an
        interface that extends or equals the 'provides' argument.

        """

    def getRegisteredMatching():
        """Return a sequence of two-tuples, each tuple consisting of:

        - interface

        - registered object

        One item is returned for each registration.

        """


class ImplementorRegistry:
    """Implementor-style interface registry
    """

    implements(IImplementorRegistry)

    # The implementation uses a mapping:
    #
    #  { provided -> (registered_provided, component) }
    #
    # Where the registered provides is what was registered and
    # provided may be some base interface

    def __init__(self, data=None):
        if data is None:
            data = {}
        self._reg = data

    def _registerAllProvided(self, primary_provide, object, provide):
        # Registers a component using (require, provide) as a key.
        # Also registers superinterfaces of the provided interface,
        # stopping when the registry already has a component
        # that provides a more general interface or when the Base is Interface.

        reg = self._reg
        reg[provide] = (primary_provide, object)
        bases = getattr(provide, '__bases__', ())
        for base in bases:
            if base is Interface:
                # Never register the say-nothing Interface.
                continue
            existing = reg.get(base, None)
            if existing is not None:
                existing_provide = existing[0]
                if existing_provide is not primary_provide:
                    if not existing_provide.extends(primary_provide):
                        continue
                    # else we are registering a general component
                    # after a more specific component.
            self._registerAllProvided(primary_provide, object, base)


    def register(self, provide, object):
        if not IInterface.providedBy(provide):
            raise TypeError(
                "The provide argument must be an interface (or None)")

        self._registerAllProvided(provide, object, provide)

    def getRegistered(self, interface, default=None):
        """Find the component registered exactly for the interface
        """
        c = self._reg.get(interface)
        if c is not None and c[0] is interface:
            return c[1]

        return default

    def getRegisteredMatching(self):
        return [(iface, impl)
                for iface, (regiface, impl) in self._reg.items()
                if iface is regiface]

    def get(self, interface, default=None):
        """Find the component registered for the interface

        A component may be returned if it was registered fgor a more
        specific interface.

        """
        c = self._reg.get(interface)
        if c is not None:
            return c[1]

        return default
