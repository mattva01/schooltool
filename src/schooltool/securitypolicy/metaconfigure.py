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

from zope.configuration.exceptions import ConfigurationError
from zope.component import provideAdapter
from schooltool.securitypolicy.policy import permcrowds
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import ICrowd


crowdmap = {} # crowd_name -> crowd_factory
objcrowds = {} # (interface, permission) -> crowd_factory

def registerCrowdAdapter(iface, permission):
    """Register an adapter to ICrowd for iface.

    The adapter dynamically retrieves the list of crowds from the
    global objcrowds.  You should not call this function several times
    for the same (iface, permission).
    """
    class AggregateCrowdAdapter(Crowd):
        def contains(self, principal):
            crowd_factories = objcrowds[(iface, permission)]
            #print '  aggregate: ' + ', '.join(crowd.__name__ for crowd in crowd_factories)
            for crowdcls in crowd_factories:
                crowd = crowdcls(self.context)
                if crowd.contains(principal):
                    return True
            return False
    provideAdapter(AggregateCrowdAdapter, provides=ICrowd, adapts=[iface],
                   name=permission)


def handle_allow(iface, crowdnames, permission):
    """Handler for the ZCML <allow> directive.

    iface is the interface for which the security declaration is issued,
    crowdnames is a list of strings,
    permission is an identifier for a permission.

    The function adds the given crowd factories to the global objcrowds
    and registers an adapter to ICrowd if it was not registered before.

    iface may be None.  In that case permcrowds is updated instead.
    """
    #print 'handle_allow', iface, crowdnames, permission

    crowds = [crowdmap[crowdname] for crowdname in crowdnames]
    if iface is None:
        global permcrowds
        permcrowds.setdefault(permission, []).extend(crowds)
        return

    global objcrowds
    if (iface, permission) not in objcrowds:
        registerCrowdAdapter(iface, permission)
        objcrowds[(iface, permission)] = []
    objcrowds[(iface, permission)].extend(crowds)


def handle_crowd(name, factory):
    crowdmap[name] = factory


def crowd(_context, name, factory):
    # TODO: raise ConfigurationError if arguments are invalid
    # TODO: discriminator
    _context.action(discriminator=None, callable=handle_crowd,
                    args=(name, factory))


def allow(_context, interface=None, crowds=None, permission=None):
    # TODO: raise ConfigurationError if arguments are invalid
    # TODO: discriminator
    _context.action(discriminator=None, callable=handle_allow,
                    args=(interface, crowds, permission))
