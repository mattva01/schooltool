#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Tests for customisation of SchoolTool security policy.
"""

import unittest
import doctest


def doctest_AccessControlCustomisations():
    r"""Tests for AccessControlCustomisations.

        >>> from schooltool.securitypolicy.customisation import AccessControlCustomisations
        >>> from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
        >>> from zope.interface.verify import verifyObject
        >>> customisations = AccessControlCustomisations()
        >>> verifyObject(IAccessControlCustomisations, customisations)
        True

    Iterating through customisations should yield us a list of all
    AccessControlSettings, there are none yet:

        >>> list(customisations)
        []

    Let's register a couple of settings:

        >>> class SettingStub(object):
        ...     def __init__(self, key, default=False):
        ...         self.default = default
        ...         self.key = key
        ...     def __repr__(self):
        ...         return "<SettingStub default=%s, key=%s>" % (self.default,
        ...                                                      self.key)

        >>> from zope.component import provideSubscriptionAdapter
        >>> from schooltool.securitypolicy.interfaces import IAccessControlSetting
        >>> for key, default in [("key1", False),
        ...                      ("key2", True)]:
        ...     provideSubscriptionAdapter(lambda c, k=key, d=default: SettingStub(k, d),
        ...                                adapts=[None],
        ...                                provides=IAccessControlSetting)

        >>> list(customisations)
        [<SettingStub default=False, key=key1>,
         <SettingStub default=True, key=key2>]

    If there is no value for a setting defined yet, we should get the
    default:

        >>> customisations.get("key1")
        False
        >>> customisations.get("key2")
        True

    If there is no such key, raise a KeyError:

        >>> customisations.get("key3")
        Traceback (most recent call last):
        ...
        KeyError: 'there is no AccessControlSetting associated with this key.'

    We can assign some value to existing keys by using the set method:

        >>> customisations.set("key1", True)
        >>> customisations.set("key2", False)

        >>> customisations.get("key1")
        True
        >>> customisations.get("key2")
        False

    It should raise a key error for unrecognized keys too:

        >>> customisations.set("key3", True)
        Traceback (most recent call last):
        ...
        KeyError: 'there is no AccessControlSetting associated with this key.'

    """


def doctest_getAccessControlCustomisations():
    """Tests for getAccessControlCustomisations.

        >>> from schooltool.securitypolicy.customisation import getAccessControlCustomisations

    Customisations should be stored in annotations of a schooltool
    application, or created on the first access if they are not there:

        >>> from zope.annotation.interfaces import IAnnotations
        >>> annotations = {}
        >>> class AppStub(object):
        ...     def __conform__(self, iface):
        ...         if iface == IAnnotations:
        ...             return annotations

        >>> customisations = getAccessControlCustomisations(AppStub())
        >>> print customisations
        <schooltool.securitypolicy.customisation.AccessControlCustomisations ...>

    On subsequent calls we should get the same customisations object:

        >>> customisations is getAccessControlCustomisations(AppStub())
        True

    The key for customisations is
    'schooltool.securitypolicy.AccessControlCustomisations':

        >>> annotations
        {'schooltool.securitypolicy.AccessControlCustomisations':
         <schooltool.securitypolicy.customisation.AccessControlCustomisations ...}

    """


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS |
                                             doctest.NORMALIZE_WHITESPACE)])
