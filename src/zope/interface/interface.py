##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
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
"""Interface object implementation

Revision information:
$Id: interface.py,v 1.12 2003/07/30 18:35:18 jim Exp $
"""

import sys
from types import FunctionType

CO_VARARGS = 4
CO_VARKEYWORDS = 8

class Element(object):

    # We can't say this yet because we don't have enough
    # infrastructure in place.
    #
    #__implements__ = IElement

    def __init__(self, __name__, __doc__=''):
        """Create an 'attribute' description
        """
        if not __doc__ and __name__.find(' ') >= 0:
            __doc__ = __name__
            __name__ = None

        self.__name__=__name__
        self.__doc__=__doc__
        self.__tagged_values = {}

    def getName(self):
        """ Returns the name of the object. """
        return self.__name__

    def getDoc(self):
        """ Returns the documentation for the object. """
        return self.__doc__

    def getTaggedValue(self, tag):
        """ Returns the value associated with 'tag'. """
        return self.__tagged_values[tag]

    def getTaggedValueTags(self):
        """ Returns a list of all tags. """
        return self.__tagged_values.keys()

    def setTaggedValue(self, tag, value):
        """ Associates 'value' with 'key'. """
        self.__tagged_values[tag] = value


class InterfaceClass(Element):
    """Prototype (scarecrow) Interfaces Implementation."""

    # We can't say this yet because we don't have enough
    # infrastructure in place.
    #
    #__implements__ = IInterface

    def __init__(self, name, bases=(), attrs=None, __doc__=None,
                 __module__=None):

        if __module__ is None:
            if (attrs is not None and
                ('__module__' in attrs) and
                isinstance(attrs['__module__'], str)
                ):
                __module__ = attrs['__module__']
                del attrs['__module__']
            else:

                try:
                    # Figure out what module defined the interface.
                    # This is how cPython figures out the module of
                    # a class, but of course it does it in C. :-/
                    __module__ = sys._getframe(1).f_globals['__name__']
                except (AttributeError, KeyError):
                    pass

        self.__module__ = __module__

        for b in bases:
            if not isinstance(b, InterfaceClass):
                raise TypeError, 'Expected base interfaces'
        # Python expects __bases__ to be a tuple.
        self.__bases__ = tuple(bases)

        if attrs is None:
            attrs = {}

        d = attrs.get('__doc__')
        if d is not None:
            if not isinstance(d, Attribute):
                if __doc__ is None:
                    __doc__ = d
                del attrs['__doc__']

        if __doc__ is None:
            __doc__ = ''

        Element.__init__(self, name, __doc__)

        self.__iro__ = mergeOrderings([_flattenInterface(self, [])])

        for k, v in attrs.items():
            if isinstance(v, Attribute):
                v.interface = name
                if not v.__name__:
                    v.__name__ = k
            elif isinstance(v, FunctionType):
                attrs[k] = fromFunction(v, name, name=k)
            else:
                raise InvalidInterface("Concrete attribute, %s" % k)

        self.__attrs = attrs

        self.__identifier__ = "%s.%s" % (self.__module__, self.__name__)


    def getBases(self):
        return self.__bases__

    def extends(self, other, strict=True):
        """Does an interface extend another?"""
        if not strict and self == other:
            return True

        for b in self.__bases__:
            if b == other: return True
            if b.extends(other): return True
        return False

    def isEqualOrExtendedBy(self, other):
        """Same interface or extends?"""
        if self == other:
            return True
        return other.extends(self)

    def isImplementedBy(self, object):
        """Does the given object implement the interface?"""

        # OPT Cache implements lookups
        implements = providedBy(object)
        cache = getattr(self, '_v_cache', self)
        if cache is self:
            cache = self._v_cache = {}


        key = implements.__signature__

        r = cache.get(key)
        if r is None:
            r = bool(implements.extends(self))
            cache[key] = r

        return r

    def isImplementedByInstancesOf(self, klass):
        """Do instances of the given class implement the interface?"""
        i = implementedBy(klass)
        return bool(i.extends(self))

    def names(self, all=False):
        """Return the attribute names defined by the interface."""
        if not all:
            return self.__attrs.keys()

        r = {}
        for name in self.__attrs.keys():
            r[name] = 1
        for base in self.__bases__:
            for name in base.names(all):
                r[name] = 1
        return r.keys()

    def __iter__(self):
        return iter(self.names(all=True))

    def namesAndDescriptions(self, all=False):
        """Return attribute names and descriptions defined by interface."""
        if not all:
            return self.__attrs.items()

        r = {}
        for name, d in self.__attrs.items():
            r[name] = d

        for base in self.__bases__:
            for name, d in base.namesAndDescriptions(all):
                if name not in r:
                    r[name] = d

        return r.items()

    def getDescriptionFor(self, name):
        """Return the attribute description for the given name."""
        r = self.queryDescriptionFor(name)
        if r is not None:
            return r

        raise KeyError, name

    __getitem__ = getDescriptionFor

    def __contains__(self, name):
        return self.queryDescriptionFor(name) is not None

    def queryDescriptionFor(self, name, default=None):
        """Return the attribute description for the given name."""
        r = self.__attrs.get(name, self)
        if r is not self:
            return r
        for base in self.__bases__:
            r = base.queryDescriptionFor(name, self)
            if r is not self:
                return r

        return default

    get = queryDescriptionFor

    def deferred(self):
        """Return a defered class corresponding to the interface."""
        if hasattr(self, "_deferred"): return self._deferred

        klass={}
        exec "class %s: pass" % self.__name__ in klass
        klass=klass[self.__name__]

        self.__d(klass.__dict__)

        self._deferred=klass

        return klass

    def _getInterface(self, ob, name):
        """Retrieve a named interface."""
        return None

    def __d(self, dict):

        for k, v in self.__attrs.items():
            if isinstance(v, Method) and not (k in dict):
                dict[k]=v

        for b in self.__bases__: b.__d(dict)

    def __repr__(self):
        r = getattr(self, '_v_repr', self)
        if r is self:
            name = self.__name__
            m = self.__module__
            if m:
                name = '%s.%s' % (m, name)
            r = "<%s %s at %x>" % (self.__class__.__name__, name, id(self))
            self._v_repr = r
        return r

    def __reduce__(self):
        return self.__name__

    def __cmp(self, o1, o2):
        # Yes, I did mean to name this __cmp, rather than __cmp__.
        # It is a private method used by __lt__ and __gt__.
        # I don't want to override __eq__ because I want the default
        # __eq__, which is really fast.
        """Make interfaces sortable

        It would ne nice if:

           More specific interfaces should sort before less specific ones.
           Otherwise, sort on name and module.

           But this is too complicated, and we're going to punt on it
           for now. XXX

        XXX For now, sort on interface and module name.

        None is treated as a psuedo interface that implies the loosest
        contact possible, no contract. For that reason, all interfaces
        sort before None.

        """

        if o1 == o2:
            return 0

        if o1 is None:
            return 1
        if o2 is None:
            return -1

# XXX first and incorrect stab at ordering more specific interfaces first
##         if self.extends(other):
##             return 1

##         if other.extends(self):
##             return 0



        n1 = (getattr(o1, '__name__', ''),
              getattr(getattr(o1,  '__module__', None), '__name__', ''))
        n2 = (getattr(o2, '__name__', ''),
              getattr(getattr(o2,  '__module__', None), '__name__', ''))

        return cmp(n1, n2)

    def __lt__(self, other):
        c = self.__cmp(self, other)
        #print '<', self, other, c < 0, c
        return c < 0

    def __gt__(self, other):
        c = self.__cmp(self, other)
        #print '>', self, other, c > 0, c
        return c > 0


def mergeOrderings(orderings, seen=None):
    """Merge multiple orderings so that within-ordering order is preserved

    Orderings are constrained in such a way that if an object appears
    in two or more orderings, then the suffix that begins with the
    object must be in both orderings.

    For example:

    >>> _mergeOrderings([
    ... ['x', 'y', 'z'],
    ... ['q', 'z'],
    ... [1, 3, 5],
    ... ['z']
    ... ])
    ['x', 'y', 'q', 1, 3, 5, 'z']

    """

    if seen is None:
        seen = {}
    result = []
    orderings.reverse()
    for ordering in orderings:
        ordering = list(ordering)
        ordering.reverse()
        for o in ordering:
            if o not in seen:
                seen[o] = 1
                result.append(o)

    result.reverse()
    return result

def _flattenInterface(iface, result):
    result.append(iface)
    for base in iface.__bases__:
        _flattenInterface(base, result)

    return result

Interface = InterfaceClass("Interface", __module__ = 'zope.interface')

class Attribute(Element):
    """Attribute descriptions
    """

    # We can't say this yet because we don't have enough
    # infrastructure in place.
    #
    #__implements__ = IAttribute

class Method(Attribute):
    """Method interfaces

    The idea here is that you have objects that describe methods.
    This provides an opportunity for rich meta-data.
    """

    # We can't say this yet because we don't have enough
    # infrastructure in place.
    #
    #__implements__ = IMethod

    interface=''

    def __call__(self, *args, **kw):
        raise BrokenImplementation(self.interface, self.__name__)

    def getSignatureInfo(self):
        return {'positional': self.positional,
                'required': self.required,
                'optional': self.optional,
                'varargs': self.varargs,
                'kwargs': self.kwargs,
                }

    def getSignatureString(self):
        sig = "("
        for v in self.positional:
            sig = sig + v
            if v in self.optional.keys():
                sig = sig + "=%s" % `self.optional[v]`
            sig = sig + ", "
        if self.varargs:
            sig = sig + ("*%s, " % self.varargs)
        if self.kwargs:
            sig = sig + ("**%s, " % self.kwargs)

        # slice off the last comma and space
        if self.positional or self.varargs or self.kwargs:
            sig = sig[:-2]

        sig = sig + ")"
        return sig


def fromFunction(func, interface='', imlevel=0, name=None):
    name = name or func.__name__
    m=Method(name, func.__doc__)
    defaults=func.func_defaults or ()
    c=func.func_code
    na=c.co_argcount-imlevel
    names=c.co_varnames[imlevel:]
    d={}
    nr=na-len(defaults)
    if nr < 0:
        defaults=defaults[-nr:]
        nr=0

    for i in range(len(defaults)):
        d[names[i+nr]]=defaults[i]

    m.positional=names[:na]
    m.required=names[:nr]
    m.optional=d

    argno = na
    if c.co_flags & CO_VARARGS:
        m.varargs = names[argno]
        argno = argno + 1
    else:
        m.varargs = None
    if c.co_flags & CO_VARKEYWORDS:
        m.kwargs = names[argno]
    else:
        m.kwargs = None

    m.interface=interface

    for k, v in func.__dict__.items():
        m.setTaggedValue(k, v)

    return m

def fromMethod(meth, interface=''):
    func = meth.im_func
    return fromFunction(func, interface, imlevel=1)


# Now we can create the interesting interfaces and wire them up:
def _wire():
    from zope.interface.declarations import classImplements

    from zope.interface.interfaces import IAttribute
    classImplements(Attribute, IAttribute)

    from zope.interface.interfaces import IMethod
    classImplements(Method, IMethod)

    from zope.interface.interfaces import IInterface
    classImplements(InterfaceClass, IInterface)

# We import this here to deal with module dependencies.
from zope.interface.declarations import providedBy, implementedBy
from zope.interface.exceptions import InvalidInterface
from zope.interface.exceptions import BrokenImplementation
