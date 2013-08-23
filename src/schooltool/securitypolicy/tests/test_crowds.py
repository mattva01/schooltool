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
Unit tests for schooltool.securitypolicy.crowds
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.component import queryUtility

from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.securitypolicy.crowds import CrowdsUtility, DescriptionUtility
from schooltool.securitypolicy.interfaces import ICrowdsUtility
from schooltool.securitypolicy.interfaces import IDescriptionUtility


def doctest_CrowdsUtility():
    """Doctest for CrowdsUtility.

        >>> cru = CrowdsUtility()
        >>> verifyObject(ICrowdsUtility, cru)
        True
    """


def doctest_getCrowdsUtility():
    """Doctest for getCrowdsUtility.

        >>> from schooltool.securitypolicy.crowds import getCrowdsUtility
        >>> queryUtility(ICrowdsUtility) is None
        True

        >>> cru = getCrowdsUtility()
        >>> print cru
        <schooltool.securitypolicy.crowds.CrowdsUtility object ...>

        >>> queryUtility(ICrowdsUtility) is cru
        True

    """


def doctest_DescriptionUtility():
    """Doctest for DescriptionUtility.

        >>> du = DescriptionUtility()
        >>> verifyObject(IDescriptionUtility, du)
        True

    """


def doctest_getDescriptionUtility():
    """Doctest for getDescriptionUtility.

        >>> from schooltool.securitypolicy.crowds import getDescriptionUtility
        >>> queryUtility(IDescriptionUtility) is None
        True

        >>> du = getDescriptionUtility()
        >>> print du
        <schooltool.securitypolicy.crowds.DescriptionUtility object ...>

        >>> queryUtility(IDescriptionUtility) is du
        True

    """


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

        >>> from schooltool.securitypolicy.crowds import ConfigurableCrowd

    Off we go:

        >>> crowd = ConfigurableCrowd(object())
        >>> crowd.setting_key = 'key'
        >>> crowd.contains(object())
        Getting key
        True

    Clean up:

        >>> setup.placelessTearDown()

    """


def doctest_ParentCrowd():
    """Tests for ParentCrowd.

        >>> setup.placelessSetUp()

        >>> from schooltool.securitypolicy.interfaces import ICrowd
        >>> class ICalendarParentCrowd(ICrowd):
        ...     pass
        >>> class CalendarStub(object):
        ...     def __init__(self, parent):
        ...         self.__parent__ = parent

        >>> from schooltool.securitypolicy.crowds import ParentCrowd
        >>> CalendarViewersCrowd = ParentCrowd(ICalendarParentCrowd,
        ...                                    'schooltool.view')
        >>> crowd = CalendarViewersCrowd(CalendarStub(None))
        >>> crowd.perm = "schooltool.view"

    First, fire a blank (no adapters registered):

        >>> crowd.contains(object())
        False

    OK, let's try with an adaptable object now:

        >>> from schooltool.app.interfaces import ICalendarParentCrowd

        >>> class ParentCrowdStub(object):
        ...     implements(ICalendarParentCrowd)
        ...     def __init__(self, context):
        ...         print 'Getting adapter for %s' % context
        ...     def contains(self, principal):
        ...         print 'Checking %s' % principal
        ...         return True

        >>> from zope.interface import Interface
        >>> class IOwner(Interface):
        ...     pass

        >>> class OwnerStub(object):
        ...     implements(IOwner)

        >>> from zope.component import provideAdapter
        >>> provideAdapter(ParentCrowdStub, adapts=[IOwner],
        ...                provides=ICalendarParentCrowd,
        ...                name='schooltool.view')

    Let's try now with the adapter:

        >>> from schooltool.app.security import CalendarViewersCrowd
        >>> crowd = CalendarViewersCrowd(CalendarStub(OwnerStub()))
        >>> crowd.contains('some principal')
        Getting adapter for <...OwnerStub ...>
        Checking some principal
        True

    Let's try another name:

        >>> CalendarEditorsCrowd = ParentCrowd(ICalendarParentCrowd,
        ...                                    'schooltool.edit')
        >>> crowd = CalendarEditorsCrowd(CalendarStub(OwnerStub()))
        >>> crowd.contains('some principal')
        False

    Now with an adapter in place:

        >>> from zope.component import provideAdapter
        >>> provideAdapter(ParentCrowdStub, adapts=[IOwner],
        ...                provides=ICalendarParentCrowd,
        ...                name='schooltool.edit')
        >>> crowd = CalendarEditorsCrowd(CalendarStub(OwnerStub()))
        >>> crowd.contains('some principal')
        Getting adapter for <...OwnerStub ...>
        Checking some principal
        True

    We're done.

        >>> setup.placefulTearDown()

    """


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS |
                                             doctest.NORMALIZE_WHITESPACE)])
