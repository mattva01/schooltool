##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
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
"""Bootstrap schema interfaces and exceptions

$Id$
"""
import zope.interface

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory("zope")

class StopValidation(Exception):
    """Raised if the validation is completed early.

    Note that this exception should be always caught, since it is just
    a way for the validator to save time.
    """

class ValidationError(zope.interface.Invalid):
    """Raised if the Validation process fails."""

    def doc(self):
        return self.__class__.__doc__

    def __cmp__(self, other):
        return cmp(self.args, other.args)

    def __repr__(self):
        return ' '.join(map(str, self.args))

class RequiredMissing(ValidationError):
    __doc__ = _("""Required input is missing.""")

class WrongType(ValidationError):
    __doc__ = _("""Object is of wrong type.""")

class TooBig(ValidationError):
    __doc__ = _("""Value is too big""")

class TooSmall(ValidationError):
    __doc__ = _("""Value is too small""")

class TooLong(ValidationError):
    __doc__ = _("""Value is too long""")

class TooShort(ValidationError):
    __doc__ = _("""Value is too short""")

class InvalidValue(ValidationError):
    __doc__ = _("""Invalid value""")

class ConstraintNotSatisfied(ValidationError):
    __doc__ = _("""Constraint not satisfied""")

class NotAContainer(ValidationError):
    __doc__ = _("""Not a container""")

class NotAnIterator(ValidationError):
    __doc__ = _("""Not an iterator""")


class IFromUnicode(zope.interface.Interface):
    """Parse a unicode string to a value

    We will often adapt fields to this interface to support views and
    other applications that need to conver raw data as unicode
    values.

    """

    def fromUnicode(str):
        """Convert a unicode string to a value.
        """
