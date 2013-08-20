#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool flourish tal expressions.
"""
import re
import types
import json

import zc.resourcelibrary
import zope.tal.taldefs
from zope.interface import implements
from zope.tales.interfaces import ITALESExpression


class JSONEncoder(json.JSONEncoder):

    _slash_re = re.compile('/')

    def encode(self, ob):
        result = json.JSONEncoder.encode(self, ob)
        return self._slash_re.sub('\/', result)

    def default(self, ob):
        if type(ob) == types.GeneratorType:
            return list(ob)
        return json.JSONEncoder.default(self, ob)


class JSONDecoder(json.JSONDecoder):
    pass


class JSONExpression(object):
    implements(ITALESExpression)

    def __init__(self, name, expr, engine):
        self.name = name
        self.expr = expr
        self.compiled = engine.compile(expr)
        self.encoder = JSONEncoder(sort_keys=True, separators=(',', ':'))

    def __call__(self, econtext):
        ob = self.compiled(econtext)
        return self.encoder.encode(ob)

    def __str__(self):
        return '%s expression (%r)' % (self.name, self.expr)

    def __repr__(self):
        return '<%s %s:%s>' % (self.__class__.__name__, self.name, self.expr)


_scriptlocal_exp = re.compile(
    '\s*(?:(?P<var>[a-zA-Z_$][\w$]*)(?:\s|$))(?:\s*(?P<expr>.*))?\s*')


_tal_name_re = re.compile('^%s$' % zope.tal.taldefs.NAME_RE)

class ScriptLocalExpression(object):
    implements(ITALESExpression)

    compiled = None
    exps = None

    script_template = '<script>$.extend(true,ST.local,%s);</script>'

    def __init__(self, name, expr, engine):
        self.exps = filter(None, [s.strip() for s in expr.split(';')])
        self.compile(self.exps, engine)
        self.encoder = JSONEncoder(sort_keys=True, separators=(',', ':'))

    def extract(self, exp, engine):
        match = _scriptlocal_exp.match(exp)
        if match is None:
            raise engine.getCompilerError()(
                ('Invalid script local expression %r'
                 ' (expected: "js_var_name tales_expression").') % exp)
        parts = match.groupdict()
        js_name = parts['var']
        if not js_name:
            raise engine.getCompilerError()(
                'Missing/invalid javascript variable name %r.' % exp)
        tal_exp = parts['expr']
        if not tal_exp:
            if not _tal_name_re.match(js_name):
                raise engine.getCompilerError()(
                    ('When only javascript variable name is specified (%r)'
                     ' it must be a valid TAL variable.') % exp)
            tal_exp = js_name
        return (js_name, tal_exp)

    def compile(self, expressions, engine):
        self.compiled = {}
        for subexp in expressions:
            js_name, tal_exp = self.extract(subexp, engine)
            if js_name in self.compiled:
                raise engine.getCompilerError()(
                    'Duplicate javascript variable name %r in %r.' % (
                        js_name, '; '.join(expressions)))
            self.compiled[js_name] = engine.compile(tal_exp)

    def __call__(self, econtext):
        if not self.compiled:
            return ''
        zc.resourcelibrary.need('schooltool.skin.flourish-scripts')
        vars = {}
        for js_var, exp in self.compiled.items():
            vars[js_var] = exp(econtext)
        return self.script_template % self.encoder.encode(vars)

    def __str__(self):
        return 'scriptlocal expressions (%s)' % list(self.exps)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, list(self.exps))
