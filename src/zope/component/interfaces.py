############################################################################
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
############################################################################
"""Component and Component Architecture Interfaces

$Id$
"""
from zope.interface import Interface, Attribute
from zope.component.exceptions import *

class IComponentArchitecture(Interface):
    """The Component Architecture is defined by six key services,
    all of which are managed by service managers.
    """

    # basic service manager tools

    def getGlobalServices():
        """Get the global service manager."""

    def getGlobalService(name):
        """Get a global service."""

    def getServices(context=None):
        """Get the service manager

        If context is None, an application-defined policy is used to choose
        an appropriate service manager.

        If 'context' is not None, context is adapted to IServiceService, and
        this adapter is returned.
        """

    def getService(name, context=None):
        """Get a named service.

        Returns the service defined by 'name' from the service manager.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager.

        If 'context' is not None, context is adapted to IServiceService, and
        this adapter is returned.
        """

    def getServiceDefinitions(context=None):
        """Get service definitions

        Returns a dictionary of the service definitions from the service
        manager in the format {nameString: serviceInterface}.

        The default behavior of placeful service managers is to include
        service definitions above them, but this can be overridden.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager.

        If 'context' is not None, context is adapted to IServiceService, and
        this adapter is returned.
        """

    # Utility service

    def getUtility(interface, name='', context=None):
        """Get the utility that provides interface

        Returns the nearest utility to the context that implements the
        specified interface.  If one is not found, raises
        ComponentLookupError.
        """

    def queryUtility(interface, name='', default=None, context=None):
        """Look for the utility that provides interface

        Returns the nearest utility to the context that implements
        the specified interface.  If one is not found, returns default.
        """

    def getUtilitiesFor(interface, context=None):
        """Return the utilities that provide an interface

        An iterable of utility name-value pairs is returned.
        """

    def getAllUtilitiesRegisteredFor(interface, context=None):
        """Return all registered utilities for an interface

        This includes overridden utilities.

        An iterable of utility instances is returned.  No names are
        returned.
        """

    # Adapter service

    def getAdapter(object, interface, name, context=''):
        """Get a named adapter to an interface for an object

        Returns an adapter that can adapt object to interface.  If a matching
        adapter cannot be found, raises ComponentLookupError.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """

    def getAdapterInContext(object, interface, context):
        """Get a special adapter to an interface for an object

        NOTE: This method should only be used if a custom context
        needs to be provided to provide custom component
        lookup. Otherwise, call the interface, as in::

           interface(object)

        Returns an adapter that can adapt object to interface.  If a matching
        adapter cannot be found, raises ComponentLookupError.

        Context is adapted to IServiceService, and this adapter's
        'Adapters' service is used.

        If the object has a __conform__ method, this method will be
        called with the requested interface.  If the method returns a
        non-None value, that value will be returned. Otherwise, if the
        object already implements the interface, the object will be
        returned.
        """

    def getMultiAdapter(objects, interface, name='', context=None):
        """Look for a multi-adapter to an interface for an objects

        Returns a multi-adapter that can adapt objects to interface.  If a
        matching adapter cannot be found, raises ComponentLookupError.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.

        The name consisting of an empty string is reserved for unnamed
        adapters. The unnamed adapter methods will often call the
        named adapter methods with an empty string for a name.
        """

    def queryAdapter(object, interface, name, default=None, context=None):
        """Look for a named adapter to an interface for an object

        Returns an adapter that can adapt object to interface.  If a matching
        adapter cannot be found, returns the default.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """

    def queryAdapterInContext(object, interface, context, default=None):
        """Look for a special adapter to an interface for an object

        NOTE: This method should only be used if a custom context
        needs to be provided to provide custom component
        lookup. Otherwise, call the interface, as in::

           interface(object, default)

        Returns an adapter that can adapt object to interface.  If a matching
        adapter cannot be found, returns the default.

        Context is adapted to IServiceService, and this adapter's
        'Adapters' service is used.

        If the object has a __conform__ method, this method will be
        called with the requested interface.  If the method returns a
        non-None value, that value will be returned. Otherwise, if the
        object already implements the interface, the object will be
        returned.
        """

    def queryMultiAdapter(objects, interface, name='', default=None,
                          context=None):
        """Look for a multi-adapter to an interface for objects

        Returns a multi-adapter that can adapt objects to interface.  If a
        matching adapter cannot be found, returns the default.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.

        The name consisting of an empty string is reserved for unnamed
        adapters. The unnamed adapter methods will often call the
        named adapter methods with an empty string for a name.
        """

    def subscribers(required, provided, context=None):
        """Get subscribers

        Subscribers are returned that provide the provided interface
        and that depend on and are computed from the sequence of
        required objects.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters'
        service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """


    # Factory service

    # TODO: Hard to make context a keyword, leaving as it is. Maybe we should
    #       at least move it to the second position.
    def createObject(context, name, *args, **kwargs):
        """Create an object using a factory

        Finds the factory of the given name that is nearest to the
        context, and passes the other given arguments to the factory
        to create a new instance. Returns a reference to the new
        object.  If a matching factory cannot be found raises
        ComponentLookupError
        """

    def getFactoryInterfaces(name, context=None):
        """Get interfaces implemented by a factory

        Finds the factory of the given name that is nearest to the
        context, and returns the interface or interface tuple that
        object instances created by the named factory will implement.
        """

    def getFactoriesFor(interface, context=None):
        """Return a tuple (name, factory) of registered factories that
        create objects which implement the given interface.
        """

    # Presentation service

    def getView(object, name, request, providing=Interface, context=None):
        """Get a named view for a given object.

        The request must implement IPresentationRequest: it provides
        the view type and the skin name.  The nearest one to the
        object is found. If a matching view cannot be found, raises
        ComponentLookupError.
        """

    def queryView(object, name, request,
                  default=None, providing=Interface, context=None):
        """Look for a named view for a given object.

        The request must implement IPresentationRequest: it provides
        the view type and the skin name.  The nearest one to the
        object is found.  If a matching view cannot be found, returns
        default.

        If context is not specified, attempts to use object to specify
        a context.
        """

    def getMultiView(objects, request, providing=Interface, name='',
                     context=None):
        """Look for a multi-view for given objects

        The request must implement IPresentationRequest: it provides
        the view type and the skin name.  The nearest one to the
        object is found.  If a matching view cannot be found, raises
        ComponentLookupError.

        If context is not specified, attempts to use the first object
        to specify a context.
        """

    def queryMultiView(objects, request, providing=Interface, name='',
                       default=None, context=None):
        """Look for a multi-view for given objects

        The request must implement IPresentationRequest: it provides
        the view type and the skin name.  The nearest one to the
        object is found.  If a matching view cannot be found, returns
        default.

        If context is not specified, attempts to use the first object
        to specify a context.
        """

    def getViewProviding(object, providing, request, context=None):
        """Look for a view based on the interface it provides.

        A call to this method is equivalent to:

            getView(object, '', request, context, providing)
        """

    def queryViewProviding(object, providing, request,
                           default=None, context=None):
        """Look for a view that provides the specified interface.

        A call to this method is equivalent to:

            queryView(object, '', request, default, context, providing)
        """

    def getDefaultViewName(object, request, context=None):
        """Get the name of the default view for the object and request.

        The request must implement IPresentationRequest, and provides the
        desired view type.  The nearest one to the object is found.
        If a matching default view name cannot be found, raises
        NotFoundError.

        If context is not specified, attempts to use
        object to specify a context.
        """

    def queryDefaultViewName(object, request, default=None, context=None):
        """Look for the name of the default view for the object and request.

        The request must implement IPresentationRequest, and provides
        the desired view type.  The nearest one to the object is
        found.  If a matching default view name cannot be found,
        returns the default.

        If context is not specified, attempts to use object to specify
        a context.
        """

    def getResource(name, request, providing=Interface, context=None):
        """Get a named resource for a given request

        The request must implement IPresentationRequest.

        The context provides a place to look for placeful resources.

        A ComponentLookupError will be raised if the component can't
        be found.
        """

    def queryResource(name, request, default=None, providing=Interface,
                      context=None):
        """Get a named resource for a given request

        The request must implement IPresentationRequest.

        The context provides a place to look for placeful resources.

        If the component can't be found, the default is returned.
        """


class IRegistry(Interface):
    """Object that supports component registry
    """

    def registrations():
        """Return an iterable of component registrations
        """


class IServiceService(Interface):
    """A service to manage Services."""

    def getServiceDefinitions():
        """Retrieve all Service Definitions

        Should return a list of tuples (name, interface)
        """

    def getInterfaceFor(name):
        """Retrieve the service interface for the given name
        """

    def getService(name):
        """Retrieve a service implementation

        Raises ComponentLookupError if the service can't be found.
        """


class IFactory(Interface):
    """A factory is responsible for creating other components."""

    title = Attribute("The factory title.")

    description = Attribute("A brief description of the factory.")

    def __call__(*args, **kw):
        """Return an instance of the objects we're a factory for."""


    def getInterfaces():
        """Get the interfaces implemented by the factory

        Return the interface(s), as an instance of Implements, that objects
        created by this factory will implement. If the callable's Implements
        instance cannot be created, an empty Implements instance is returned.
        """


class IUtilityService(Interface):
    """A service to manage Utilities."""

    def getUtility(interface, name=''):
        """Look up a utility that provides an interface.

        If one is not found, raises ComponentLookupError.
        """

    def queryUtility(interface, name='', default=None):
        """Look up a utility that provides an interface.

        If one is not found, returns default.
        """

    def getUtilitiesFor(interface):
        """Look up the registered utilities that provide an interface.

        Returns an iterable of name-utility pairs.
        """

    def getAllUtilitiesRegisteredFor(interface):
        """Return all registered utilities for an interface

        This includes overwridden utilities.

        An iterable of utility instances is returned.  No names are
        returned.
        """


class IContextDependent(Interface):
    """Components implementing this interface must have a context component.

    Usually the context must be one of the arguments of the
    constructor. Adapters and views are a primary example of context-dependent
    components.
    """

    context = Attribute(
        """The context of the object

        This is the object being adapted, viewed, extended, etc.
        """)


class IAdapterService(Interface):
    """A service to manage Adapters."""

    def queryAdapter(object, interface, name, default=None):
        """Look for a named adapter to an interface for an object

        If a matching adapter cannot be found, returns the default.

        The name consisting of an empty string is reserved for unnamed
        adapters. The unnamed adapter methods will often call the
        named adapter methods with an empty string for a name.
        """

    def queryMultiAdapter(objects, interface, name, default=None):
        """Look for a multi-adapter to an interface for an object

        If a matching adapter cannot be found, returns the default.

        The name consisting of an empty string is reserved for unnamed
        adapters. The unnamed adapter methods will often call the
        named adapter methods with an empty string for a name.
        """

    def subscribers(required, provided):
        """Get subscribers

        Subscribers are returned that provide the provided interface
        and that depend on and are comuted from the sequence of
        required objects.
        """


class IPresentation(Interface):
    """Presentation components provide interfaces to external actors

    The are created for requests, which encapsulate external actors,
    connections, etc.
    """

    request = Attribute(
        """The request

        The request is a surrogate for the user. It also provides the
        presentation type and skin. It is of type
        IPresentationRequest.
        """)


class IPresentationRequest(Interface):
    """An IPresentationRequest provides methods for getting view meta data."""

    def getPresentationSkin():
        """Get the skin to be used for a request.

        The skin is a string as would be passed
        to IViewService.getView.
        """


class IResource(IPresentation):
    """Resources provide data to be used for presentation."""


class IResourceFactory(Interface):
    """A factory to create factories using the request."""

    def __call__(request):
        """Create a resource for a request

        The request must be an IPresentationRequest.
        """


class IView(IPresentation, IContextDependent):
    """Views provide a connection between an external actor and an object"""


class IViewFactory(Interface):
    """Objects for creating views"""

    def __call__(context, request):
        """Create an view (IView) object

        The context aregument is the object displayed by the view. The
        request argument is an object, such as a web request, that
        "stands in" for the user.
        """


class IPresentationService(Interface):
    """A service to manage Presentation components."""

    def queryResource(name, request, default=None, providing=Interface):
        """Look up a named resource for a given request

        The request must implement IPresentationRequest.

        The default will be returned if the component can't be found.
        """

    def queryView(object, name, request, default=None, providing=Interface):
        """Look for a named view for a given object and request

        The request must implement IPresentationRequest.

        The default will be returned if the component can't be found.
        """

    def queryMultiView(objects, request, providing=Interface, name='',
                       default=None):
        """Adapt the given objects and request

        The first argument is a tuple of objects to be adapted with the
        request.
        """
