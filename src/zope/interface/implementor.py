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
"""Adapter-style interface registry

See Adapter class.

$Id: implementor.py,v 1.8 2004/03/05 22:09:28 jim Exp $
"""
__metaclass__ = type # All classes are new style when run with Python 2.2+

from zope.interface import Interface, implements
from zope.interface.interfaces import IInterface
from zope.interface.interfaces import IImplementorRegistry

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
