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
"""Generic Python Expression Handler

$Id: pythonexpr.py,v 1.2 2004/03/21 16:55:50 philikon Exp $
"""

class PythonExpr:
    def __init__(self, name, expr, engine):
        text = expr.replace('\n', ' ').strip()
        self.text = text
        # The next line can legally raise SyntaxError.
        self._code = code = compile(text, '<string>', 'eval')
        self._varnames = code.co_names

    def _bind_used_names(self, econtext, builtins):
        # Bind template variables
        names = {}
        vars = econtext.vars
        marker = self
        for vname in self._varnames:
            val = vars.get(vname, marker)
            if val is not marker:
                names[vname] = val
            elif vname not in builtins:
                # Fall back to using expression types as variable values.
                val = econtext._engine.getTypes().get(vname, marker)
                if val is not marker:
                    val = ExprTypeProxy(vname, val, econtext)
                    names[vname] = val

        names['__builtins__'] = builtins
        return names

    def __call__(self, econtext):
        __traceback_info__ = self.text
        vars = self._bind_used_names(econtext, __builtins__)
        return eval(self._code, vars)

    def __str__(self):
        return 'Python expression "%s"' % self.text

    def __repr__(self):
        return '<PythonExpr %s>' % self.text


class ExprTypeProxy:
    '''Class that proxies access to an expression type handler'''
    def __init__(self, name, handler, econtext):
        self._name = name
        self._handler = handler
        self._econtext = econtext

    def __call__(self, text):
        return self._handler(self._name, text,
                             self._econtext._engine)(self._econtext)
