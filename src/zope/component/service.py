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
"""Service Manager implementation

$Id$
"""

from zope.exceptions import DuplicationError
from zope.component.interfaces import IServiceService
from zope.component.exceptions import ComponentLookupError
from zope.interface import implements


class IGlobalServiceManager(IServiceService):

    def defineService(name, interface):
        """Define a new service of the given name implementing the given
        interface.  If the name already exists, raises
        DuplicationError"""

    def provideService(name, component):
        """Register a service component.

        Provide a service component to do the work of the named
        service.  If a service component has already been assigned to
        this name, raise DuplicationError; if the name has not been
        defined, raises UndefinedService; if the component does not
        implement the registered interface for the service name,
        raises InvalidService.

        """

class UndefinedService(Exception):
    """An attempt to register a service that has not been defined
    """

class InvalidService(Exception):
    """An attempt to register a service that doesn't implement
       the required interface
    """

class GlobalServiceManager(object):
    """service manager"""

    implements(IGlobalServiceManager)

    def __init__(self, name=None, module=None):
        self._clear()
        self.__name__ = name
        self.__module__ = module

    def _clear(self):
        self.__defs     = {'Services': IServiceService}
        self.__services = {'Services': self}

    def __reduce__(self):
        # Global service managers are pickled as global objects
        return self.__name__

    def defineService(self, name, interface):
        """see IGlobalServiceManager interface"""

        if name in self.__defs:
            raise DuplicationError(name)

        self.__defs[name] = interface

    def getServiceDefinitions(self):
        """see IServiceService Interface"""
        return self.__defs.items()

    def provideService(self, name, component, force=False):
        """see IGlobalServiceManager interface, above

        The force keyword allows one to replace an existing
        service.  This is mostly useful in testing scenarios.
        """

        if not force and name in self.__services:
            raise DuplicationError(name)

        if name not in self.__defs:
            raise UndefinedService(name)

        if not self.__defs[name].providedBy(component):
            raise InvalidService(name, component, self.__defs[name])

        if isinstance(component, GlobalService):
            component.__parent__ = self
            component.__name__ = name

        self.__services[name] = component

    def getService(self, name):
        """see IServiceService interface"""
        service = self.__services.get(name)
        if service is None:
            raise ComponentLookupError(name)

        return service


def GS(service_manager, service_name):
    return service_manager.getService(service_name)

class GlobalService(object):

    def __reduce__(self):
        return GS, (self.__parent__, self.__name__)



# the global service manager instance
serviceManager = GlobalServiceManager('serviceManager', __name__)

defineService = serviceManager.defineService

# Register our cleanup with Testing.CleanUp to make writing unit tests
# simpler.
from zope.testing.cleanup import addCleanUp
addCleanUp(serviceManager._clear)
del addCleanUp
