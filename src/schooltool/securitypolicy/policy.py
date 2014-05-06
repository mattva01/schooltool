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
SchoolTool security policy.

"""
import zope.keyreference.interfaces
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
        factories = getCrowdsUtility().getFactories(permission, None)
        if factories:
            return self.checkCrowds(factories, obj)

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

    def checkCrowds(self, factories, obj):
        """Check if an object is in any of the given crowds."""
        for participation in self.participations:
            for factory in factories:
                crowd = factory(obj)
                if crowd.contains(participation.principal):
                    return True
        return False


class CachingSecurityPolicy(ParanoidSecurityPolicy):
    """Crowd-based caching security policy."""

    def cachingKey(self, permission, obj):
        try:
            ref = zope.keyreference.interfaces.IKeyReference(obj, None)
            if ref is None:
                return None
        except zope.keyreference.interfaces.NotYet:
            return None
        return (permission, ref)

    @classmethod
    def getCache(cls, participation):
        cache = getattr(participation, '_st_perm_cache', None)
        if cache is None:
            try:
                participation._st_perm_cache = {'perm': {},
                                                'enabled': True}
            except AttributeError:
                return None
        return participation._st_perm_cache

    def checkCache(self, permission, obj):
        key = self.cachingKey(permission, obj)
        if key is None:
            return None # uncacheable
        result = None
        for participation in self.participations:
            cache = self.getCache(participation)
            if cache is not None:
                perm = cache['perm'].get(key, None)
                result = max(result, perm)
        return result

    def cache(self, participation, permission, obj, value):
        cache = self.getCache(participation)
        if cache is None or not cache['enabled']:
            return
        key = self.cachingKey(permission, obj)
        if key is None:
            return # uncacheable
        cache['perm'][key] = value

    def checkPermission(self, permission, obj):
        """Return True if principal has permission on object."""

        perm = self.checkCache(permission, obj)
        if perm is not None:
            return perm

        perm = self.checkPermissionCrowds(permission, obj)
        if perm is not None:
            return perm

        perm = self.checkByAdaptation(permission, obj)
        return perm

    def checkByAdaptation(self, permission, obj):
        crowd = queryAdapter(obj, ICrowd, name=permission, default=None)
        # If there is no crowd that has the given permission on this
        # object, try to look up a crowd that includes the parent.
        objects = [obj]
        while crowd is None and obj is not None:
            obj = getParent(obj)
            objects.append(obj)
            crowd = queryAdapter(obj, ICrowd, name=permission, default=None)
        if crowd is None: # no crowds found
            raise AssertionError('no crowd found for', obj, permission)

        for participation in self.participations:
            if crowd.contains(participation.principal):
                for o in objects:
                    self.cache(participation, permission, o, True)
                return True
            else:
                for o in objects:
                    self.cache(participation, permission, o, False)
        else:
            return False

    def checkPermissionCrowds(self, permission, obj):
        """Check object-independent crowds."""
        factories = getCrowdsUtility().getFactories(permission, None)
        if not factories:
            return None

        for participation in self.participations:
            for factory in factories:
                crowd = factory(obj)
                if crowd.contains(participation.principal):
                    self.cache(participation, permission, obj, True)
                    return True
            self.cache(participation, permission, obj, False)
        return False
