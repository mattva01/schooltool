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
"""TALES

An implementation of a TAL expression engine

$Id$
"""
import re

from zope.interface import implements

try:
    from zope import tal
except ImportError:
    tal = None

if tal:
    from zope.tal.interfaces import ITALExpressionEngine
    from zope.tal.interfaces import ITALExpressionCompiler
    from zope.tal.interfaces import ITALExpressionErrorInfo
    from zope.tales.interfaces import ITALESIterator


NAME_RE = r"[a-zA-Z][a-zA-Z0-9_]*"
_parse_expr = re.compile(r"(%s):" % NAME_RE).match
_valid_name = re.compile('%s$' % NAME_RE).match


class TALESError(Exception):
    """Error during TALES evaluation"""

class Undefined(TALESError):
    '''Exception raised on traversal of an undefined path'''

class CompilerError(Exception):
    '''TALES Compiler Error'''

class RegistrationError(Exception):
    '''Expression type or base name registration Error'''


_default = object()

class Iterator(object):
    """TALES Iterator
    """

    if tal:
        implements(ITALESIterator)

    def __init__(self, name, seq, context):
        """Construct an iterator

        Iterators are defined for a name, a sequence, or an iterator and a
        context, where a context simply has a setLocal method:

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)

        A local variable is not set until the iterator is used:

        >>> int("foo" in context.vars)
        0

        We can create an iterator on an empty sequence:

        >>> it = Iterator('foo', (), context)

        An iterator works as well:

        >>> it = Iterator('foo', {"apple":1, "pear":1, "orange":1}, context)
        >>> it.next()
        True
        
        >>> it = Iterator('foo', {}, context)
        >>> it.next()
        False

        >>> it = Iterator('foo', iter((1, 2, 3)), context)
        >>> it.next()
        True
        >>> it.next()
        True

        """

        self._seq = seq
        self._iter = i = iter(seq)
        self._nextIndex = 0
        self._name = name
        self._setLocal = context.setLocal

        # This is tricky. We want to know if we are on the last item,
        # but we can't know that without trying to get it. :(
        self._last = False
        try:
            self._next = i.next()
        except StopIteration:
            self._done = True
        else:
            self._done = False

    def next(self):
        """Advance the iterator, if possible.

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> bool(it.next())
        True
        >>> context.vars['foo']
        'apple'
        >>> bool(it.next())
        True
        >>> context.vars['foo']
        'pear'
        >>> bool(it.next())
        True
        >>> context.vars['foo']
        'orange'
        >>> bool(it.next())
        False

        >>> it = Iterator('foo', {"apple":1, "pear":1, "orange":1}, context)
        >>> bool(it.next())
        True
        >>> bool(it.next())
        True
        >>> bool(it.next())
        True
        >>> bool(it.next())
        False

        >>> it = Iterator('foo', (), context)
        >>> bool(it.next())
        False

        >>> it = Iterator('foo', {}, context)
        >>> bool(it.next())
        False


        If we can advance, set a local variable to the new value.
        """
        # Note that these are *NOT* Python iterators!
        if self._done:
            return False
        self._item = v = self._next
        try:
            self._next = self._iter.next()
        except StopIteration:
            self._done = True
            self._last = True

        self._nextIndex += 1
        self._setLocal(self._name, v)
        return True

    def index(self):
        """Get the iterator index

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> int(bool(it.next()))
        1
        >>> it.index()
        0
        >>> int(bool(it.next()))
        1
        >>> it.index()
        1
        >>> int(bool(it.next()))
        1
        >>> it.index()
        2
        """
        index = self._nextIndex - 1
        if index < 0:
            raise TypeError("No iteration position") 
        return index

    def number(self):
        """Get the iterator position

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> int(bool(it.next()))
        1
        >>> it.number()
        1
        >>> int(bool(it.next()))
        1
        >>> it.number()
        2
        >>> int(bool(it.next()))
        1
        >>> it.number()
        3
        """
        return self._nextIndex

    def even(self):
        """Test whether the position is even

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.even()
        False
        >>> it.next()
        True
        >>> it.even()
        True
        >>> it.next()
        True
        >>> it.even()
        False
        """
        return not (self._nextIndex % 2)

    def odd(self):
        """Test whether the position is odd

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.odd()
        True
        >>> it.next()
        True
        >>> it.odd()
        False
        >>> it.next()
        True
        >>> it.odd()
        True
        """
        return bool(self._nextIndex % 2)

    def parity(self):
        """Return 'odd' or 'even' depending on the position's parity

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.parity()
        'odd'
        >>> it.next()
        True
        >>> it.parity()
        'even'
        >>> it.next()
        True
        >>> it.parity()
        'odd'
        """
        if self._nextIndex % 2:
            return 'odd'
        return 'even'

    def letter(self, base=ord('a'), radix=26):
        """Get the iterator position as a lower-case letter

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.letter()
        'a'
        >>> it.next()
        True
        >>> it.letter()
        'b'
        >>> it.next()
        True
        >>> it.letter()
        'c'
        """
        index = self._nextIndex - 1
        if index < 0:
            raise TypeError("No iteration position") 
        s = ''
        while 1:
            index, off = divmod(index, radix)
            s = chr(base + off) + s
            if not index: return s

    def Letter(self):
        """Get the iterator position as an upper-case letter

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.Letter()
        'A'
        >>> it.next()
        True
        >>> it.Letter()
        'B'
        >>> it.next()
        True
        >>> it.Letter()
        'C'
        """
        return self.letter(base=ord('A'))

    def Roman(self, rnvalues=(
                    (1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),
                    (100,'C'),(90,'XC'),(50,'L'),(40,'XL'),
                    (10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')) ):
        """Get the iterator position as an upper-case roman numeral

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.Roman()
        'I'
        >>> it.next()
        True
        >>> it.Roman()
        'II'
        >>> it.next()
        True
        >>> it.Roman()
        'III'
        """
        n = self._nextIndex
        s = ''
        for v, r in rnvalues:
            rct, n = divmod(n, v)
            s = s + r * rct
        return s

    def roman(self):
        """Get the iterator position as a lower-case roman numeral

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.roman()
        'i'
        >>> it.next()
        True
        >>> it.roman()
        'ii'
        >>> it.next()
        True
        >>> it.roman()
        'iii'
        """
        return self.Roman().lower()

    def start(self):
        """Test whether the position is the first position

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.start()
        True
        >>> it.next()
        True
        >>> it.start()
        False
        >>> it.next()
        True
        >>> it.start()
        False

        >>> it = Iterator('foo', {}, context)
        >>> it.start()
        False
        >>> it.next()
        False
        >>> it.start()
        False
        """
        return self._nextIndex == 1

    def end(self):
        """Test whether the position is the last position

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.end()
        False
        >>> it.next()
        True
        >>> it.end()
        False
        >>> it.next()
        True
        >>> it.end()
        True

        >>> it = Iterator('foo', {}, context)
        >>> it.end()
        False
        >>> it.next()
        False
        >>> it.end()
        False
        """
        return self._last

    def item(self):
        """Get the iterator value

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.next()
        True
        >>> it.item()
        'apple'
        >>> it.next()
        True
        >>> it.item()
        'pear'
        >>> it.next()
        True
        >>> it.item()
        'orange'

        >>> it = Iterator('foo', {1:2}, context)
        >>> it.next()
        True
        >>> it.item()
        1

        """
        if self._nextIndex == 0:
            raise TypeError("No iteration position") 
        return self._item

    def length(self):
        """Get the length of the iterator sequence

        >>> context = Context(ExpressionEngine(), {})
        >>> it = Iterator('foo', ("apple", "pear", "orange"), context)
        >>> it.length()
        3

        You can even get the length of a mapping:

        >>> it = Iterator('foo', {"apple":1, "pear":2, "orange":3}, context)
        >>> it.length()
        3

        But you can't get the length of an iterable which doesn't
        support len():

        >>> class MyIter(object):
        ...     def __init__(self, seq):
        ...         self._next = iter(seq).next
        ...     def __iter__(self):
        ...         return self
        ...     def next(self):
        ...         return self._next()
        >>> it = Iterator('foo', MyIter({"apple":1, "pear":2}), context)
        >>> it.length()
        Traceback (most recent call last):
        ...
        TypeError: len() of unsized object

        """
        return len(self._seq)


class ErrorInfo(object):
    """Information about an exception passed to an on-error handler."""
    if tal:
        implements(ITALExpressionErrorInfo)

    def __init__(self, err, position=(None, None)):
        if isinstance(err, Exception):
            self.type = err.__class__
            self.value = err
        else:
            self.type = err
            self.value = None
        self.lineno = position[0]
        self.offset = position[1]


class ExpressionEngine(object):
    '''Expression Engine

    An instance of this class keeps a mutable collection of expression
    type handlers.  It can compile expression strings by delegating to
    these handlers.  It can provide an expression Context, which is
    capable of holding state and evaluating compiled expressions.
    '''
    if tal:
        implements(ITALExpressionCompiler)

    def __init__(self):
        self.types = {}
        self.base_names = {}
        self.namespaces = {}
        self.iteratorFactory = Iterator

    def registerFunctionNamespace(self, namespacename, namespacecallable):
        """Register a function namespace

        namespace - a string containing the name of the namespace to 
                    be registered

        namespacecallable - a callable object which takes the following
                            parameter:

                            context - the object on which the functions 
                                      provided by this namespace will
                                      be called

                            This callable should return an object which
                            can be traversed to get the functions provided
                            by the this namespace.

        example:

           class stringFuncs(object):

              def __init__(self,context):
                 self.context = str(context)

              def upper(self):
                 return self.context.upper()

              def lower(self):
                 return self.context.lower()

            engine.registerFunctionNamespace('string',stringFuncs)
        """
        self.namespaces[namespacename] = namespacecallable


    def getFunctionNamespace(self, namespacename):
        """ Returns the function namespace """
        return self.namespaces[namespacename]

    def registerType(self, name, handler):
        if not _valid_name(name):
            raise RegistrationError, (
                'Invalid expression type name "%s".' % name)
        types = self.types
        if name in types:
            raise RegistrationError, (
                'Multiple registrations for Expression type "%s".' %
                name)
        types[name] = handler

    def getTypes(self):
        return self.types

    def registerBaseName(self, name, object):
        if not _valid_name(name):
            raise RegistrationError, 'Invalid base name "%s".' % name
        base_names = self.base_names
        if name in base_names:
            raise RegistrationError, (
                'Multiple registrations for base name "%s".' % name)
        base_names[name] = object

    def getBaseNames(self):
        return self.base_names

    def compile(self, expression):
        m = _parse_expr(expression)
        if m:
            type = m.group(1)
            expr = expression[m.end():]
        else:
            type = "standard"
            expr = expression
        try:
            handler = self.types[type]
        except KeyError:
            raise CompilerError, (
                'Unrecognized expression type "%s".' % type)
        return handler(type, expr, self)

    def getContext(self, contexts=None, **kwcontexts):
        if contexts is not None:
            if kwcontexts:
                kwcontexts.update(contexts)
            else:
                kwcontexts = contexts
        return Context(self, kwcontexts)

    def getCompilerError(self):
        return CompilerError


class Context(object):
    '''Expression Context

    An instance of this class holds context information that it can
    use to evaluate compiled expressions.
    '''

    if tal:
        implements(ITALExpressionEngine)

    position = (None, None)
    source_file = None

    def __init__(self, engine, contexts):
        self._engine = engine
        self.contexts = contexts
        self.setContext('nothing', None)
        self.setContext('default', _default)

        self.repeat_vars = rv = {}
        # Wrap this, as it is visible to restricted code
        self.setContext('repeat', rv)
        self.setContext('loop', rv) # alias

        self.vars = vars = contexts.copy()
        self._vars_stack = [vars]

        # Keep track of what needs to be popped as each scope ends.
        self._scope_stack = []

    def setContext(self, name, value):
        # Hook to allow subclasses to do things like adding security proxies
        self.contexts[name] = value

    def beginScope(self):
        self.vars = vars = self.vars.copy()
        self._vars_stack.append(vars)        
        self._scope_stack.append([])

    def endScope(self):
        self._vars_stack.pop()
        self.vars = self._vars_stack[-1]

        scope = self._scope_stack.pop()
        # Pop repeat variables, if any
        i = len(scope) 
        while i:
            i = i - 1
            name, value = scope[i]
            if value is None:
                del self.repeat_vars[name]
            else:
                self.repeat_vars[name] = value

    def setLocal(self, name, value):
        self.vars[name] = value

    def setGlobal(self, name, value):
        for vars in self._vars_stack:
            vars[name] = value

    def getValue(self, name, default=None):
        value = default
        for vars in self._vars_stack:
            value = vars.get(name, default)
            if value is not default:
                break
        return value

    def setRepeat(self, name, expr):
        expr = self.evaluate(expr)
        if not expr:
            return self._engine.iteratorFactory(name, (), self)
        it = self._engine.iteratorFactory(name, expr, self)
        old_value = self.repeat_vars.get(name)
        self._scope_stack[-1].append((name, old_value))
        self.repeat_vars[name] = it
        return it

    def evaluate(self, expression):
        if isinstance(expression, str):
            expression = self._engine.compile(expression)
        __traceback_supplement__ = (
           TALESTracebackSupplement, self, expression)
        return expression(self)

    evaluateValue = evaluate

    def evaluateBoolean(self, expr):
        return not not self.evaluate(expr)

    def evaluateText(self, expr):
        text = self.evaluate(expr)
        if text is self.getDefault() or text is None:
            return text
        return unicode(text)

    def evaluateStructure(self, expr):
        return self.evaluate(expr)
    evaluateStructure = evaluate

    def evaluateMacro(self, expr):
        # TODO: Should return None or a macro definition
        return self.evaluate(expr)
    evaluateMacro = evaluate

    def createErrorInfo(self, err, position):
        return ErrorInfo(err, position)

    def getDefault(self):
        return _default

    def setSourceFile(self, source_file):
        self.source_file = source_file

    def setPosition(self, position):
        self.position = position


class TALESTracebackSupplement(object):
    """Implementation of zope.exceptions.ITracebackSupplement"""

    def __init__(self, context, expression):
        self.context = context
        self.source_url = context.source_file
        self.line = context.position[0]
        self.column = context.position[1]
        self.expression = repr(expression)

    def getInfo(self, as_html=0):
        import pprint
        data = self.context.contexts.copy()
        if 'modules' in data:
            del data['modules']     # the list is really long and boring
        s = pprint.pformat(data)
        if not as_html:
            return '   - Names:\n      %s' % s.replace('\n', '\n      ')
        else:
            from cgi import escape
            return '<b>Names:</b><pre>%s</pre>' % (escape(s))
        return None
