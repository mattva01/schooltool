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
from zope.app.testing import setup
from zope.component import getAdapter
from schooltool.securitypolicy import metaconfigure as mc


def doctest_handle_allow():
    """Tests for handle_allow.

        >>> from schooltool.securitypolicy import metaconfigure as mc

        >>> mc.crowdmap = {'cr1': 'fac1', 'cr2': 'fac2', 'cr3': 'fac3'}
        >>> def registerCrowdAdapterStub(iface, permission):
        ...     print 'registerCrowdAdapter' + str((iface, permission))

        >>> mc.registerCrowdAdapter = registerCrowdAdapterStub

    First check a simple declaration:

        >>> mc.handle_allow('iface', ['cr1', 'cr2'], 'my.permission')
        registerCrowdAdapter('iface', 'my.permission')

        >>> mc.objcrowds
        {('iface', 'my.permission'): ['fac1', 'fac2']}

    Another call will not invoke registerCrowdAdapter again:

        >>> mc.handle_allow('iface', ['cr3'], 'my.permission')
        >>> mc.objcrowds
        {('iface', 'my.permission'): ['fac1', 'fac2', 'fac3']}

    Let's check the case when an interface is not provided:

        >>> mc.handle_allow(None, ['cr1'], 'my.permission')
        >>> mc.permcrowds
        {'my.permission': ['fac1']}

        >>> mc.handle_allow(None, ['cr2'], 'my.permission')
        >>> mc.permcrowds
        {'my.permission': ['fac1', 'fac2']}

    """


def doctest_handle_crowd():
    """Tests for handle_crowd.

        >>> from schooltool.securitypolicy.metaconfigure import handle_crowd
        >>> from schooltool.securitypolicy.metaconfigure import crowdmap
        >>> crowdmap
        {}
        >>> handle_crowd('drunkards', 'brewery')
        >>> crowdmap
        {'drunkards': 'brewery'}

    Clean up:

        >>> crowdmap.clear()

    """


def test_registerCrowdAdapter():
    """Tests for registerCrowdAdapter.

        >>> from schooltool.securitypolicy import metaconfigure
        >>> from schooltool.securitypolicy.interfaces import ICrowd

        >>> oldObjCrowds = metaconfigure.objcrowds

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
        >>> metaconfigure.objcrowds = {(IMyObject, 'perm'): [CrowdStub]}

        >>> adapter.contains('some principal')
        contains(some principal)
        False

        >>> adapter.contains('r00t')
        contains(r00t)
        True


    """

class Fixture(object):

    def setUp(self, test=None):
        setup.placelessSetUp()
        self.oldRegisterCrowdAdapter = mc.registerCrowdAdapter
        self.oldCrowdMap = mc.crowdmap
        self.oldObjCrowds = mc.objcrowds
        self.oldPermCrowds = mc.permcrowds

        mc.objcrowds = {}
        mc.permcrowds = {}
        mc.crowdmap = {}

    def tearDown(self, test=None):
        setup.placelessTearDown()
        mc.registerCrowdAdapter = self.oldRegisterCrowdAdapter
        mc.crowdmap = self.oldCrowdMap
        mc.objcrowds = self.oldObjCrowds
        mc.permcrowds = self.oldPermCrowds

def test_suite():
    f = Fixture()
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS,
                                 setUp=f.setUp, tearDown=f.tearDown)])

