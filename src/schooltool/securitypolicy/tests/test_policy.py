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
from zope.app.testing import ztapi
from zope.interface import implements, directlyProvides, Interface
from zope.component import adapts
from zope.app.testing import setup
from zope.traversing.interfaces import IContainmentRoot
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import ICrowd


class IObj(Interface):
    pass


class Obj(object):
    implements(IObj)

class AnotherObj(object):
    pass

class PermCrowd(Crowd):
    adapts(IObj)
    def contains(seld, principal):
        return principal == 'roodkcab'


class ObjCrowd(Crowd):
    adapts(IObj)
    def contains(self, principal):
        return principal == 'root'


class ParticipationStub(object):
    interaction = None
    principal = 'guest'


def test_SchoolToolSecurityPolicy():
    """

        >>> from schooltool.securitypolicy.metaconfigure import CrowdsUtility
        >>> from schooltool.securitypolicy.interfaces import ICrowdsUtility
        >>> cru = CrowdsUtility()
        >>> ztapi.provideUtility(ICrowdsUtility, cru)

    Let's construct a security policy.

        >>> from schooltool.securitypolicy import policy
        >>> participation = ParticipationStub()
        >>> sp = policy.SchoolToolSecurityPolicy(participation)

    First without any declarations checkPermission should deny access:

        >>> obj = Obj()

        >>> sp.checkPermission('perm', obj)
        False

    Test generic (interface independent) permissions:

        >>> cru.permcrowds['perm'] = [PermCrowd]
        >>> participation.principal = 'roodkcab'
        >>> sp.checkPermission('perm', obj)
        True

    If we provide a different principal, things work out differently:

        >>> participation.principal = 'root'
        >>> sp.checkPermission('perm', obj)
        True

    If no crowd is found for a given object, its parents are checked instead:

        >>> obj2 = AnotherObj()
        >>> obj2.__parent__ = obj
        >>> obj3 = AnotherObj()
        >>> obj3.__parent__ = obj2

        >>> sp.checkPermission('perm', obj3)
        True

    The code won't climb up beyond IContainmentRoot:

        >>> obj2.__parent__ = None
        >>> directlyProvides(obj2, IContainmentRoot)
        >>> sp.checkPermission('perm', obj3)
        False

    """


def setUp(test=None):
    setup.placelessSetUp()
    ztapi.provideAdapter(IObj, ICrowd, ObjCrowd, 'perm')

def tearDown(test=None):
    setup.placelessTearDown()


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS,
                                 setUp=setUp, tearDown=tearDown)])
