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
"""Page Template module

HTML- and XML-based template objects using TAL, TALES, and METAL.

$Id: pagetemplate.py,v 1.10 2004/03/19 23:35:03 srichter Exp $
"""
__metaclass__ = type # All classes are new style when run with Python 2.2+

import sys
from zope.tal.talparser import TALParser
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter
from zope.tales.engine import Engine
# Don't use cStringIO here!  It's not unicode aware.
from StringIO import StringIO


class MacroCollection:
    def __get__(self, parent, type=None):
        parent._cook_check()
        return parent._v_macros


_default_options = {}

class PageTemplate:
    """Page Templates using TAL, TALES, and METAL.

    Subclassing
    -----------

    The following methods have certain internal responsibilities.

    pt_getContext(**keywords)
        Should ignore keyword arguments that it doesn't care about,
        and construct the namespace passed to the TALES expression
        engine.  This method is free to use the keyword arguments it
        receives.

    pt_render(namespace, source=0)
        Responsible the TAL interpreter to perform the rendering.  The
        namespace argument is a mapping which defines the top-level
        namespaces passed to the TALES expression engine.

    __call__(*args, **keywords)
        Calls pt_getContext() to construct the top-level namespace
        passed to the TALES expression engine, then calls pt_render()
        to perform the rendering.
    """
    content_type = 'text/html'
    expand = 1
    _v_errors = ()
    _v_warnings = ()
    _v_program = None
    _v_macros = None
    _v_cooked = 0
    _text = ''
    _engine_name = 'default'
    _error_start = '<!-- Page Template Diagnostics'

    macros = MacroCollection()

    def pt_edit(self, text, content_type):
        if content_type:
            self.content_type = str(content_type)
        if hasattr(text, 'read'):
            text = text.read()
        self.write(text)

    def pt_getContext(self, args=(), options=_default_options, **ignored):
        rval = {'template': self,
                'options': options,
                'args': args,
                'nothing': None,
                'usage': TemplateUsage(options.get("template_usage", u'')),
                }
        rval.update(self.pt_getEngine().getBaseNames())
        return rval

    def __call__(self, *args, **kwargs):
        return self.pt_render(self.pt_getContext(args, kwargs))

    pt_getEngineContext = Engine.getContext

    def pt_getEngine(self):
        return Engine

    def pt_render(self, namespace, source=False):
        """Render this Page Template"""
        self._cook_check()
        __traceback_supplement__ = (PageTemplateTracebackSupplement,
                                    self, namespace)
        if self._v_errors:
            raise PTRuntimeError(str(self._v_errors))

        output = StringIO(u'')
        context = self.pt_getEngineContext(namespace)
        TALInterpreter(self._v_program, self._v_macros,
                       context, output, tal=not source, strictinsert=0)()
        return output.getvalue()

    def pt_errors(self, namespace):
        self._cook_check()
        err = self._v_errors
        if err:
            return err
        try:
            self.pt_render(namespace, source=1)
        except:
            return ('Macro expansion failed', '%s: %s' % sys.exc_info()[:2])

    def pt_warnings(self):
        self._cook_check()
        return self._v_warnings

    def write(self, text):
        # We accept both, since the text can either come from a file (and the
        # parser will take are of the encoding or from a TTW template, in
        # which case we have already unicode. 
        assert isinstance(text, (str, unicode))

        if text.startswith(self._error_start):
            errend = text.find('-->')
            if errend >= 0:
                text = text[errend + 4:]
        if self._text != text:
            self._text = text
        # XXX can this be done only if we changed self._text?
        self._cook()

    def read(self):
        """Gets the source, sometimes with macros expanded."""
        self._cook_check()
        if not self._v_errors:
            if not self.expand:
                return self._text
            try:
                # XXX not clear how this ever gets called, but the
                # first arg to pt_render() needs to change if it ever does.
                return self.pt_render({}, source=1)
            except:
                return ('%s\n Macro expansion failed\n %s\n-->\n%s' %
                        (self._error_start, "%s: %s" % sys.exc_info()[:2],
                         self._text) )

        return ('%s\n %s\n-->\n%s' % (self._error_start,
                                      '\n'.join(self._v_errors),
                                      self._text))

    def pt_source_file(self):
        """To be overridden."""
        return None

    def _cook_check(self):
        if not self._v_cooked:
            self._cook()

    def _cook(self):
        """Compile the TAL and METAL statments.

        Cooking must not fail due to compilation errors in templates.
        """
        engine = self.pt_getEngine()
        source_file = self.pt_source_file()
        if self.html():
            gen = TALGenerator(engine, xml=0, source_file=source_file)
            parser = HTMLTALParser(gen)
        else:
            gen = TALGenerator(engine, source_file=source_file)
            parser = TALParser(gen)

        self._v_errors = ()
        try:
            parser.parseString(self._text)
            self._v_program, self._v_macros = parser.getCode()
        except:
            self._v_errors = ["Compilation failed",
                              "%s: %s" % sys.exc_info()[:2]]
        self._v_warnings = parser.getWarnings()
        self._v_cooked = 1

    def html(self):
        if not hasattr(self, 'is_html'):
            return self.content_type == 'text/html'
        return self.is_html


class TemplateUsage:
    def __init__(self, value):
        if not isinstance(value, unicode):
            raise TypeError('TemplateUsage should be initialized with a '
                            'Unicode string',
                            repr(value))
        self.stringValue = value

    def __str__(self):
        return self.stringValue

    def __getitem__(self, key):
        if key == self.stringValue:
            return self.stringValue
        else:
            return None

    def __nonzero__(self):
        return self.stringValue <> u''



class PTRuntimeError(RuntimeError):
    '''The Page Template has template errors that prevent it from rendering.'''
    pass


class PageTemplateTracebackSupplement:
    #implements(ITracebackSupplement)

    def __init__(self, pt, namespace):
        self.manageable_object = pt
        try:
            w = pt.pt_warnings()
        except: # We're already trying to report an error, don't make another.
            w = ()
        e = pt.pt_errors(namespace)
        if e:
            w = list(w) + list(e)
        self.warnings = w
