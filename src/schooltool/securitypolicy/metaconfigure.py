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
SchoolTool metaconfiguration code.
"""

from zope.interface import implements
from zope.component import provideAdapter, provideSubscriptionAdapter
from zope.component import queryUtility, getGlobalSiteManager
from zope.container.btree import BTreeContainer

from schooltool.securitypolicy.crowds import AggregateCrowd
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.securitypolicy.interfaces import ICrowdToDescribe
from schooltool.securitypolicy.interfaces import ICrowdDescription
from schooltool.securitypolicy.interfaces import IAccessControlSetting
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.securitypolicy.crowds import getCrowdsUtility
from schooltool.securitypolicy.crowds import getDescriptionUtility
from schooltool.securitypolicy.crowds import DescriptionGroup
from schooltool.securitypolicy.crowds import GroupAction
from schooltool.securitypolicy.crowds import CrowdDescription


# ZCML execution order
ZCML_REGISTER_DESCRIPTION_GROUPS       = 10100
ZCML_REGISTER_DESCRIPTION_ACTIONS      = 10200
ZCML_REGISTER_CROWD_DESCRIPTIONS       = 10300
ZCML_REGISTER_DESCRIPTION_SWITCHING    = 10400


class AggregateUtilityCrowd(AggregateCrowd):
    interface = None
    permission = None

    def crowdFactories(self):
        return getCrowdsUtility().getFactories(self.permission, self.interface)


def registerCrowdAdapter(permission, interface):
    """Register an adapter to ICrowd for interface.

    The adapter dynamically retrieves the list of crowds from the
    global objcrowds.  You should not call this function several times
    for the same (permission, interface).
    """
    aggregator_class = type(
        str('%s_%s' % (AggregateUtilityCrowd.__name__, interface.__name__)),
        (AggregateUtilityCrowd, ),
        {'interface': interface, 'permission': permission})

    provideAdapter(aggregator_class, provides=ICrowd, adapts=[interface],
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

    def __init__(self, key, text, alt_text, default):
        self.key = key
        self.text = text
        self.alt_text = alt_text
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
        if self.alt_text is None:
            return "<AccessControlSetting key=%s, text=%s, default=%s>" % (
                self.key, self.text, self.default)
        return "<AccessControlSetting key=%s, text=%s, alt_text=%s, default=%s>" % (
            self.key, self.text, self.alt_text, self.default)


def handle_setting(key, text, alt_text, default):
    def accessControlSettingFactory(context=None):
        return AccessControlSetting(key, text, alt_text, default)
    provideSubscriptionAdapter(accessControlSettingFactory,
                               adapts=[None],
                               provides=IAccessControlSetting)

def setting(_context, key=None, text=None, alt_text=None, default=None):
    _context.action(
        discriminator=('setting', key),
        callable=handle_setting, args=(key, text, alt_text, default))


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


def handle_group(name, group):
    util = getDescriptionUtility()
    util.groups[name] = group
    group.__name__ = name
    group.__parent__ = util.groups


def describe_group(_context, name=None, title=None, description=None, klass=None):
    if klass is None and title is None:
        raise TypeError("Must specify title or klass.")

    if klass is None:
        klass = DescriptionGroup

    new_class = type(str('%s_%s' % (klass.__name__, name.capitalize())),
                     (klass, ), {})
    group = new_class()
    if title is not None:
        group.title = title
    if description is not None:
        group.description = description

    _context.action(discriminator=('describe_group', name),
                    callable=handle_group,
                    args=(name, group),
                    order=ZCML_REGISTER_DESCRIPTION_GROUPS)


def handle_action(group_name, name, action):
    util = getDescriptionUtility()
    if group_name not in util.actions_by_group:
        util.actions_by_group[group_name]=BTreeContainer()
    util.actions_by_group[group_name][name] = action
    action.__name__ = name
    action.__parent__ = util.actions_by_group[group_name]


def describe_action(_context, group=None, name=None, order=0,
                    interface=None, permission='',
                    title=None, description=None, klass=None):
    if klass is None and title is None:
        raise TypeError("Must specify title or klass.")

    if klass is None:
        klass = GroupAction

    new_class = type(str('%s_%s' % (klass.__name__, name.capitalize())),
                     (klass, ), {})
    action = new_class()
    if title is not None:
        action.title = title
    if description is not None:
        action.description = description
    if interface is not None:
        action.interface = interface
    if permission is not None:
        action.permission = permission
    action.order = order

    _context.action(discriminator=('describe_action', group, name),
                    callable=handle_action,
                    args=(group, name, action),
                    order=ZCML_REGISTER_DESCRIPTION_ACTIONS)


def handle_crowd_description(context, group_id, action_id,
                             interface, permission_id,
                             crowd_getter, description_factory):
    util = getDescriptionUtility()

    group = None
    if group_id is not None:
        group = util.groups[group_id]

    action = None
    if action_id is not None:
        action = util.actions_by_group[group_id][action_id]

    crowd_factory = crowd_getter()

    provideAdapter(description_factory,
                   provides=ICrowdDescription,
                   adapts=[crowd_factory,
                           action and action.__class__ or None,
                           group and group.__class__ or None,
                           ])


def describe_crowd(_context, group=None, action=None,
                   interface=None, permission=None,
                   crowd=None, crowd_factory=None,
                   factory=None, title=None, description=None):

    if crowd is not None and crowd_factory is not None:
        raise TypeError("Must specify either crowd or crowd_factory.")

    if action is not None and group is None:
        raise TypeError("Must specify group when specifying action.")

    if crowd is not None:
        crowd_getter = lambda: getCrowdsUtility().getFactory(crowd)
    elif crowd_factory is not None:
        crowd_getter = lambda: crowd_factory
    else:
        crowd_getter = lambda: None

    if factory is None:
        if title is None and description is None:
            raise TypeError("Must specify either description factory"
                            " or title/description.")
        factory = CrowdDescription

    factory_dict = {}
    if title is not None:
        factory_dict['title'] = title
    if description is not None:
        factory_dict['description'] = description
    new_factory = type(factory.__name__, (factory, ), factory_dict)

    discriminator = ('describe_crowd', group, action,
                     interface, permission, crowd, crowd_factory)

    _context.action(discriminator=discriminator,
                    callable=handle_crowd_description,
                    args=(_context, group, action,
                          interface, permission, crowd_getter,
                          new_factory),
                    order=ZCML_REGISTER_CROWD_DESCRIPTIONS)


def handle_switch_description(context, group_id, action_id,
                              crowd_getter, replacement_crowd_getter):
    util = getDescriptionUtility()

    group = None
    if group_id is not None:
        group = util.groups[group_id]

    action = None
    if action_id is not None:
        action = util.actions_by_group[group_id][action_id]

    replacement = replacement_crowd_getter()
    unpack_replacement = lambda crowd, action, group: replacement(crowd)

    provideAdapter(unpack_replacement,
                   provides=ICrowdToDescribe,
                   adapts=[crowd_getter(),
                           action and action.__class__ or None,
                           group and group.__class__ or None,
                           ])


def switch_description(_context,
                       group=None, action=None,
                       crowd=None, crowd_factory=None,
                       use_crowd=None, use_crowd_factory=None):

    if crowd is not None and crowd_factory is not None:
        raise TypeError("Must specify either crowd or crowd_factory.")

    if use_crowd is not None and use_crowd_factory is not None:
        raise TypeError("Must specify either use_crowd or use_crowd_factory.")

    if action is not None and group is None:
        raise TypeError("Must specify group when specifying action.")

    if crowd is not None:
        crowd_getter = lambda: getCrowdsUtility().getFactory(crowd)
    elif crowd_factory is not None:
        crowd_getter = lambda: crowd_factory
    else:
        crowd_getter = lambda: None

    if use_crowd is not None:
        replacement_crowd_getter = lambda: getCrowdsUtility().getFactory(use_crowd)
    elif use_crowd_factory is not None:
        replacement_crowd_getter = lambda: use_crowd_factory
    else:
        replacement_crowd_getter = lambda: None

    discriminator = ('switch_description', group, action,
                     crowd, crowd_factory, use_crowd, use_crowd_factory)

    _context.action(discriminator=discriminator,
                    callable=handle_switch_description,
                    args=(_context, group, action,
                          crowd_getter, replacement_crowd_getter),
                    order=ZCML_REGISTER_DESCRIPTION_SWITCHING)

