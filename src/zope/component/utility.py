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
"""utility service

$Id$
"""
from zope.component.exceptions import Invalid, ComponentLookupError
from zope.component.interfaces import IUtilityService, IRegistry
from zope.component.service import GlobalService
from zope.interface.adapter import AdapterRegistry
import zope.interface

class IGlobalUtilityService(IUtilityService, IRegistry):

    def provideUtility(providedInterface, component, name=''):
        """Provide a utility

        A utility is a component that provides an interface.
        """

class UtilityService(AdapterRegistry):
    """Provide IUtilityService

    Mixin that superimposes utility management on adapter registery
    implementation
    """

    def getUtility(self, interface, name=''):
        """See IUtilityService interface"""
        c = self.queryUtility(interface, name)
        if c is not None:
            return c
        raise ComponentLookupError(interface, name)

    def queryUtility(self, interface, name='', default=None):
        """See IUtilityService interface"""

        byname = self._null.get(interface)
        if byname:
            return byname.get(name, default)
        else:
            return default

    def getUtilitiesFor(self, interface):
        byname = self._null.get(interface)
        if byname:
            for item in byname.iteritems():
                yield item

    def getAllUtilitiesRegisteredFor(self, interface):
        return iter(self._null.get(('s', interface)) or ())

class GlobalUtilityService(UtilityService, GlobalService):

    zope.interface.implementsOnly(IGlobalUtilityService)

    def __init__(self):
        UtilityService.__init__(self)
        self._registrations = {}

    def provideUtility(self, providedInterface, component, name='', info=''):

        if not providedInterface.providedBy(component):
            raise Invalid("The registered component doesn't implement "
                          "the promised interface.")

        self.register((), providedInterface, name, component)

        # Also subscribe to support getAllUtilitiesRegisteredFor:
        self.subscribe((), providedInterface, component)

        self._registrations[(providedInterface, name)] = UtilityRegistration(
            providedInterface, name, component, info)

    def registrations(self):
        return self._registrations.itervalues()


class UtilityRegistration(object):

    def __init__(self, provided, name, component, doc):
        (self.provided, self.name, self.component, self.doc
         ) = provided, name, component, doc

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (
            self.__class__.__name__,
            self.provided.__name__, self.name,
            getattr(self.component, '__name__', self.component), self.doc,
            )

