##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Global Adapter Service

$Id$
"""
from zope.component.exceptions import ComponentLookupError
from zope.component.interfaces import IAdapterService, IRegistry
from zope.component.service import GlobalService
from zope.interface.adapter import AdapterRegistry
from zope.interface import implements, providedBy, Interface
import sys
import warnings

class IGlobalAdapterService(IAdapterService, IRegistry):

    def register(required, provided, name, factory, info=''):
        """Register an adapter factory

        :Parameters:
          - `required`: a sequence of specifications for objects to be
             adapted. 
          - `provided`: The interface provided by the adapter
          - `name`: The adapter name
          - `factory`: The object used to compute the adapter
          - `info`: Provide some info about this particular adapter.
        """

    def subscribe(required, provided, factory, info=''):
        """Register a subscriber factory

        :Parameters:
          - `required`: a sequence of specifications for objects to be
             adapted. 
          - `provided`: The interface provided by the adapter
          - `name`: The adapter name
          - `factory`: The object used to compute the subscriber
          - `info`: Provide some info about this particular adapter.
        """

class AdapterService(AdapterRegistry):
    """Base implementation of an adapter service, implementing only the
    'IAdapterService' interface.

    No write-methods were implemented.
    """

    implements(IAdapterService)

class GlobalAdapterService(AdapterService, GlobalService):
    """Global Adapter Service implementation."""

    implements(IGlobalAdapterService)

    def __init__(self):
        AdapterRegistry.__init__(self)
        self._registrations = {}

    def register(self, required, provided, name, factory, info=''):
        """Register an adapter

        >>> registry = GlobalAdapterService()
        >>> class R1(Interface):
        ...     pass
        >>> class R2(R1):
        ...     pass
        >>> class P1(Interface):
        ...     pass
        >>> class P2(P1):
        ...     pass

        >>> registry.register((R1, ), P2, 'bob', 'c1', 'd1')
        >>> registry.register((R1, ), P2,    '', 'c2', 'd2')
        >>> registry.lookup((R2, ), P1, '')
        'c2'

        >>> registrations = map(repr, registry.registrations())
        >>> registrations.sort()
        >>> for registration in registrations:
        ...    print registration
        AdapterRegistration(('R1',), 'P2', '', 'c2', 'd2')
        AdapterRegistration(('R1',), 'P2', 'bob', 'c1', 'd1')

        """
        required = tuple(required)
        self._registrations[(required, provided, name)] = AdapterRegistration(
            required, provided, name, factory, info)

        AdapterService.register(self, required, provided, name, factory)

    def subscribe(self, required, provided, factory, info=''):
        """Register an subscriptions adapter

        >>> registry = GlobalAdapterService()
        >>> class R1(Interface):
        ...     pass
        >>> class R2(R1):
        ...     pass
        >>> class P1(Interface):
        ...     pass
        >>> class P2(P1):
        ...     pass

        >>> registry.subscribe((R1, ), P2, 'c1', 'd1')
        >>> registry.subscribe((R1, ), P2, 'c2', 'd2')
        >>> subscriptions = map(str, registry.subscriptions((R2, ), P1))
        >>> subscriptions.sort()
        >>> subscriptions
        ['c1', 'c2']

        >>> registrations = map(repr, registry.registrations())
        >>> registrations.sort()
        >>> for registration in registrations:
        ...    print registration
        SubscriptionRegistration(('R1',), 'P2', 'c1', 'd1')
        SubscriptionRegistration(('R1',), 'P2', 'c2', 'd2')

        """
        required = tuple(required)

        registration = SubscriptionRegistration(
            required, provided, factory, info)

        self._registrations[(required, provided)] = (
            self._registrations.get((required, provided), ())
            +
            (registration, )
            )

        AdapterService.subscribe(self, required, provided, factory)

    def registrations(self):
        for registration in self._registrations.itervalues():
            if isinstance(registration, tuple):
                for r in registration:
                    yield r
            else:
                yield registration


class AdapterRegistration(object):
    """Registration for a simple adapter."""

    def __init__(self, required, provided, name, value, doc=''):
        (self.required, self.provided, self.name, self.value, self.doc
         ) = required, provided, name, value, doc

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r)' % (
            self.__class__.__name__,
            tuple([getattr(r, '__name__', None) for r in self.required]),
            self.provided.__name__, self.name,
            self.value, self.doc,
            )


class SubscriptionRegistration(object):
    """Registration for a subscription adapter."""

    def __init__(self, required, provided, value, doc):
        (self.required, self.provided, self.value, self.doc
         ) = required, provided, value, doc

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (
            self.__class__.__name__,
            tuple([getattr(r, '__name__', None) for r in self.required]),
            self.provided.__name__, self.value, self.doc,
            )
