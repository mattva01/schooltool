##############################################################################
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
##############################################################################
"""Implementation of interface declarations

$Id: declarations.py,v 1.17 2003/08/16 00:44:44 srichter Exp $
"""

import sys
from zope.interface.interface import InterfaceClass, mergeOrderings
import exceptions
from types import ClassType
from zope.interface.advice import addClassAdvisor

# There are imports from _zope_interface_ospec later in the file
# because _zope_interface_ospec depends on some functions defined
# here.


DescriptorAwareMetaClasses = ClassType, type

__metaclass__ = type

heap = 1 << 9

# Notes:
#
# We have 3 implementations of interface specifications:
#
# ImplementsSpecification
#   Holds specifications of interfaces of instances of classes.
#
# ProvidesSpecification
#   These are specifications for interfaces directly provided by
#   objects.   This is a descriptor that assures
#   that if we get it from a class for an instance, we get an attribute
#   error.
#
# ObjectSpecification
#   Holds the specification for all of the interfaces of an object.
#   These are computed on the floy based on provides and implements
#   specs.
#
# We also have a descriptor to support providedBy


# implementation info for immutable classes (heap flag clear)
# This is overridden by _zope_interface_ospec.
_implements_reg = {}

# This is overridden by _zope_interface_ospec.
class InterfaceSpecificationBase:
    __slots__ = ['__signature__']


# This function is needed by _zope_interface_ospec and, so, must be
# defined before _zope_interface_ospec is imported.
def classImplements(cls, *interfaces):
    """Declare additional interfaces implemented for instances of a class

    The arguments after the class are one or more interfaces or
    interface specifications (IInterfaceSpecification objects).

    The interfaces given (including the interfaces in the
    specifications) are added to any interfaces previously
    declared.

    Consider the following example::


    for example:

    >>> from zope.interface import Interface
    >>> class I1(Interface): pass
    ...
    >>> class I2(Interface): pass
    ...
    >>> class I3(Interface): pass
    ...
    >>> class I4(Interface): pass
    ...
    >>> class I5(Interface): pass
    ...
    >>> class A:
    ...   implements(I3)
    >>> class B:
    ...   implements(I4)
    >>> class C(A, B):
    ...   pass
    >>> classImplements(C, I1, I2)
    >>> [i.getName() for i in implementedBy(C)]
    ['I1', 'I2', 'I3', 'I4']
    >>> classImplements(C, I5)
    >>> [i.getName() for i in implementedBy(C)]
    ['I1', 'I2', 'I5', 'I3', 'I4']

    Instances of ``C`` provide ``I1``, ``I2``, ``I5``, and whatever interfaces
    instances of ``A`` and ``B`` provide.

    """

    _setImplements(cls,
                   _getImplements(cls) + ImplementsSpecification(*interfaces)
                   )

# This function is needed by _zope_interface_ospec and, so, must be
# defined before _zope_interface_ospec is imported.
def proxySig(cls):
    # Get an implementation signature from a proxied class

    # XXX If we got here, we must have a
    # security-proxied class. This introduces an
    # indirect dependency on security proxies,
    # which we don't want. This is necessary to
    # support old-style __implements__ interface
    # declarations.

    # If we got here, we must have an old-style
    # declaration, so we'll just look for an
    # __implements__.  We can't fix it because the class
    # is probably security proxied.

    implements = getattr(cls, '__implements__', None)
    if implements is not None:
        assert ((implements.__class__ == tuple)
                or
                (InterfaceClass in
                 implements.__class__.__mro__)
                )
        sig = `implements`

        return sig

# This function is needed by _zope_interface_ospec and, so, must be
# defined before _zope_interface_ospec is imported.
def oldSpecSig(cls, implements):
    implements = ImplementsOnlySpecification(implements)
    _setImplements(cls, implements)
    return implements.__signature__

# This is overridden by _zope_interface_ospec.

def combinedSpec(provides, cls):
    if provides is not None:
        result = [provides]
    else:
        result = []

    _gatherSpecs(cls, result)

    return InterfaceSpecification(*result)

class ObjectSpecification_py:
    """Provide object specifications

    These combine information for the object and for it's classes.

    For example::

        >>> from zope.interface import Interface
        >>> class I1(Interface): pass
        ...
        >>> class I2(Interface): pass
        ...
        >>> class I3(Interface): pass
        ...
        >>> class I31(I3): pass
        ...
        >>> class I4(Interface): pass
        ...
        >>> class I5(Interface): pass
        ...
        >>> class A: implements(I1)
        ...
        >>> class B: __implements__ = I2
        ...
        >>> class C(A, B): implements(I31)
        ...
        >>> c = C()
        >>> directlyProvides(c, I4)
        >>> [i.getName() for i in providedBy(c)]
        ['I4', 'I31', 'I1', 'I2']
        >>> [i.getName() for i in providedBy(c).flattened()]
        ['I4', 'I31', 'I3', 'I1', 'I2', 'Interface']
        >>> int(I1 in providedBy(c))
        1
        >>> int(I3 in providedBy(c))
        0
        >>> int(providedBy(c).extends(I3))
        1
        >>> int(providedBy(c).extends(I31))
        1
        >>> int(providedBy(c).extends(I5))
        0
        >>> class COnly(A, B): implementsOnly(I31)
        ...
        >>> class D(COnly): implements(I5)
        ...
        >>> c = D()
        >>> directlyProvides(c, I4)
        >>> [i.getName() for i in providedBy(c)]
        ['I4', 'I5', 'I31']
        >>> [i.getName() for i in providedBy(c).flattened()]
        ['I4', 'I5', 'I31', 'I3', 'Interface']
        >>> int(I1 in providedBy(c))
        0
        >>> int(I3 in providedBy(c))
        0
        >>> int(providedBy(c).extends(I3))
        1
        >>> int(providedBy(c).extends(I1))
        0
        >>> int(providedBy(c).extends(I31))
        1
        >>> int(providedBy(c).extends(I5))
        1
    """

    __slots__ = ['provides', 'cls', '_specslot']

    only = True

    def __init__(self, provides, cls):
        self.provides = provides
        self.cls = cls

    def __nonzero__(self):
        """
        >>> from zope.interface import Interface
        >>> class I1(Interface):
        ...     pass
        >>> class I2(Interface):
        ...     pass
        >>> class C:
        ...     implements(I1)
        >>> c = C()
        >>> int(bool(providedBy(c)))
        1
        >>> directlyProvides(c, I2)
        >>> int(bool(providedBy(c)))
        1
        >>> class C:
        ...     pass
        >>> c = C()
        >>> int(bool(providedBy(c)))
        0
        >>> directlyProvides(c, I2)
        >>> int(bool(providedBy(c)))
        1
        """
        return bool(self.__signature__)

    def __signature__(self):

        provides = self.provides
        if provides is not None:
            provides = provides.__signature__
        else:
            provides = ''


        sig = ''
        cls = self.cls
        try:
            flags = cls.__flags__
        except AttributeError:
            flags = heap

        if flags & heap:
            try:
                dict = cls.__dict__
            except AttributeError:
                sig = proxySig(cls)

            else:
                # Normal case
                implements = dict.get('__implements__')
                if implements is None:
                    # No implements spec, lets add one:
                    classImplements(cls)
                    implements = dict['__implements__']

                try:
                    sig = implements.__signature__
                except AttributeError:
                    # Old-style implements!  Fix it up.
                    sig = oldSpecSig(cls, implements)

        else:
            # Look in reg
            implements = _implements_reg.get(cls)
            if implements is None:
                # No implements spec, lets add one:
                classImplements(cls)
                implements = _implements_reg[cls]
            sig = implements.__signature__



        if sig:
            if provides:
                return provides, sig
            return sig
        else:
            return provides

    __signature__ = property(__signature__)

    def _v_spec(self):
        spec = getattr(self, '_specslot', self)
        if spec is not self:
            return spec

        spec = combinedSpec(self.provides, self.cls)

        self._specslot = spec

        return spec

    _v_spec = property(_v_spec)

    def __contains__(self, interface):
        return interface in self._v_spec

    def __iter__(self):
        return iter(self._v_spec)

    def flattened(self):
        return self._v_spec.flattened()

    def extends(self, interface):
        return self._v_spec.extends(interface)

    def __add__(self, other):
        return self._v_spec + other
    __radd__ = __add__

    def __sub__(self, other):
        return self._v_spec - other

# We keep ObjectSpecification_py around for doctest. :)
ObjectSpecification = ObjectSpecification_py

def getObjectSpecification(ob):

    provides = getattr(ob, '__provides__', None)
    try:
        cls = ob.__class__
    except AttributeError:
        # We can't get the class, so just consider provides
        if provides is not None:
            # Just use the provides spec
            return provides

        # No interfaces
        return _empty

    return ObjectSpecification(provides, cls)

def providedBy(ob):

    # Here we have either a special object, an old-style declaration
    # or a descriptor

    try:
        r = ob.__providedBy__

        # We might have gotten a descriptor from an instance of a
        # class (like an ExtensionClass) that doesn't support
        # descriptors.  We'll make sure we got one by trying to get
        # the only attribute, which all specs have.
        r.only

    except AttributeError:
        # No descriptor, so fall back to a plain object spec
        r = getObjectSpecification(ob)

    return r

class ObjectSpecificationDescriptor:

    def __get__(self, inst, cls):
        """Get an object specification for an object

        For example::

          >>> from zope.interface import Interface
          >>> class IFoo(Interface): pass
          ...
          >>> class IFooFactory(Interface): pass
          ...
          >>> class C:
          ...   implements(IFoo)
          ...   classProvides(IFooFactory)
          >>> [i.getName() for i in C.__providedBy__]
          ['IFooFactory']
          >>> [i.getName() for i in C().__providedBy__]
          ['IFoo']

        """

        # Get an ObjectSpecification bound to either an instance or a class,
        # depending on how we were accessed.
        
        if inst is None:
            return getObjectSpecification(cls)
        else:
            return getObjectSpecification(inst)

from _zope_interface_ospec import _implements_reg
from _zope_interface_ospec import InterfaceSpecificationBase
from _zope_interface_ospec import ObjectSpecification
from _zope_interface_ospec import getObjectSpecification, providedBy
from _zope_interface_ospec import ObjectSpecificationDescriptor

def InterfaceSpecification(*interfaces):
    """Create an interface specification

    The arguments are one or more interfaces or interface
    specifications (IInterfaceSpecification objects).

    A new interface specification (IInterfaceSpecification) with
    the given interfaces is returned.
    """
    return Spec(*_flattenSpecs(interfaces, []))


_spec_cache = {}

class Spec(InterfaceSpecificationBase):

    only = False

    # We don't want to pickle these
    def __reduce__(self):
        raise TypeError, "can't pickle InterfaceSpecification objects"

    def __init__(self, *interfaces):
        self.interfaces = interfaces

        cached = _spec_cache.get(interfaces)
        if not cached:
            set = {}
            iro = mergeOrderings(
                [iface.__iro__ for iface in self.interfaces],
                set)
            sig = '\t'.join([iface.__identifier__ for iface in iro])
            cached = iro, set, sig
            _spec_cache[interfaces] = cached

        self.__iro__, self.set, self.__signature__ = cached

    def __nonzero__(self):
        """Test whether there are any interfaces in a specification.

        >>> from zope.interface import Interface
        >>> class I1(Interface): pass
        ...
        >>> spec = InterfaceSpecification(I1)
        >>> int(bool(spec))
        1
        >>> spec = InterfaceSpecification()
        >>> int(bool(spec))
        0
        """
        return bool(self.interfaces)

    def __contains__(self, interface):
        """Test whether an interface is in the specification

        for example::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(I3): pass
          ...
          >>> spec = InterfaceSpecification(I2, I3)
          >>> spec = InterfaceSpecification(I4, spec)
          >>> int(I1 in spec)
          0
          >>> int(I2 in spec)
          1
          >>> int(I3 in spec)
          1
          >>> int(I4 in spec)
          1
        """
        return interface in self.interfaces

    def __iter__(self):
        """Return an iterator for the interfaces in the specification

        for example::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(I3): pass
          ...
          >>> spec = InterfaceSpecification(I2, I3)
          >>> spec = InterfaceSpecification(I4, spec)
          >>> i = iter(spec)
          >>> i.next().getName()
          'I4'
          >>> i.next().getName()
          'I2'
          >>> i.next().getName()
          'I3'
          >>> list(i)
          []
        """

        return iter(self.interfaces)

    def flattened(self):
        """Return an iterator of all included and extended interfaces

        for example::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(I3): pass
          ...
          >>> spec = InterfaceSpecification(I2, I3)
          >>> spec = InterfaceSpecification(I4, spec)
          >>> i = spec.flattened()
          >>> i.next().getName()
          'I4'
          >>> i.next().getName()
          'I2'
          >>> i.next().getName()
          'I1'
          >>> i.next().getName()
          'I3'
          >>> i.next().getName()
          'Interface'
          >>> list(i)
          []

        """

        return iter(self.__iro__)

    def extends(self, interface):
        """Does the specification extend the given interface?

        Test whether an interface in the specification extends the
        given interface

        Examples::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(I3): pass
          ...
          >>> spec = InterfaceSpecification()
          >>> int(spec.extends(Interface))
          0
          >>> spec = InterfaceSpecification(I2)
          >>> int(spec.extends(Interface))
          1
          >>> int(spec.extends(I1))
          1
          >>> int(spec.extends(I2))
          1
          >>> int(spec.extends(I3))
          0
          >>> int(spec.extends(I4))
          0

        """
        return interface in self.set

    def __add__(self, other):
        """Add twp specifications or a specification and an interface


        Examples::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(I3): pass
          ...
          >>> spec = InterfaceSpecification()
          >>> [iface.getName() for iface in spec]
          []
          >>> [iface.getName() for iface in spec+I1]
          ['I1']
          >>> [iface.getName() for iface in I1+spec]
          ['I1']
          >>> spec2 = spec
          >>> spec += I1
          >>> [iface.getName() for iface in spec]
          ['I1']
          >>> [iface.getName() for iface in spec2]
          []
          >>> spec2 += InterfaceSpecification(I3, I4)
          >>> [iface.getName() for iface in spec2]
          ['I3', 'I4']
          >>> [iface.getName() for iface in spec+spec2]
          ['I1', 'I3', 'I4']
          >>> [iface.getName() for iface in spec2+spec]
          ['I3', 'I4', 'I1']

        """
        if other is None:
            other = _empty
        return self.__class__(*_flattenSpecs((self, other), []))

    __radd__ = __add__

    def __sub__(self, other):
        """Remove interfaces from a specification

        Examples::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(I3): pass
          ...
          >>> spec = InterfaceSpecification()
          >>> [iface.getName() for iface in spec]
          []
          >>> spec -= I1
          >>> [iface.getName() for iface in spec]
          []
          >>> spec -= InterfaceSpecification(I1, I2)
          >>> [iface.getName() for iface in spec]
          []
          >>> spec = InterfaceSpecification(I2, I4)
          >>> [iface.getName() for iface in spec]
          ['I2', 'I4']
          >>> [iface.getName() for iface in spec - I4]
          ['I2']
          >>> [iface.getName() for iface in spec - I1]
          ['I4']
          >>> [iface.getName() for iface
          ...  in spec - InterfaceSpecification(I3, I4)]
          ['I2']

        """
        if other is None:
            other = ()
        else:
            other = _flattenSpecs((other,), [])

        ifaces = []


        for iface in self:
            for oface in other:
                if oface in iface.__iro__:
                    break
            else:
                ifaces.append(iface)

        return self.__class__(*ifaces)


class PicklableSpec(Spec):
    """Mix-in that adds picklability

    This is done using a mix-in to prevent regular interface specs
    from being pickled.
    
    """

    __safe_for_unpickling__ = True

    def __reduce__(self):
        return self.__class__, self.interfaces



def _flattenSpecs(specs, result):
    """Flatten a sequence of interfaces and interface specs to interfaces

    >>> I1 = InterfaceClass('I1', (), {})
    >>> I2 = InterfaceClass('I2', (), {})
    >>> I3 = InterfaceClass('I3', (), {})
    >>> spec = InterfaceSpecification(I1, I2)
    >>> r = _flattenSpecs((I3, spec), [])
    >>> int(r == [I3, I1, I2])
    1

    """
    try:
        # catch bad spec by seeing if we can iterate over it
        ispecs = iter(specs)
    except TypeError:
        # Must be a bad spec
        raise exceptions.BadImplements(specs)

    for spec in ispecs:
        # We do this rather than isinstance because it works w proxies classes
        if InterfaceClass in spec.__class__.__mro__:
            if spec not in result:
                result.append(spec)
        elif spec is specs:
            # Try to avoid an infinate loop by getting a string!
            raise TypeError("Bad interface specification", spec)
        else:
            _flattenSpecs(spec, result)

    return result

_empty = InterfaceSpecification()

def ImplementsSpecification(*interfaces):
    return Implements(*_flattenSpecs(interfaces, []))
    
class Implements(PicklableSpec):

    __module__ = 'zope.interface'

    _cspec = None
    def setClass(self, cls):
        self._cspec = Spec(*_flattenSpecs(_gatherSpecs(cls, []), []))
        self.__signature__ = self._cspec.__signature__

    def __get__(self, inst, cls):
        """Get an implementation specification for an object.

        This is a apecification of everything implemented by the
        object's classes and base classes.

        For example::

          >>> from zope.interface import Interface
          >>> class I1(Interface): pass
          ...
          >>> class I2(I1): pass
          ...
          >>> class I3(Interface): pass
          ...
          >>> class I4(Interface): pass
          ...
          >>> class A: implements(I2)
          ...
          >>> class B(A): implements(I3)
          ...
          >>> [i.getName() for i in B.__implements__]
          ['I3', 'I2']
          >>> b = B()
          >>> directlyProvides(b, I4)
          >>> [i.getName() for i in b.__implements__]
          ['I3', 'I2']

        """

        return InterfaceSpecification(_gatherSpecs(cls, []))


def ImplementsOnlySpecification(*interfaces):
    return Only(*_flattenSpecs(interfaces, []))

class Only(Implements):

    __module__ = 'zope.interface'

    only = True

    def __init__(self, *interfaces):
        Spec.__init__(self, *interfaces)
        self.__signature__ = "only(%s)" % self.__signature__


def ProvidesSpecification(*interfaces):
    return Provides(*_flattenSpecs(interfaces, []))

class Provides(PicklableSpec):

    __module__ = 'zope.interface'

    def __get__(self, inst, cls):
        """Make sure that a class __provides__ doesn't leak to an instance

        For example::

          >>> from zope.interface import Interface
          >>> class IFooFactory(Interface): pass
          ...
          >>> class C:
          ...   classProvides(IFooFactory)
          >>> [i.getName() for i in C.__provides__]
          ['IFooFactory']
          >>> getattr(C(), '__provides__', 0)
          0

        """
        if inst is None:
            # We were accessed through a class, so we are the class'
            # provides spec. Just return this object as is, but only
            # if it is in the class dict.
            r = cls.__dict__.get('__provides__')
            if r is not None:
                assert(r is self)
                return r

        raise AttributeError, '__provides__'


_objectSpecificationDescriptor = ObjectSpecificationDescriptor()

def classImplementsOnly(cls, *interfaces):
    """Declare the only interfaces implemented by instances of a class

    The arguments after the class are one or more interfaces or
    interface specifications (IInterfaceSpecification objects).

    The interfaces given (including the interfaces in the
    specifications) replace any previous declarations.

    Consider the following example::

        >>> from zope.interface import Interface
        >>> class I1(Interface): pass
        ...
        >>> class I2(Interface): pass
        ...
        >>> class I3(Interface): pass
        ...
        >>> class I4(Interface): pass
        ...
        >>> class A:
        ...   implements(I3)
        >>> class B:
        ...   implements(I4)
        >>> class C(A, B):
        ...   pass
        >>> classImplementsOnly(C, I1, I2)
        >>> [i.getName() for i in implementedBy(C)]
        ['I1', 'I2']

    Instances of ``C`` provide only ``I1``, ``I2``, and regardless of
    whatever interfaces instances of ``A`` and ``B`` implement.

    """
    spec = ImplementsOnlySpecification(*interfaces)
    spec.only = True
    _setImplements(cls, ImplementsOnlySpecification(*interfaces))

def directlyProvides(object, *interfaces):
    """Declare interfaces declared directly for an object

    The arguments after the object are one or more interfaces or
    interface specifications (IInterfaceSpecification objects).

    The interfaces given (including the interfaces in the
    specifications) replace interfaces previously
    declared for the object.

    Consider the following example::

      >>> from zope.interface import Interface
      >>> class I1(Interface): pass
      ...
      >>> class I2(Interface): pass
      ...
      >>> class IA1(Interface): pass
      ...
      >>> class IA2(Interface): pass
      ...
      >>> class IB(Interface): pass
      ...
      >>> class IC(Interface): pass
      ...
      >>> class A: implements(IA1, IA2)
      ...
      >>> class B: implements(IB)
      ...

      >>> class C(A, B):
      ...    implements(IC)

      >>> ob = C()
      >>> directlyProvides(ob, I1, I2)
      >>> int(I1 in providedBy(ob))
      1
      >>> int(I2 in providedBy(ob))
      1
      >>> int(IA1 in providedBy(ob))
      1
      >>> int(IA2 in providedBy(ob))
      1
      >>> int(IB in providedBy(ob))
      1
      >>> int(IC in providedBy(ob))
      1

    The object, ``ob`` provides ``I1``, ``I2``, and whatever interfaces
    instances have been declared for instances of ``C``.

    To remove directly provided interfaces, use ``directlyProvidedBy`` and
    subtract the unwanted interfaces. For example::

      >>> directlyProvides(ob, directlyProvidedBy(ob)-I2)
      >>> int(I1 in providedBy(ob))
      1
      >>> int(I2 in providedBy(ob))
      0

    removes I2 from the interfaces directly provided by
    ``ob``. The object, ``ob`` no longer directly provides ``I2``,
    although it might still provide ``I2`` if it's class
    implements ``I2``.

    To add directly provided interfaces, use ``directlyProvidedBy`` and
    include additional interfaces.  For example::

      >>> int(I2 in providedBy(ob))
      0
      >>> directlyProvides(ob, directlyProvidedBy(ob), I2)

    adds I2 to the interfaces directly provided by ob::

      >>> int(I2 in providedBy(ob))
      1

    """

    # We need to avoid setting this attribute on meta classes that
    # don't support descriptors.
    # We can do away with this check when we get rid of the old EC
    cls = getattr(object, '__class__', None)
    if cls is not None and getattr(cls,  '__class__', None) is cls:
        # It's a meta class (well, at least it it could be an extension class)
        if not isinstance(object, DescriptorAwareMetaClasses):
            raise TypeError("Attempt to make an interface declaration on a "
                            "non-descriptor-aware class")

    object.__provides__ = ProvidesSpecification(*interfaces)

def implementedBy(class_):
    """Return the interfaces implemented for a class' instances

    The value returned is an IInterfaceSpecification.

    for example:

      >>> from zope.interface import Interface
      >>> class I1(Interface): pass
      ...
      >>> class I2(I1): pass
      ...
      >>> class I3(Interface): pass
      ...
      >>> class I4(I3): pass
      ...
      >>> class C1:
      ...   implements(I2)
      >>> class C2(C1):
      ...   implements(I3)
      >>> [i.getName() for i in implementedBy(C2)]
      ['I3', 'I2']
    """

    return InterfaceSpecification(_gatherSpecs(class_, []))



def directlyProvidedBy(object):
    """Return the interfaces directly provided by the given object

    The value returned is an IInterfaceSpecification.

    """
    return getattr(object, "__provides__", _empty)

def _implements_advice(cls):
    _setImplements(cls, cls.__dict__['__implements__'])
    return cls

def _implements(name, spec):
    frame = sys._getframe(2)
    locals = frame.f_locals

    # Try to make sure we were called from a class def
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError(name+" can be used only from a class definition.")

    if '__providedBy__' in locals:
        raise TypeError(name+" can be used only once in a class definition.")

    locals["__implements__"] = spec
    addClassAdvisor(_implements_advice, depth=3)

def implements(*interfaces):
    """Declare interfaces implemented by instances of a class

    This function is called in a class definition.

    The arguments are one or more interfaces or interface
    specifications (IInterfaceSpecification objects).

    The interfaces given (including the interfaces in the
    specifications) are added to any interfaces previously
    declared.

    Previous declarations include declarations for base classes
    unless implementsOnly was used.

    This function is provided for convenience. It provides a more
    convenient way to call classImplements. For example::

      implements(I1)

    is equivalent to calling::

      classImplements(C, I1)

    after the class has been created.

    Consider the following example::


      >>> from zope.interface import Interface
      >>> class IA1(Interface): pass
      ...
      >>> class IA2(Interface): pass
      ...
      >>> class IB(Interface): pass
      ...
      >>> class IC(Interface): pass
      ...
      >>> class A: implements(IA1, IA2)
      ...
      >>> class B: implements(IB)
      ...

      >>> class C(A, B):
      ...    implements(IC)

      >>> ob = C()
      >>> int(IA1 in providedBy(ob))
      1
      >>> int(IA2 in providedBy(ob))
      1
      >>> int(IB in providedBy(ob))
      1
      >>> int(IC in providedBy(ob))
      1

    Instances of ``C`` implement ``I1``, ``I2``, and whatever interfaces
    instances of ``A`` and ``B`` implement.

    """
    spec = ImplementsSpecification(interfaces)
    _implements("implements", spec)

def implementsOnly(*interfaces):
    """Declare the only interfaces implemented by instances of a class

    This function is called in a class definition.

    The arguments are one or more interfaces or interface
    specifications (IInterfaceSpecification objects).

    Previous declarations including declarations for base classes
    are overridden.

    This function is provided for convenience. It provides a more
    convenient way to call classImplementsOnly. For example::

      implementsOnly(I1)

    is equivalent to calling::

      classImplementsOnly(I1)

    after the class has been created.

    Consider the following example::

      >>> from zope.interface import Interface
      >>> class IA1(Interface): pass
      ...
      >>> class IA2(Interface): pass
      ...
      >>> class IB(Interface): pass
      ...
      >>> class IC(Interface): pass
      ...
      >>> class A: implements(IA1, IA2)
      ...
      >>> class B: implements(IB)
      ...

      >>> class C(A, B):
      ...    implementsOnly(IC)

      >>> ob = C()
      >>> int(IA1 in providedBy(ob))
      0
      >>> int(IA2 in providedBy(ob))
      0
      >>> int(IB in providedBy(ob))
      0
      >>> int(IC in providedBy(ob))
      1


    Instances of ``C`` implement ``IC``, regardless of what
    instances of ``A`` and ``B`` implement.

    """
    spec = ImplementsOnlySpecification(interfaces)
    spec.only = True
    _implements("implements", spec)

def classProvides(*interfaces):
    """Declare interfaces provided directly by a class

    This function is called in a class definition.

    The arguments are one or more interfaces or interface
    specifications (IInterfaceSpecification objects).

    The given interfaces (including the interfaces in the
    specifications) are used to create the class's direct-object
    interface specification.  An error will be raised if the module
    class has an direct interface specification.  In other words, it is
    an error to call this function more than once in a class
    definition.

    Note that the given interfaces have nothing to do with the
    interfaces implemented by instances of the class.

    This function is provided for convenience. It provides a more
    convenient way to call directlyProvidedByProvides for a class. For
    example::

      classProvides(I1)

    is equivalent to calling::

      directlyProvides(theclass, I1)

    after the class has been created.

    For example::

          >>> from zope.interface import Interface
          >>> class IFoo(Interface): pass
          ...
          >>> class IFooFactory(Interface): pass
          ...
          >>> class C:
          ...   implements(IFoo)
          ...   classProvides(IFooFactory)
          >>> [i.getName() for i in C.__providedBy__]
          ['IFooFactory']
          >>> [i.getName() for i in C().__providedBy__]
          ['IFoo']

    if equivalent to::

          >>> from zope.interface import Interface
          >>> class IFoo(Interface): pass
          ...
          >>> class IFooFactory(Interface): pass
          ...
          >>> class C:
          ...   implements(IFoo)
          >>> directlyProvides(C, IFooFactory)
          >>> [i.getName() for i in C.__providedBy__]
          ['IFooFactory']
          >>> [i.getName() for i in C().__providedBy__]
          ['IFoo']


    """
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError(
            "classProvides can only be used from a class definition.")

    if '__provides__' in locals:
        raise TypeError(
            "classProvides can only be used once in a class definition.")

    locals["__provides__"] = ProvidesSpecification(*interfaces)

def moduleProvides(*interfaces):
    """Declare interfaces provided by a module

    This function is used in a module definition.

    The arguments are one or more interfaces or interface
    specifications (IInterfaceSpecification objects).

    The given interfaces (including the interfaces in the
    specifications) are used to create the module's direct-object
    interface specification.  An error will be raised if the module
    already has an interface specification.  In other words, it is
    an error to call this function more than once in a module
    definition.

    This function is provided for convenience. It provides a more
    convenient way to call directlyProvides. For example::

      moduleImplements(I1)

    is equivalent to::

      directlyProvides(sys.modules[__name__], I1)

    """
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def
    if (locals is not frame.f_globals) or ('__name__' not in locals):
        raise TypeError(
            "moduleProvides can only be used from a module definition.")

    if '__provides__' in locals:
        raise TypeError(
            "moduleProvides can only be used once in a module definition.")

    locals["__provides__"] = ProvidesSpecification(*interfaces)


def _getImplements(cls):

    try:
        flags = cls.__flags__
    except AttributeError:
        flags = heap

    if flags & heap:
        try:
            d = cls.__dict__

        except AttributeError:

            # XXX If we got here, we must have a
            # security-proxied class. This introduces an
            # indirect dependency on security proxies,
            # which we don't want. This is necessary to
            # support old-style __implements__ interface
            # declarations.

            # If we got here, we must have an old-style
            # declaration, so we'll just look for an
            # __implements__.

            implements = getattr(cls, '__implements__', None)
            if implements is not None:
                implements = ImplementsOnlySpecification(implements)

            return implements

        k = '__implements__'
    else:
        d = _implements_reg
        k = cls

    return d.get(k)

def _finddescr(cls):
    # Try to find the __providedBy__ descriptor. If we can't find it,
    # just return the class. 

    d = cls.__dict__.get("__providedBy__", cls)
    if d is not cls:
        return d
    for b in cls.__bases__:
        d = _finddescr(b)
        if d is not b:
            return d

    return cls

def _setImplements(cls, v):
    flags = getattr(cls, '__flags__', heap)

    if flags & heap:
        cls.__implements__ = v

        # Add a __providedBy__ descriptor if there isn't already one.
        # If there is one and it's not in the dict, then make a copy
        # here.

        try:
            cls.__providedBy__
        except AttributeError:
            # No existing descriptor, add one
            cls.__providedBy__ = _objectSpecificationDescriptor
        else:
            # Hm, the class already has a descriptor, let's get it and
            # see if it's the right kind.
            try:
                mro = cls.__mro__
            except AttributeError:
                pb = _finddescr(cls)
                if pb is cls:
                    pb = None
            else:
                for c in mro:
                    pb = c.__dict__.get("__providedBy__", c)
                    if pb is not c:
                        break
                else: # no break
                    pb = None

            if not isinstance(pb, ObjectSpecificationDescriptor):
                raise TypeError(
                    cls,
                    "has a __providedBy__ descriptor of the wrong type",
                    pb)

            if "__providedBy__" not in cls.__dict__:
                cls.__providedBy__ = pb

    else:
        _implements_reg[cls] = v

    v.setClass(cls)

def _getmro(C, r):
  if C not in r: r.append(C)
  for b in C.__bases__:
    _getmro(b, r)
  return r

def _gatherSpecs(cls, result):
    implements = _getImplements(cls)
    if implements is not None:
        try:
            stop = implements.only
        except AttributeError:
            # Must be an old-style interface spec
            implements = ImplementsOnlySpecification(
                _flattenSpecs([implements], []))
            stop = 1
            _setImplements(cls, implements)

        if stop:
            result.append(implements)
            return result

        cspec = implements._cspec
        if cspec is not None:
            # We have a cached spec.
            # This makes out job much easier
            result.append(cspec)
            return result

        # No cached cspec. Compute one if we're being called recursively.
        # We know we're being called recursively is result is not empty!
        if result:
            implements.setClass(cls)
            cspec = implements._cspec
            # Now we have one
            result.append(cspec)
            return result

        result.append(implements)

    for b in cls.__bases__:
        _gatherSpecs(b, result)

    return result

# DocTest:
if __name__ == "__main__":
    import doctest, __main__
    doctest.testmod(__main__, isprivate=lambda *a: False)
