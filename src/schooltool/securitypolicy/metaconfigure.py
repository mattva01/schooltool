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
SchoolTool metaconfiguration code.

$Id$

"""

from zope.interface import implements
from zope.component import provideAdapter, provideSubscriptionAdapter
from zope.security.zcml import permission
from zope.component import queryUtility, getGlobalSiteManager

from schooltool.securitypolicy.crowds import Crowd, AggregateCrowd
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.securitypolicy.interfaces import ICrowdsUtility
from schooltool.securitypolicy.interfaces import IAccessControlSetting
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.app.interfaces import ISchoolToolApplication


class CrowdNotRegistered(Exception):
    pass


class CrowdsUtility(object):
    implements(ICrowdsUtility)

    def __init__(self):
        self.factories = {}
        self.crowds = {}

    def getFactories(self, permission, interface):
        names = self.crowds.get((permission, interface), [])
        factories = []
        for name in names:
            if name not in self.factories:
                raise CrowdNotRegistered(name)
            factories.append(self.factories[name])
        return factories


def getCrowdsUtility():
    """Helper - returns crowds utility and registers new one if missing."""
    utility = queryUtility(ICrowdsUtility)
    if not utility:
        utility = CrowdsUtility()
        getGlobalSiteManager().registerUtility(utility, ICrowdsUtility)
    return utility


def registerCrowdAdapter(permission, interface):
    """Register an adapter to ICrowd for interface.

    The adapter dynamically retrieves the list of crowds from the
    global objcrowds.  You should not call this function several times
    for the same (permission, interface).
    """
    class AggregateUtilityCrowd(AggregateCrowd):
        def crowdFactories(self):
            return getCrowdsUtility().getFactories(permission, interface)

    provideAdapter(AggregateUtilityCrowd, provides=ICrowd, adapts=[interface],
                   name=permission)


def handle_crowd(name, factory):
    """Handler for the ZCML <crowd> directive."""
    getCrowdsUtility().factories[name] = factory


def handle_allow(crowdname, permission, interface):
    """Handler for the ZCML <allow> directive.

    interface is the interface for which the security declaration is issued,
    crowdname is a string,
    permission is an identifier for a permission.

    The function registers the given crowd factory in the ICrowdsUtility.

    An adapter to ICrowd is provided if interface is specified.
    """

    utility = getCrowdsUtility()

    discriminator = (permission, interface)
    if discriminator not in utility.crowds:
        utility.crowds[discriminator] = []
        if interface is not None:
            registerCrowdAdapter(permission, interface)

    utility.crowds[discriminator].append(crowdname)


def crowd(_context, name, factory):
    # Declare the crowd.
    _context.action(discriminator=('crowd', name), callable=handle_crowd,
                    args=(name, factory))


def allow(_context, interface=None, crowds=None, permission=None):
    for crowd in crowds:
        _context.action(discriminator=('allow', crowd, permission, interface),
                        callable=handle_allow,
                        args=(crowd, permission, interface))


def deny(_context, interface=None, crowds=None, permission=None):
    # XXX: Deny directive needs documentation.
    for crowd in crowds:
        _context.action(discriminator=('allow', crowd, permission, interface),
                        callable=lambda: None,
                        args=())


class AccessControlSetting(object):
    implements(IAccessControlSetting)

    def __init__(self, key, text, default):
        self.key = key
        self.text = text
        self.default = default

    def getValue(self):
        app = ISchoolToolApplication(None)
        customisations = IAccessControlCustomisations(app)
        return customisations.get(self.key)

    def setValue(self, value):
        app = ISchoolToolApplication(None)
        customisations = IAccessControlCustomisations(app)
        return customisations.set(self.key, value)

    def __repr__(self):
        return "<AccessControlSetting key=%s, text=%s, default=%s>" % (
                self.key, self.text, self.default)


def handle_setting(key, text, default):
    def accessControlSettingFactory(context=None):
        return AccessControlSetting(key, text, default)
    provideSubscriptionAdapter(accessControlSettingFactory,
                               adapts=[None],
                               provides=IAccessControlSetting)

def setting(_context, key=None, text=None, default=None):
    _context.action(discriminator=('setting', key),
                    callable=handle_setting, args=(key, text, default))


def handle_aggregate_crowd(name, crowd_names):
    factories = getCrowdsUtility().factories
    try:
        crowds = [factories[crowd_name] for crowd_name in crowd_names]
    except KeyError:
        raise ValueError("invalid crowd id", crowd_name)

    class AggregateCrowdFactory(AggregateCrowd):
        def crowdFactories(self):
            return crowds
    handle_crowd(name, AggregateCrowdFactory)


def aggregate_crowd(_context, name, crowds):
    _context.action(discriminator=('crowd', name),
                    callable=handle_aggregate_crowd, args=(name, crowds))
