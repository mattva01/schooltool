##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""Global Presentation Service

This module contains an adapter-registry-based global presentation
service. Additionally it contains all registration classes that can occur:

  - SkinRegistration

  - LayerRegistration

  - DefaultSkinRegistration

  - PresentationRegistration

$Id$
"""
from types import ClassType
from zope.component.interfaces import IPresentationService, IRegistry
from zope.component.service import GlobalService
from zope.component.servicenames import Presentation
from zope.interface import providedBy
from zope.interface.interfaces import IInterface
import zope.interface
import zope.interface.adapter

class IGlobalPresentationService(zope.interface.Interface):
    """Provide ability to update the global presentation service
    """

    def defineSkin(name, layers):
        """Define a skin

        A skin is defined for a request type.  It consists of a
        sequence of layer names.  Layers must be defined before they
        are used in a skin definition.

        Note that there is one predefined layer, "default".
        """

    def setDefaultSkin(name):
        """Set the default skin for a request type

        If not set, it defaults to the "default" skin.
        """

    def defineLayer(name):
        """Define a layer
        """

    def provideAdapter(request_type, factory, name='', contexts=(),
                       providing=zope.interface.Interface, layer='default'):
        """Provide a presentation adapter
        """

class IDefaultViewName(zope.interface.Interface):
    """A string that contains the default view name

    A default view name is used to select a view when a user hasn't
    specified one.
    """

class GlobalPresentationService(GlobalService):
    r"""Global presentation service

       The global presentation service provides management of views, and
       resources arranged in skins, where skins are ordered collections
       of layers.

       Views are modeled as adapters of objects and requests.
       Resources are just request adapters.

       The adapters are arranged in layers.

       Let's look at some examples. First, we'll create a service:

       >>> s = GlobalPresentationService()

       And define a custom layer and skin:

       >>> s.defineLayer('custom')
       >>> s.defineSkin('custom', ['custom', 'default'])

       We'll define a request type and a fake request:

       >>> class IRequest(zope.interface.Interface):
       ...     "Demonstration request type"

       >>> class Request(object):
       ...     zope.interface.implements(IRequest)
       ...     def getPresentationSkin(self):
       ...         return getattr(self, 'skin', None)


       >>> request = Request()

       With this in place, we can start registering resources. A resource
       is just a request adapter.

       >>> class MyResource(object):
       ...    def __init__(self, request):
       ...        self.request = request

       To register a resource, we register it as an adapter. Most
       resources are going to interface with a user, and, so, don't
       really provide a programatic interface. For this reason, we
       register them to provide the empty interface, Interface, which is
       the default provided interface:

       >>> s.provideAdapter(IRequest, MyResource, name='foo', layer='custom')

       Now we can try to look this up:

       >>> s.queryResource('foo', request)

       But we won't get anything, because our request doesn't specify a
       skin and, the default skin gets used.  Our resource was registered
       in the custom layer, which isn't used by the default skin. If we
       set out request skin to 'custom':

       >>> request.skin = 'custom'

       Then the lookup will suceed:

       >>> r = s.queryResource('foo', request)
       >>> r.__class__.__name__
       'MyResource'
       >>> r.request is request
       True

       Views are registered as "multi" adapters.  Multi-adapters adapt
       multiple objects simultaneously.

       >>> class IContact(zope.interface.Interface):
       ...     "Demonstration content type"

       >>> class MyView(object):
       ...     def __init__(self, context, request):
       ...         self.context, self.request = context, request

       >>> s.provideAdapter(IRequest, MyView, contexts=[IContact], 
       ...                  name='foo', layer='custom')

       When defining views, we provide one or more (typically 1) context
       interfaces, corresponding to the contexts of the view.

       >>> class Contact(object):
       ...     zope.interface.implements(IContact)

       >>> c = Contact()

       We look up views with queryView:

       >>> v = s.queryView(c, 'foo', request)
       >>> v.__class__.__name__
       'MyView'
       >>> v.request is request
       True
       >>> v.context is c
       True

       Most views and resources are unnamed and provide no interface. We
       can also have views that provide interfaces.  For example, we
       might need a view to help out with finding objects:

       >>> class ITraverse(zope.interface.Interface):
       ...     "Sample traversal interface (imagine interesting methods :)"

       >>> class Traverser(object):
       ...     zope.interface.implements(ITraverse)
       ...     def __init__(self, context, request):
       ...         self.context, self.request = context, request

       which we register using the provided interface, rather than a name. 

       >>> s.provideAdapter(IRequest, Traverser, contexts=[IContact],
       ...                  providing=ITraverse, layer='custom')

       (We could use a name too, if we wanted to.)

       Then we look up the view using the interface:

       >>> v = s.queryView(c, '', request, providing=ITraverse)
       >>> v.__class__.__name__
       'Traverser'
       >>> v.request is request
       True
       >>> v.context is c
       True
       """

    zope.interface.implements(IPresentationService,
                              IGlobalPresentationService,
                              IRegistry,
                              )

    def __init__(self):
        self._layers = {'default': GlobalLayer(self, 'default')}
        self._skins = {'default': [self._layers['default']]}
        self.skins = {'default': ('default', )}
        self.defaultSkin = 'default'
        self._registrations = {}

    def registrations(self):
        return self._registrations.itervalues()

    def defineSkin(self, name, layers, info=''):
        """Define a skin

        A skin is defined for a request type.  It consists of a
        sequence of layer names.  Layers must be defined before they
        are used in a skin definition.

        Note that there is one predefined layer, "default".

        >>> s = GlobalPresentationService()
        >>> s.defineSkin('default', ['default'])
        Traceback (most recent call last):
        ...
        ValueError: ("Can\'t redefine skin", 'default')


        The layers used in a skin definition must be defined before
        they are used:

        >>> s.defineSkin('custom', ['custom', 'default'])
        Traceback (most recent call last):
        ...
        ValueError: ('Undefined layers', ['custom'])


        >>> s.defineLayer('custom')
        >>> s.defineSkin('custom', ['custom', 'default'], 'custom doc')

        >>> skins = s.skins.items()
        >>> skins.sort()
        >>> skins
        [('custom', ('custom', 'default')), ('default', ('default',))]

        A skin registration is also recorded for each registered skin.

        >>> registrations = map(str, s.registrations())
        >>> registrations.sort()
        >>> for r in registrations:
        ...     print r
        zope.component.presentation.LayerRegistration('custom', '')
        zope.component.presentation.SkinRegistration('custom', """ \
                              """['custom', 'default'], 'custom doc')
        """

        if name in self._skins:
            raise ValueError("Can't redefine skin", name)

        bad = [layer for layer in layers if layer not in self._layers]
        if bad:
            raise ValueError, ("Undefined layers", bad)

        self._skins[name] = [self._layers[layer] for layer in layers]
        self.skins[name] = tuple(layers)
        self._registrations[('skin', name)
                            ] = SkinRegistration(name, layers, info)

    def querySkin(self, name):
        return self.skins.get(name)

    def queryLayer(self, name):
        return self._layers.get(name)

    def setDefaultSkin(self, name, info=''):
        """Set the default skin for a request type

        If not set, it defaults to the "default" skin.

        >>> s = GlobalPresentationService()
        >>> s.defaultSkin
        'default'

        >>> s.setDefaultSkin('custom')
        Traceback (most recent call last):
        ...
        ValueError: ('Undefined skin', 'custom')

        >>> s.defineLayer('custom')
        >>> s.defineSkin('custom', ['custom', 'default'])
        >>> s.setDefaultSkin('custom', 'yawn')
        >>> s.defaultSkin
        'custom'

        A default skin registration is also recorded for each
        registered default skin.

        >>> registrations = map(str, s.registrations())
        >>> registrations.sort()
        >>> for r in registrations:
        ...     print r
        zope.component.presentation.DefaultSkinRegistration('custom', 'yawn')
        zope.component.presentation.LayerRegistration('custom', '')
        zope.component.presentation.SkinRegistration('custom', """ \
                       """['custom', 'default'], '')
        """

        # Make sure we are refering to a defined skin
        if name not in self._skins:
            raise ValueError, ("Undefined skin", name)

        self.defaultSkin = name
        self._registrations['defaultSkin'
                            ] = DefaultSkinRegistration(name, info)

    def defineLayer(self, name, info=''):
        """Define a layer

        >>> s = GlobalPresentationService()
        >>> s.defineLayer('custom', 'blah')

        You can't define a layer that's already defined:

        >>> s.defineLayer('custom')
        Traceback (most recent call last):
        ...
        ValueError: ("Can\'t redefine layer", 'custom')

        A layer registration is also recorded for each registered layer.

        >>> list(s.registrations())
        [zope.component.presentation.LayerRegistration('custom', 'blah')]
        """

        if name in self._layers:
            raise ValueError("Can\'t redefine layer", name)

        self._layers[name] = GlobalLayer(self, name)
        self._registrations[('layer', name)] = LayerRegistration(name, info)

    def provideAdapter(self, request_type, factory, name=u'', contexts=(), 
                       providing=zope.interface.Interface, layer='default',
                       info=''):
        """Provide a presentation adapter

        This is a fairly low-level interface that supports both
        resources and views.

        """

        ifaces = []
        for context in contexts:
            if not IInterface.providedBy(context) and context is not None:
                if not isinstance(context, (type, ClassType)):
                    raise TypeError(context, IInterface)
                context = zope.interface.implementedBy(context)

            ifaces.append(context)

        ifaces.append(request_type)
        ifaces = tuple(ifaces)

        reg = self._layers[layer]

        reg.register(ifaces, providing, name, factory)

        self._registrations[
            (layer, ifaces, providing, name)
            ] = PresentationRegistration(layer, ifaces, providing, name,
                                         factory, info)

    def queryResource(self, name, request, default=None,
                      providing=zope.interface.Interface):
        """Look up a named resource for a given request

        The request must implement IPresentationRequest.

        The default will be returned if the component can't be found.
        """
        skin = request.getPresentationSkin() or self.defaultSkin
        for layer in self._skins[skin]:
            r = layer.queryAdapter(request, providing, name)
            if r is not None:
                return r
        return default

    def queryView(self, object, name, request,
                  providing=zope.interface.Interface, default=None):
        """Look for a named view for a given object and request

        The request must implement IPresentationRequest.

        The default will be returned if the component can't be found.
        """
        skin = request.getPresentationSkin() or self.defaultSkin
        objects = object, request
        for layer in self._skins.get(skin, ()):
            r = layer.queryMultiAdapter(objects, providing, name)
            if r is not None:
                return r
        return default

    def queryMultiView(self, objects, request,
                       providing=zope.interface.Interface, name='',
                       default=None):
        """Adapt the given objects and request

        The first argument is a sequence of objects to be adapted with the
        request.
        """
        skin = request.getPresentationSkin() or self.defaultSkin
        objects = objects + (request, )
        for layer in self._skins[skin]:
            r = layer.queryMultiAdapter(objects, providing, name)
            if r is not None:
                return r
        return default


    ############################################################
    #
    # The following methods are provided for convenience and for
    # backward compatability with old code:

    def provideView(self, for_, name, type, maker, layer='default',
                    providing=zope.interface.Interface):
        # Helper function for simple view defs
        return self.provideAdapter(type, maker, name,
                                   contexts=[for_], layer=layer,
                                   providing=providing)


    def setDefaultViewName(self, for_, request_type, name, layer="default"):
        """Default view names

        A default view name is a name that an application should use
        if a user hasn't selected one.  This should not be confused
        with unnamed views.

        The presentation service can store this by storing the name as
        an "adapter".
        """
        return self.provideAdapter(request_type, name,
                                   providing=IDefaultViewName,
                                   contexts=[for_], layer=layer)

    def queryDefaultViewName(self, object, request, default=None):
        skin = request.getPresentationSkin() or 'default'
        objects = object, request
        for layer in self._skins[skin]:
            r = layer.lookup(map(providedBy, objects), IDefaultViewName)
            if r is not None:
                return r
        return default

    def provideResource(self, name, request_type, factory, layer='default',
                        providing=zope.interface.Interface):
        # Helper function for simple view defs
        return self.provideAdapter(request_type, factory, name, layer=layer,
                                   providing=providing)


def GL(presentation_service, layer_name):
    return presentation_service.queryLayer(layer_name)


class GlobalLayer(zope.interface.adapter.AdapterRegistry):

    def __init__(self, parent, name):
        super(GlobalLayer, self).__init__()
        self.__parent__ = parent
        self.__name__ = name

    def __reduce__(self):
        return GL, (self.__parent__, self.__name__)


class SkinRegistration(object):
    """Registration for a global skin."""

    def __init__(self, skin, layers, info):
        self.skin, self.layers, self.doc = skin, layers, info

    def __repr__(self):
        """Representation of the object in a doctest-friendly format."""
        return '%s.%s(%r, %r, %r)' % (
            self.__class__.__module__, self.__class__.__name__,
            self.skin, self.layers, self.doc)


class LayerRegistration(object):
    """Registration for a global layer."""

    def __init__(self, layer, info):
        self.layer, self.doc = layer, info

    def __repr__(self):
        """Representation of the object in a doctest-friendly format."""
        return '%s.%s(%r, %r)' % (
            self.__class__.__module__, self.__class__.__name__,
            self.layer, self.doc)


class DefaultSkinRegistration(object):
    """Registration for the global default skin."""

    def __init__(self, skin, info):
        self.skin, self.doc = skin, info

    def __repr__(self):
        """Representation of the object in a doctest-friendly format."""
        return '%s.%s(%r, %r)' % (
            self.__class__.__module__, self.__class__.__name__,
            self.skin, self.doc)


class PresentationRegistration(object):
    """Registration for a single presentation component."""

    def __init__(self, layer, required, provided, name, factory, info):
        (self.layer, self.required, self.provided, self.name,
         self.factory, self.doc
         ) = layer, required, provided, name, factory, info

    def __repr__(self):
        """Representation of the object in a doctest-friendly format."""
        return '%s.%s(%s, %r, %r, %r, %r, %r)' % (
            self.__class__.__module__, self.__class__.__name__,
            self.layer,
            tuple([getattr(s, '__name__', None) for s in self.required]),
            self.provided.__name__,
            self.name, getattr(self.factory, '__name__', self.factory),
            self.doc)

