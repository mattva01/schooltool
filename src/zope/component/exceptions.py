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
"""Exceptions used by the Component Architecture

$Id$
"""
from zope.exceptions import NotFoundError

__all__ = ["ComponentLookupError",
           "Invalid",
           "Misused"]

class ComponentLookupError(NotFoundError):
    """A component could not be found."""

class Invalid(Exception):
    """A component doesn't satisfy a promise."""

class Misused(Exception):
    """A component is being used (registered) for the wrong interface."""
