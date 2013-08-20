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
Unit tests for schooltool.securitypolicy.metaconfigure
"""
import unittest
import doctest

from zope.interface import implements, Interface
from zope.interface.verify import verifyObject
from zope.app.testing import setup
from zope.component import getAdapter, provideUtility
from zope.component import queryUtility

from schooltool.securitypolicy import metaconfigure as mc
from schooltool.securitypolicy.crowds import CrowdsUtility
from schooltool.securitypolicy.interfaces import ICrowdsUtility


def doctest_CrowdsUtility():
    """Doctest for CrowdsUtility.

        >>> cru = CrowdsUtility()
        >>> verifyObject(ICrowdsUtility, cru)
        True

    """


def doctest_getCrowdsUtility():
    """Doctest for getCrowdsUtility.

        >>> from schooltool.securitypolicy.metaconfigure import getCrowdsUtility
        >>> queryUtility(ICrowdsUtility) is None
        True

        >>> cru = getCrowdsUtility()
        >>> print cru
        <schooltool.securitypolicy.crowds.CrowdsUtility object ...>

        >>> queryUtility(ICrowdsUtility) is cru
        True

    """


def doctest_registerCrowdAdapter():
    """Doctests for registerCrowdAdapter.

        >>> from schooltool.securitypolicy import metaconfigure
        >>> from schooltool.securitypolicy.interfaces import ICrowd
        >>> cru = CrowdsUtility()

        >>> cru.factories = {
        ...     'crowd A': 'Factory A',
        ...     'crowd B': 'Factory B',
        ...     }

        >>> provideUtility(cru, provides=ICrowdsUtility)

        >>> class IMyObject(Interface):
        ...     pass

    Let's invoke registerCrowdAdapter:

        >>> metaconfigure.registerCrowdAdapter('perm', IMyObject)

    An adapter should have been registered.

        >>> class MyObject(object):
        ...     implements(IMyObject)
        >>> obj = MyObject()
        >>> adapter = getAdapter(obj, ICrowd, name='perm')
        >>> adapter
        <AggregateCrowd crowds=[]>

        >>> cru.crowds = {('perm', IMyObject): ['crowd A', 'crowd B']}
        >>> adapter.crowdFactories()
        ['Factory A', 'Factory B']

    """


def doctest_handle_crowd():
    """Doctest for handle_crowd

        >>> from schooltool.securitypolicy.metaconfigure import handle_crowd
        >>> cru = CrowdsUtility()
        >>> provideUtility(cru, provides=ICrowdsUtility)

        >>> handle_crowd('cr1', 'fac1')
        >>> print sorted(cru.factories.keys())
        ['cr1']
        >>> cru.factories['cr1']
        'fac1'
    """


def doctest_handle_allow():
    """Tests for handle_allow.

        >>> cru = CrowdsUtility()
        >>> cru.factories = {'cr1': 'Factory 1',
        ...                  'cr2': 'Factory 2',
        ...                  'cr3': 'Factory 3'}

        >>> provideUtility(cru, provides=ICrowdsUtility)
        >>> def registerCrowdAdapterStub(permission, iface):
        ...     print 'registerCrowdAdapter' + str((iface, permission))

        >>> mc.registerCrowdAdapter = registerCrowdAdapterStub

    First check a simple declaration:

        >>> mc.handle_allow('cr1', 'my.permission', 'iface')
        registerCrowdAdapter('iface', 'my.permission')
        >>> mc.handle_allow('cr2', 'my.permission', 'iface')

        >>> def printCrowds():
        ...     for discriminator, names in sorted(cru.crowds.items()):
        ...         print '%s: %s' % (discriminator, names)

        >>> printCrowds()
        ('my.permission', 'iface'): ['cr1', 'cr2']

    Another call will not invoke registerCrowdAdapter again:

        >>> mc.handle_allow('cr3', 'my.permission', 'iface')
        >>> printCrowds()
        ('my.permission', 'iface'): ['cr1', 'cr2', 'cr3']

    Crowd factories for the registered permission/interface pair
    can be obtained:

        >>> cru.getFactories('my.permission', 'iface')
        ['Factory 1', 'Factory 2', 'Factory 3']

    Passing a name that does not exist yet to the allow declaration
    will work as the actual lookup is postponed:

        >>> mc.handle_allow('cr4', 'my.permission', 'iface')
        >>> printCrowds()
        ('my.permission', 'iface'): ['cr1', 'cr2', 'cr3', 'cr4']

    But if you try to look up crowd factories you will get a key error:

        >>> cru.getFactories('my.permission', 'iface')
        Traceback (most recent call last):
        ...
        CrowdNotRegistered: cr4

    Let's check the case when an interface is not provided:

        >>> mc.handle_allow('cr1', 'my.permission', None)
        >>> printCrowds()
        ('my.permission', None): ['cr1']
        ('my.permission', 'iface'): ['cr1', 'cr2', 'cr3', 'cr4']

        >>> mc.handle_allow('cr2', 'my.permission', None)
        >>> printCrowds()
        ('my.permission', None): ['cr1', 'cr2']
        ('my.permission', 'iface'): ['cr1', 'cr2', 'cr3', 'cr4']

        >>> cru.getFactories('my.permission', None)
        ['Factory 1', 'Factory 2']

    """


class ContextStub(object):
    def action(self, discriminator, callable, args):
        print discriminator
        print callable
        print args
        print '---'


def doctest_crowd():
    """Doctests for crowd

        >>> from schooltool.securitypolicy.metaconfigure import crowd

        >>> _context = ContextStub()
        >>> crowd(_context, 'ipqs', 'ipqsfactory')
        ('crowd', 'ipqs')
          <function handle_crowd at ...>
          ('ipqs', 'ipqsfactory')
        ---

    """


def doctest_handle_aggregate_crowd():
    """Doctests for handle_aggregate_crowd.

        >>> cru = CrowdsUtility()
        >>> cru.factories['old1'] = 'crowd A'
        >>> cru.factories['old2'] = 'crowd B'
        >>> provideUtility(cru, provides=ICrowdsUtility)

        >>> from schooltool.securitypolicy import metaconfigure
        >>> metaconfigure.handle_aggregate_crowd('newcrowd', ['old1', 'old2'])

        >>> factory = cru.factories['newcrowd']
        >>> factory(None).crowdFactories()
        ['crowd A', 'crowd B']

    """


def doctest_aggregate_crowd():
    """Doctests for aggregate_crowd.

        >>> from schooltool.securitypolicy.metaconfigure import aggregate_crowd
        >>> _context = ContextStub()
        >>> aggregate_crowd(_context, 'newcrowd', ['old1', 'old2'])
        ('crowd', 'newcrowd')
          <function handle_aggregate_crowd ...>
          ('newcrowd', ['old1', 'old2'])
        ---

    """


def doctest_allow():
    """Doctests for allow.

        >>> from schooltool.securitypolicy.metaconfigure import allow
        >>> _context = ContextStub()
        >>> allow(_context, 'interface', ['ipqs', 'ecug'], 'do')
        ('allow', 'ipqs', 'do', 'interface')
          <function handle_allow ...>
          ('ipqs', 'do', 'interface')
        ---
        ('allow', 'ecug', 'do', 'interface')
          <function handle_allow ...>
          ('ecug', 'do', 'interface')
        ---

    """


def doctest_AccessControlSetting():
    """Doctests for AccessControlSetting.

        >>> from schooltool.securitypolicy.metaconfigure import AccessControlSetting
        >>> setting = AccessControlSetting("key", "Some text", "Alt text", False)

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

        >>> handle_setting("key", "text", None, False)

    Now we should have one:

        >>> subscribers([None], IAccessControlSetting)
        [<AccessControlSetting key=key, text=text, default=False>]

    Let's add another one:

        >>> handle_setting("another_key", "more text", "alt text", True)
        >>> subscribers([None], IAccessControlSetting)
        [<AccessControlSetting key=key, text=text, default=False>,
         <AccessControlSetting key=another_key, text=more text,
                               alt_text=alt text, default=True>]

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
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=f.setUp, tearDown=f.tearDown)])

