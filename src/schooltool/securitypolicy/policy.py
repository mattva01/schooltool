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
SchoolTool security policy.

$Id$

"""

from zope.security.simplepolicies import ParanoidSecurityPolicy
from zope.component import queryAdapter
from zope.traversing.api import getParent
from schooltool.securitypolicy.crowds import ICrowd
from schooltool.securitypolicy.metaconfigure import getCrowdsUtility


class SchoolToolSecurityPolicy(ParanoidSecurityPolicy):
    """Crowd-based security policy."""

    def checkPermission(self, permission, obj):
        """Return True if principal has permission on object."""

        # Check the generic, interface-independent permissions.
        crowdclasses = getCrowdsUtility().permcrowds.get(permission, [])
        if self.checkCrowds(crowdclasses, obj):
            return True

        # No quick method worked, look up the crowd by adaptation.
        return self.checkByAdaptation(permission, obj)

    def checkByAdaptation(self, permission, obj):
        crowd = queryAdapter(obj, ICrowd, name=permission, default=None)
        # If there is no crowd that has the given permission on this
        # object, try to look up a crowd that includes the parent.
        while crowd is None and obj is not None:
            obj = getParent(obj)
            crowd = queryAdapter(obj, ICrowd, name=permission, default=None)
        if crowd is None: # no crowds found
            raise AssertionError('no crowd found for', obj, permission)

        for participation in self.participations:
            if crowd.contains(participation.principal):
                return True
        else:
            return False

    def checkCrowds(self, crowdclasses, obj):
        """Check if an object is in any of the given crowds."""
        for participation in self.participations:
            for crowdcls in crowdclasses:
                crowd = crowdcls(obj)
                if crowd.contains(participation.principal):
                    return True
        return False
