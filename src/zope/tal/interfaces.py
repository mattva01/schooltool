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
"""Interface that a TAL expression implementation provides to the METAL/TAL
implementation.

$Id$
"""
from zope.interface import Attribute, Interface


class ITALExpressionCompiler(Interface):
    """Compile-time interface provided by a TAL expression implementation.

    The TAL compiler needs an instance of this interface to support
    compilation of TAL expressions embedded in documents containing
    TAL and METAL constructs.
    """

    def getCompilerError():
        """Return the exception class raised for compilation errors.
        """

    def compile(expression):
        """Return a compiled form of 'expression' for later evaluation.

        'expression' is the source text of the expression.

        The return value may be passed to the various evaluate*()
        methods of the ITALExpressionEngine interface.  No compatibility is
        required for the values of the compiled expression between
        different ITALExpressionEngine implementations.
        """

    def getContext(namespace):
        """Create an expression execution context

        The given namespace provides the initial top-level names.
        """

class ITALExpressionEngine(Interface):
    """Render-time interface provided by a TAL expression implementation.

    The TAL interpreter uses this interface to TAL expression to support
    evaluation of the compiled expressions returned by
    ITALExpressionCompiler.compile().
    """

    def getDefault():
        """Return the value of the 'default' TAL expression.

        Checking a value for a match with 'default' should be done
        using the 'is' operator in Python.
        """

    def setPosition((lineno, offset)):
        """Inform the engine of the current position in the source file.

        This is used to allow the evaluation engine to report
        execution errors so that site developers can more easily
        locate the offending expression.
        """

    def setSourceFile(filename):
        """Inform the engine of the name of the current source file.

        This is used to allow the evaluation engine to report
        execution errors so that site developers can more easily
        locate the offending expression.
        """

    def beginScope():
        """Push a new scope onto the stack of open scopes.
        """

    def endScope():
        """Pop one scope from the stack of open scopes.
        """

    def evaluate(compiled_expression):
        """Evaluate an arbitrary expression.

        No constraints are imposed on the return value.
        """

    def evaluateBoolean(compiled_expression):
        """Evaluate an expression that must return a Boolean value.
        """

    def evaluateMacro(compiled_expression):
        """Evaluate an expression that must return a macro program.
        """

    def evaluateStructure(compiled_expression):
        """Evaluate an expression that must return a structured
        document fragment.

        The result of evaluating 'compiled_expression' must be a
        string containing a parsable HTML or XML fragment.  Any TAL
        markup contained in the result string will be interpreted.
        """

    def evaluateText(compiled_expression):
        """Evaluate an expression that must return text.

        The returned text should be suitable for direct inclusion in
        the output: any HTML or XML escaping or quoting is the
        responsibility of the expression itself.

        If the expression evaluates to None, then that is returned. It
        represents 'nothing' in TALES.
        If the expression evaluates to what getDefault() of this interface
        returns, by comparison using 'is', then that is returned. It
        represents 'default' in TALES.
        """

    def evaluateValue(compiled_expression):
        """Evaluate an arbitrary expression.

        No constraints are imposed on the return value.
        """

    def createErrorInfo(exception, (lineno, offset)):
        """Returns an ITALExpressionErrorInfo object.

        The returned object is used to provide information about the
        error condition for the on-error handler.
        """

    def setGlobal(name, value):
        """Set a global variable.

        The variable will be named 'name' and have the value 'value'.
        """

    def setLocal(name, value):
        """Set a local variable in the current scope.

        The variable will be named 'name' and have the value 'value'.
        """

    def getValue(name, default=None):
        """Get a variable by name.

        If the variable does not exist, return default.
        """

    def setRepeat(name, compiled_expression):
        """Start a repetition, returning an ITALIterator.

        The engine is expected to add the a value (typically the
        returned iterator) for the name to the variable namespace.
        """

    def translate(msgid, domain=None, mapping=None, default=None):
        """See zope.i18n.interfaces.ITranslationDomain.translate"""

    def evaluateCode(lang, code):
        """Evaluates code of the given language.

        Returns whatever the code outputs. This can be defined on a
        per-language basis. In Python this usually everything the print
        statement will return.
        """
        

class ITALIterator(Interface):
    """A TAL iterator

    Not to be confused with a Python iterator.
    """

    def next():
        """Advance to the next value in the iteration, if possible

        Return a true value if it was possible to advance and return
        a false value otherwise.
        """


class ITALExpressionErrorInfo(Interface):

    type = Attribute("type",
                     "The exception class.")

    value = Attribute("value",
                      "The exception instance.")

    lineno = Attribute("lineno",
                       "The line number the error occurred on in the source.")

    offset = Attribute("offset",
                       "The character offset at which the error occurred.")
