##############################################################################
#
# Copyright (c) 2002, 2003 Zope Corporation and Contributors.
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
"""Configuration data structures and loader for the ZRS.

$Id: __init__.py,v 1.10 2003/08/01 20:41:59 fdrake Exp $
"""
from ZConfig.loader import loadConfig, loadConfigFile
from ZConfig.loader import loadSchema, loadSchemaFile

class ConfigurationError(Exception):
    def __init__(self, msg):
        self.message = msg
        Exception.__init__(self, msg)

    def __str__(self):
        return self.message


class _ParseError(ConfigurationError):
    def __init__(self, msg, url, lineno, colno=None):
        self.url = url
        self.lineno = lineno
        self.colno = colno
        ConfigurationError.__init__(self, msg)

    def __str__(self):
        s = self.message
        if self.url:
            s += "\n("
        elif (self.lineno, self.colno) != (None, None):
            s += " ("
        if self.lineno:
            s += "line %d" % self.lineno
            if self.colno is not None:
                s += ", column %d" % self.colno
            if self.url:
                s += " in %s)" % self.url
            else:
                s += ")"
        elif self.url:
            s += self.url + ")"
        return s


class SchemaError(_ParseError):
    """Raised when there's an error in the schema itself."""

    def __init__(self, msg, url=None, lineno=None, colno=None):
        _ParseError.__init__(self, msg, url, lineno, colno)


class ConfigurationMissingSectionError(ConfigurationError):
    def __init__(self, type, name=None):
        self.type = type
        self.name = name
        details = 'Missing section (type: %s' % type
        if name is not None:
            details += ', name: %s' % name
        ConfigurationError.__init__(self, details + ')')


class ConfigurationConflictingSectionError(ConfigurationError):
    def __init__(self, type, name=None):
        self.type = type
        self.name = name
        details = 'Conflicting sections (type: %s' % type
        if name is not None:
            details += ', name: %s' % name
        ConfigurationError.__init__(self, details + ')')


class ConfigurationSyntaxError(_ParseError):
    """Raised when there's a syntax error in a configuration file."""


class ConfigurationTypeError(ConfigurationError):
    def __init__(self, msg, found, expected):
        self.found = found
        self.expected = expected
        ConfigurationError.__init__(self, msg)


class DataConversionError(ConfigurationError, ValueError):
    """Raised when a data type conversion function raises ValueError."""

    def __init__(self, exception, value, position):
        ConfigurationError.__init__(self, str(exception))
        self.exception = exception
        self.value = value
        self.lineno, self.colno, self.url = position

    def __str__(self):
        s = "%s (line %s" % (self.message, self.lineno)
        if self.colno is not None:
            s += ", %s" % self.colno
        if self.url:
            s += ", in %s)" % self.url
        else:
            s += ")"
        return s


class SubstitutionSyntaxError(ConfigurationError):
    """Raised when interpolation source text contains syntactical errors."""


class SubstitutionReplacementError(ConfigurationSyntaxError, LookupError):
    """Raised when no replacement is available for a reference."""

    def __init__(self, source, name, url=None, lineno=None):
        self.source = source
        self.name = name
        ConfigurationSyntaxError.__init__(
            self, "no replacement for " + `name`, url, lineno)
