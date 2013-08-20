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
Unit tests for schooltool.securitypolicy.policy
"""
import unittest
import doctest

from zope.interface import implements, directlyProvides, Interface
from zope.component import adapts
from zope.component import provideAdapter, provideUtility
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


class ParticipationStub(object):
    interaction = None
    principal = 'guest'


def test_SchoolToolSecurityPolicy_checkPermission():
    """Tests for SchoolToolSecurityPolicy.

        >>> from schooltool.securitypolicy.crowds import CrowdsUtility
        >>> from schooltool.securitypolicy.interfaces import ICrowdsUtility
        >>> cru = CrowdsUtility()
        >>> provideUtility(cru, ICrowdsUtility)

    Let's construct a security policy.

        >>> from schooltool.securitypolicy import policy
        >>> participation = ParticipationStub()
        >>> sp = policy.SchoolToolSecurityPolicy(participation)

        >>> byadaptation_returns = False
        >>> def checkByAdaptationStub(permission, obj):
        ...     print 'checkByAdaptation' + str((permission, obj))
        ...     return byadaptation_returns
        >>> sp.checkByAdaptation = checkByAdaptationStub

        >>> checkcrowds_returns = False
        >>> def checkCrowdsStub(crowdclasses, obj):
        ...     print 'checkCrowds' + str((crowdclasses, obj))
        ...     return checkcrowds_returns
        >>> sp.checkCrowds = checkCrowdsStub

    First, we test the path where no crowds accept the principal:

        >>> obj = Obj()

        >>> sp.checkPermission('perm', obj)
        checkByAdaptation('perm', <...Obj object ...>)
        False

    Interface-independent permissions
    ---------------------------------

        >>> checkcrowds_returns = True
        >>> cru.factories = {'the crowd': 'crowd factory'}
        >>> cru.crowds[('perm', None)] = ['the crowd']
        >>> sp.checkPermission('perm', obj)
        checkCrowds(['crowd factory'], <...Obj object ...>)
        True

    Another case: there is a registered crowd for the permission, but checkCrowds
    fails:

        >>> checkcrowds_returns = False

        >>> sp.checkPermission('perm', obj)
        checkCrowds(['crowd factory'], <...Obj object ...>)
        False

    """


def test_SchoolToolSecurityPolicy_checkByAdaptation():
    """Tests for SchoolToolSecurityPolicy.checkByAdaptation.

        >>> from schooltool.securitypolicy.crowds import CrowdsUtility
        >>> from schooltool.securitypolicy.interfaces import ICrowdsUtility
        >>> cru = CrowdsUtility()
        >>> provideUtility(cru, ICrowdsUtility)

    Let's construct a security policy.

        >>> from schooltool.securitypolicy import policy
        >>> participation = ParticipationStub()
        >>> sp = policy.SchoolToolSecurityPolicy(participation)

        >>> obj = Obj()

    First, check the straightforward case

        >>> contains_returns = False
        >>> class ObjCrowd(Crowd):
        ...     adapts(IObj)
        ...     def contains(self, principal):
        ...         return contains_returns
        >>> provideAdapter(ObjCrowd, (IObj,), ICrowd, 'perm')

        >>> sp.checkByAdaptation('perm', obj)
        False

        >>> contains_returns = True
        >>> sp.checkByAdaptation('perm', obj)
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
        Traceback (most recent call last):
            ...
        AssertionError: ('no crowd found for', None, 'perm')

    """


def test_SchoolToolSecurityPolicy_checkCrowds():
    """Tests for SchoolToolSecurityPolicy.checkCrowds.

    Check crowds just check whether any principal is contained in at
    least one of the crowds constructed from a crowdcls list passed to
    it:

        >>> class NegativeCrowdStub(object):
        ...     def __init__(self, context):
        ...         pass
        ...     def contains(self, principal):
        ...         return False
        >>> class CrowdStub(NegativeCrowdStub):
        ...     def contains(self, principal):
        ...         return principal == 'john'

        >>> class ParticipationStub(object):
        ...     interaction = None
        ...     def __init__(self, principal):
        ...         self.principal = principal

        >>> from schooltool.securitypolicy import policy
        >>> sp = policy.SchoolToolSecurityPolicy(ParticipationStub('john'),
        ...                                      ParticipationStub('pete'))

        >>> sp.checkCrowds([NegativeCrowdStub, NegativeCrowdStub], object())
        False

        >>> sp.checkCrowds([NegativeCrowdStub, CrowdStub], object())
        True

    If john is not logged in, we'd still get False:

        >>> sp = policy.SchoolToolSecurityPolicy(ParticipationStub('pete'))
        >>> sp.checkCrowds([NegativeCrowdStub, CrowdStub], object())
        False

    """


def setUp(test=None):
    setup.placelessSetUp()

def tearDown(test=None):
    setup.placelessTearDown()


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=doctest.ELLIPSIS,
                                 setUp=setUp, tearDown=tearDown),
           ])
