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
Unit tests for schooltool.securitypolicy.policy

$Id$
"""

import unittest
from zope.testing import doctest
from zope.interface import implements, Interface
from zope.interface.verify import verifyObject
from zope.app.testing import setup
from zope.app.testing import ztapi
from zope.component import getAdapter
from schooltool.securitypolicy import metaconfigure as mc
from schooltool.securitypolicy.metaconfigure import CrowdsUtility
from schooltool.securitypolicy.interfaces import ICrowdsUtility
from zope.app import zapi


def doctest_CrowdsUtility():
    """Doctest for CrowdsUtility.

        >>> cru = CrowdsUtility()
        >>> verifyObject(ICrowdsUtility, cru)
        True
    """


def doctest_getCrowdsUtility():
    """Doctest for getCrowdsUtility.

        >>> from schooltool.securitypolicy.metaconfigure import getCrowdsUtility
        >>> zapi.queryUtility(ICrowdsUtility) is None
        True

        >>> cru = getCrowdsUtility()
        >>> print cru
        <schooltool.securitypolicy.metaconfigure.CrowdsUtility object ...>

        >>> zapi.queryUtility(ICrowdsUtility) is cru
        True
    """


def doctest_registerCrowdAdapter():
    """Doctests for registerCrowdAdapter.

        >>> from schooltool.securitypolicy import metaconfigure
        >>> from schooltool.securitypolicy.interfaces import ICrowd
        >>> cru = CrowdsUtility()
        >>> ztapi.provideUtility(ICrowdsUtility, cru)

        >>> class IMyObject(Interface):
        ...     pass

    Let's invoke registerCrowdAdapter:

        >>> metaconfigure.registerCrowdAdapter(IMyObject, 'perm')

    An adapter should have been registered.

        >>> class MyObject(object):
        ...     implements(IMyObject)
        >>> obj = MyObject()
        >>> adapter = getAdapter(obj, ICrowd, name='perm')
        >>> adapter
        <...AggregateCrowdAdapter...>

    What's so special about this adapter?  It aggregates crowds retrieved from
    objcrowds:

        >>> class CrowdStub(object):
        ...     def __init__(self, context):
        ...         pass
        ...     def contains(self, principal):
        ...         print 'contains(%s)' % principal
        ...         return principal == 'r00t'
        >>> cru.objcrowds = {(IMyObject, 'perm'): [CrowdStub]}

        >>> adapter.contains('some principal')
        contains(some principal)
        False

        >>> adapter.contains('r00t')
        contains(r00t)
        True
    """


def doctest_handle_crowd():
    """Doctest for handle_crowd

        >>> from schooltool.securitypolicy.metaconfigure import handle_crowd
        >>> cru = CrowdsUtility()
        >>> ztapi.provideUtility(ICrowdsUtility, cru)

        >>> handle_crowd('cr1', 'fac1')
        >>> print sorted(cru.crowdmap.keys())
        ['cr1']
        >>> cru.crowdmap['cr1']
        'fac1'
    """


def doctest_handle_allow():
    """Tests for handle_allow.

        >>> from schooltool.securitypolicy import metaconfigure as mc

        >>> cru = CrowdsUtility()
        >>> cru.crowdmap = {'cr1': 'fac1',
        ...                 'cr2': 'fac2',
        ...                 'cr3': 'fac3'}
        >>> ztapi.provideUtility(ICrowdsUtility, cru)
        >>> def registerCrowdAdapterStub(iface, permission):
        ...     print 'registerCrowdAdapter' + str((iface, permission))

        >>> mc.registerCrowdAdapter = registerCrowdAdapterStub

    First check a simple declaration:

        >>> mc.handle_allow('iface', 'cr1', 'my.permission')
        registerCrowdAdapter('iface', 'my.permission')
        >>> mc.handle_allow('iface', 'cr2', 'my.permission')

        >>> cru.objcrowds
        {('iface', 'my.permission'): ['fac1', 'fac2']}

    Another call will not invoke registerCrowdAdapter again:

        >>> mc.handle_allow('iface', 'cr3', 'my.permission')
        >>> cru.objcrowds
        {('iface', 'my.permission'): ['fac1', 'fac2', 'fac3']}

    Let's check the case when an interface is not provided:

        >>> mc.handle_allow(None, 'cr1', 'my.permission')
        >>> cru.permcrowds
        {'my.permission': ['fac1']}

        >>> mc.handle_allow(None, 'cr2', 'my.permission')
        >>> cru.permcrowds
        {'my.permission': ['fac1', 'fac2']}

    """


def doctest_crowd():
    """Doctests for crowd

        >>> from schooltool.securitypolicy.metaconfigure import crowd
        >>> class ContextStub(object):
        ...     def action(self, discriminator, callable, args):
        ...         print discriminator
        ...         print callable
        ...         print args

        >>> _context = ContextStub()
        >>> crowd(_context, 'ipqs', 'ipqsfactory')
        ('Crowd', 'ipqs')
        <function handle_crowd at ...>
        ('ipqs', 'ipqsfactory')
    """


def doctest_allow():
    """Doctests for allow

        >>> from schooltool.securitypolicy.metaconfigure import allow
        >>> class ContextStub(object):
        ...     def action(self, discriminator, callable, args):
        ...         print discriminator, callable, args

        >>> _context = ContextStub()
        >>> allow(_context, 'interface', ['ipqs', 'ecug'], 'do')
        ('Allow', 'interface', 'ipqs', 'do') <function handle_allow ...> ('interface', 'ipqs', 'do')
        ('Allow', 'interface', 'ecug', 'do') <function handle_allow ...> ('interface', 'ecug', 'do')

    """


def doctest_AccessControlSetting():
    """Doctests for AccessControlSetting.

        >>> from schooltool.securitypolicy.metaconfigure import AccessControlSetting
        >>> setting = AccessControlSetting("key", "Some text", False)

    Setting should implement the IAccessControlSetting interface:

        >>> from schooltool.securitypolicy.interfaces import IAccessControlSetting
        >>> verifyObject(IAccessControlSetting, setting)
        True

    getValue is just a wrapper for the get method of the
    adapter from schooltool application to IAccessControlCustomisations:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
        >>> class CustomisationsStub(object):
        ...     implements(IAccessControlCustomisations)
        ...     def get(self, key):
        ...         return "Value for setting: %s" % key
        ...     def set(self, key, value):
        ...         return "Setting value of %s to %s" % (key, value)

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication)
        ...     def __conform__(self, iface):
        ...         if iface == IAccessControlCustomisations:
        ...             return CustomisationsStub()

        >>> from zope.component import provideAdapter
        >>> provideAdapter(lambda context: AppStub(),
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> setting.getValue()
        'Value for setting: key'

    We can set the value of the setting directly as well:

        >>> setting.setValue("new value")
        'Setting value of key to new value'

    """


def doctest_handle_setting():
    """Tests for handle_setting.

        >>> from schooltool.securitypolicy.metaconfigure import handle_setting

    Handle setting should register a subscriber adapter for
    IAccessControlSetting interface, initially there are no subscribers:

        >>> from zope.component import subscribers
        >>> from schooltool.securitypolicy.interfaces import IAccessControlSetting
        >>> subscribers([None], IAccessControlSetting)
        []

        >>> handle_setting("key", "text", False)

    Now we should have one:

        >>> subscribers([None], IAccessControlSetting)
        [<AccessControlSetting key=key, text=text, default=False>]

    Let's add another one:

        >>> handle_setting("another_key", "more text", True)
        >>> subscribers([None], IAccessControlSetting)
        [<AccessControlSetting key=key, text=text, default=False>,
         <AccessControlSetting key=another_key, text=more text, default=True>]

    """


class Fixture(object):

    def setUp(self, test=None):
        setup.placelessSetUp()
        self.oldRegisterCrowdAdapter = mc.registerCrowdAdapter

    def tearDown(self, test=None):
        setup.placelessTearDown()
        mc.registerCrowdAdapter = self.oldRegisterCrowdAdapter


def test_suite():
    f = Fixture()
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS |
                                             doctest.NORMALIZE_WHITESPACE,
                                 setUp=f.setUp, tearDown=f.tearDown)])

