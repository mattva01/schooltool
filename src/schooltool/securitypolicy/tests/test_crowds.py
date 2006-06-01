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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for schooltool.securitypolicy.crowds

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.app.interfaces import ISchoolToolApplication
from zope.interface import implements


def doctest_AggregateCrowd():
    """Doctests for AggregateCrowd.

    What's so special about this adapter?  It aggregates crowds retrieved from
    objcrowds:

        >>> class CrowdStub(object):
        ...     def __init__(self, context):
        ...         pass
        ...     def contains(self, principal):
        ...         print 'contains(%s)' % principal
        ...         return principal == 'r00t'

    The crowdFactories method is normally overridden:

        >>> from schooltool.securitypolicy.crowds import AggregateCrowd
        >>> adapter = AggregateCrowd(object())

        >>> adapter.crowdFactories = lambda: [CrowdStub]

        >>> adapter.contains('some principal')
        contains(some principal)
        False

        >>> adapter.contains('r00t')
        contains(r00t)
        True

    """


def doctest_ConfigurableCrowd():
    """Tests for ConfigurableCrowd.

    Some setup:

        >>> setup.placelessSetUp()
        >>> class CustomisationsStub(object):
        ...     implements(IAccessControlCustomisations)
        ...     def get(self, key):
        ...         print 'Getting %s' % key
        ...         return True

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication)
        ...     def __conform__(self, iface):
        ...         if iface == IAccessControlCustomisations:
        ...             return CustomisationsStub()

        >>> from zope.component import provideAdapter
        >>> provideAdapter(lambda context: AppStub(),
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> from schooltool.app.security import ConfigurableCrowd

    Off we go:

        >>> crowd = ConfigurableCrowd(object())
        >>> crowd.setting_key = 'key'
        >>> crowd.contains(object())
        Getting key
        True

    Clean up:

        >>> setup.placelessTearDown()

    """


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS |
                                             doctest.NORMALIZE_WHITESPACE)])
