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
Tests for schooltool content provider machinery.
"""
import unittest
import doctest

from zope.tales.tales import CompilerError

from schooltool.app.browser.testing import setUp, tearDown


class PythonExp(object):

    def __init__(self, exp):
        self.exp = exp

    def __call__(self, econtext):
        return eval(self.exp)


class TalVariableExp(object):

    def __init__(self, exp):
        self.exp = exp

    def __call__(self, econtext):
        return econtext.vars[self.exp.strip()]


class TalContext(object):

    def __init__(self, vars=()):
        self.vars = dict(vars)


class TestTalEngine(object):

    def compile(self, expr):
        if expr.startswith('python:'):
            return PythonExp(expr[7:])
        return TalVariableExp(expr)

    def getCompilerError(self):
        return CompilerError


def doctest_JSONEncoder():
    """Tests for JSONEncoder.

        >>> from schooltool.skin.flourish.tal import JSONEncoder

    JSONEncoder is extended version of python's json.JSONEncoder

        >>> import json

        >>> issubclass(JSONEncoder, json.JSONEncoder)
        True

    We can encode some of the standart python types to JSON.

        >>> encoder = JSONEncoder()

        >>> data = {'hello': 'world', 'foo': ('bar', 2, 'baz')}
        >>> encoder.encode(data)
        '{"foo": ["bar", 2, "baz"], "hello": "world"}'

    In addition, we can also encode generators.

        >>> def countme(x):
        ...     for y in range(x):
        ...         yield y

        >>> encoder.encode(countme(5))
        '[0, 1, 2, 3, 4]'

        >>> encoder.encode({'numbers': countme(3)})
        '{"numbers": [0, 1, 2]}'

        >>> print encoder.encode({'Pe/ter': 'Ahmaleethaxor</script>!'})
        {"Pe\\/ter": "Ahmaleethaxor<\\/script>!"}

    """


def doctest_JSONExpression():
    """Tests for JSONExpression.

        >>> from schooltool.skin.flourish.tal import JSONExpression

        >>> engine = TestTalEngine()

    This expression encodes a result of a TAL expression to JSON.

        >>> exp = JSONExpression(
        ...     'json', 'python:{"hello": ("world", )}', engine)

        >>> exp(TalContext())
        '{"hello":["world"]}'

    __str__ and __repr__ looks similar to the rest of TAL expressions.

        >>> print exp
        json expression ('python:{"hello": ("world", )}')

        >>> print repr(exp)
        <JSONExpression json:python:{"hello": ("world", )}>

    """


def doctest_ScriptLocalExpression():
    """Tests for ScriptLocalExpression.

        >>> from schooltool.skin.flourish.tal import ScriptLocalExpression

        >>> engine = TestTalEngine()

        >>> exp = ScriptLocalExpression('scriptlocal',
        ...     'foo python:2*2, 3*5', engine)

        >>> print exp(TalContext())
        <script>$.extend(true,ST.local,{"foo":[4,15]});</script>

        >>> exp = ScriptLocalExpression('scriptlocal',
        ...     'nine python: 3*3;'
        ...     'ten python: 2*5;', engine)

        >>> print exp(TalContext())
        <script>$.extend(true,ST.local,{"nine":9,"ten":10});</script>

        >>> context = TalContext({'name': 'Bob', 'age': 10})

        >>> exp = ScriptLocalExpression('scriptlocal',
        ...     'student name', engine)

        >>> print exp(context)
        <script>$.extend(true,ST.local,{"student":"Bob"});</script>

        >>> exp = ScriptLocalExpression('scriptlocal',
        ...     'name; age', engine)

        >>> print exp(context)
        <script>$.extend(true,ST.local,{"age":10,"name":"Bob"});</script>

    """


def doctest_ScriptLocalExpression_syntax():
    """Tests for ScriptLocalExpression syntax errors.

        >>> from schooltool.skin.flourish.tal import ScriptLocalExpression

        >>> engine = TestTalEngine()

    Bad syntax raises CompilerError:

        >>> ScriptLocalExpression('scriptlocal', 'mumbo+jumbo hey', engine)
        Traceback (most recent call last):
        ...
        CompilerError: Invalid script local expression 'mumbo+jumbo hey'
                       (expected: "js_var_name tales_expression").

        >>> ScriptLocalExpression('scriptlocal', ' good; b?a/d', engine)
        Traceback (most recent call last):
        ...
        CompilerError: Invalid script local expression 'b?a/d'
                       (expected: "js_var_name tales_expression").

    As well as duplicate variable names do:

        >>> ScriptLocalExpression('scriptlocal', 'tony foo; tony bar', engine)
        Traceback (most recent call last):
        ...
        CompilerError: Duplicate javascript variable name 'tony' in
                       'tony foo; tony bar'.

    Variable names cannot start with digits.

        >>> ScriptLocalExpression('scriptlocal', '7bad', engine)
        Traceback (most recent call last):
        ...
        CompilerError: Invalid script local expression '7bad'
                       (expected: "js_var_name tales_expression").

    When tal expression is not specified (it's assumed to be identical
    to the variable name), variable names must be valid TAL variables.

        >>> ScriptLocalExpression('scriptlocal', '$bogus', engine)
        Traceback (most recent call last):
        ...
        CompilerError: When only javascript variable name is specified
                       ('$bogus') it must be a valid TAL variable.

    Names starting with underscore are valid:

        >>> ScriptLocalExpression('scriptlocal', '_hello_world', engine)
        <ScriptLocalExpression ['_hello_world']>

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
