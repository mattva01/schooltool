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
SchoolTool security policy crowds.
"""

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy
from zope.component import queryAdapter, queryMultiAdapter, queryUtility
from zope.component import getGlobalSiteManager
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer


from schooltool.securitypolicy.interfaces import (
    ICrowdsUtility,
    IDescriptionUtility,
    ICrowd,
    IAccessControlCustomisations,
    ICrowdToDescribe,
    IDescription,
    IDescriptionGroup,
    IGroupAction,
    ICrowdDescription)

from schooltool.common import SchoolToolMessage as _


class CrowdNotRegistered(Exception):
    pass


class CrowdsUtility(object):
    implements(ICrowdsUtility)

    def __init__(self):
        self.factories = {}
        self.crowds = {}

    def getCrowdNames(self, permission, interface):
        return self.crowds.get((permission, interface), [])

    def getFactory(self, crowd_name):
        if crowd_name not in self.factories:
            raise CrowdNotRegistered(crowd_name)
        return self.factories[crowd_name]

    def getFactories(self, permission, interface):
        names = self.getCrowdNames(permission, interface)
        return [self.getFactory(name) for name in names]


def getCrowdsUtility():
    """Helper - returns crowds utility and registers new one if missing."""
    utility = queryUtility(ICrowdsUtility)
    if not utility:
        utility = CrowdsUtility()
        getGlobalSiteManager().registerUtility(utility, ICrowdsUtility)
    return utility


class DescriptionUtility(object):
    implements(IDescriptionUtility)

    def __init__(self):
        self.groups = BTreeContainer()
        self.actions_by_group = BTreeContainer()


def getDescriptionUtility():
    """Helper - returns crowd description utility and registers
    a new one if missing.
    """
    utility = queryUtility(IDescriptionUtility)
    if not utility:
        utility = DescriptionUtility()
        getGlobalSiteManager().registerUtility(utility, IDescriptionUtility)
    return utility


class Description(Contained):
    implements(IDescription)

    title = u''
    description = u''

    def __repr__(self):
        return '<%s.%s (%r)>' % (self.__class__.__module__,
                              self.__class__.__name__,
                              self.title)


class DescriptionGroup(Description):
    implements(IDescriptionGroup)


class GroupAction(Description):
    implements(IGroupAction)

    interface = None
    permission = None

    @property
    def group(self):
        if self.__parent__ is None:
            return None
        group_name = self.__parent__.__name__
        util = getDescriptionUtility()
        if group_name not in util.groups:
            return None
        return util.groups[group_name]


class Crowd(object):
    """An abstract base class for crowds."""

    implements(ICrowd)

    title = u''
    description = u''

    def __init__(self, context):
        # As crowds are used in our security policy we have to trust
        # them
        self.context = removeSecurityProxy(context)

    def contains(self, principal):
        raise NotImplementedError()

    def __str__(self):
        return "<%s>" % self.__class__.__name__

    __repr__ = __str__


class AggregateCrowd(Crowd):
    """A base class for aggregating crowds.

    Override crowdFactories to specify which crowds to aggregate.
    """

    def contains(self, principal):
        for crowdcls in self.crowdFactories():
            crowd = crowdcls(self.context)
            if crowd.contains(principal):
                return True
        return False

    def crowdFactories(self):
        raise NotImplementedError("override this in subclasses")

    def __str__(self):
        crowds = [factory(self.context) for factory in self.crowdFactories()]
        return "<AggregateCrowd crowds=%s>" % crowds

    __repr__ = __str__


class ConfigurableCrowd(Crowd):
    """A base class for calendar parent crowds.

    You only need to override `setting_key` which indicates the key
    of the corresponding security setting.
    """

    setting_key = None # override in subclasses

    @property
    def settings(self):
        # XXX: Avoid a circular import.  Very naughty.
        from schooltool.app.interfaces import ISchoolToolApplication
        app = ISchoolToolApplication(None)
        return IAccessControlCustomisations(app)

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        return self.settings.get(self.setting_key)


class EverybodyCrowd(Crowd):
    """A crowd that contains absolutely everybody."""

    title = _(u'Everybody')
    description = _(u'Everybody, including users that are not logged in.')

    def contains(self, principal):
        return True


class OwnerCrowd(Crowd):
    """Crowd of owners.

    The crowd tries to adapt the context to IPerson.  If adaptation succeeds,
    it compares the obtained person with the current principal.
    """

    def contains(self, principal):
        from schooltool.person.interfaces import IPerson
        from schooltool.app.browser import same # XXX
        person = IPerson(principal, None)
        owner = IPerson(self.context, None)
        return person is not None and same(person, owner)


class _GroupCrowd(Crowd):
    """A base class for crowds determined by the principal's groups."""

    group = None # override this

    def contains(self, principal):
        return self.group in principal.groups


class AuthenticatedCrowd(_GroupCrowd):
    """Authenticated users."""

    title = _(u'Authenticated user')
    description = _(u'All logged in users.')

    group = 'zope.Authenticated'


class AnonymousCrowd(_GroupCrowd):
    """Anonymous users."""

    title = _(u'Anybody')
    description = _(u'Users who did not log in')

    group = 'zope.Anybody'


class LoggedInCrowd(Crowd):

    title = _(u'Logged In')
    description = _(u'All logged in users.')

    def contains(self, principal):
        from schooltool.person.interfaces import IPerson
        person = IPerson(principal, None)
        return person is not None


class SuperUserCrowd(Crowd):

    title = _(u'Super user')
    description = _(u'The super user - owner of this SchoolTool application.')

    def contains(self, principal):
        from schooltool.app.browser import same # XXX
        from schooltool.app.interfaces import ISchoolToolApplication
        from schooltool.person.interfaces import IPerson
        app = ISchoolToolApplication(None)
        persons = app['persons']
        person = IPerson(principal, None)
        return person is not None and same(person, persons.super_user)


class ManagerGroupCrowd(_GroupCrowd):
    group = 'sb.group.manager'


class ManagersCrowd(Crowd):

    def contains(self, principal):
        managers_group = ManagerGroupCrowd(self.context)
        super_users = SuperUserCrowd(self.context)
        return super_users.contains(principal) or managers_group.contains(principal)


class AdministratorsCrowd(_GroupCrowd):
    group = 'sb.group.administrators'

class ClerksCrowd(_GroupCrowd):
    group = 'sb.group.clerks'

class TeachersCrowd(_GroupCrowd):
    group = 'sb.group.teachers'

class StudentsCrowd(_GroupCrowd):
    group = 'sb.group.students'


class AdministrationCrowd(AggregateCrowd):

    def crowdFactories(self):
        return [AdministratorsCrowd, ClerksCrowd, ManagersCrowd]


class ParentCrowdTemplate(Crowd):
    """A crowd that contains principals who are allowed to access the context."""

    interface = None
    permission = ''

    def contains(self, principal):
        parent = self.context.__parent__
        pcrowd = queryAdapter(parent, self.interface, self.permission,
                              default=None)
        if pcrowd is not None:
            return pcrowd.contains(principal)
        else:
            return False


def ParentCrowd(interface, permission):
    return type('ParentCrowd',
                (ParentCrowdTemplate,),
                {'interface': interface,
                 'permission': permission})


class CrowdDescription(Description):
    implements(ICrowdDescription)

    def __init__(self, crowd, action, group):
        self.crowd, self.action, self.group = crowd, action, group


class DefaultCrowdDescription(Description):
    implements(ICrowdDescription)

    def __init__(self, crowd, action, group):
        self.crowd, self.action, self.group = crowd, action, group
        if hasattr(self.crowd, 'title'):
            self.title = self.crowd.title
        if hasattr(self.crowd, 'description'):
            self.description = self.crowd.description


class AggregateCrowdDescription(CrowdDescription):

    @property
    def description(self):
        return u', '.join([d.title for d in self.getDescriptions()
                           if d.title])

    def getFactories(self):
        return self.crowd.crowdFactories()

    def getDescriptions(self):
        factories = self.getFactories()
        descriptions =[
            getCrowdDescription(factory(None), self.action, self.group)
            for factory in factories]
        return filter(None, descriptions)


def getCrowdDescription(crowd, action, group):
    crowd_to_describe = queryMultiAdapter(
        (crowd, action, group),
        ICrowdToDescribe,
        default=None)
    if crowd_to_describe is None:
        return None
    description = queryMultiAdapter(
        (crowd_to_describe, action, group),
        ICrowdDescription,
        default=None)

    return description


def defaultCrowdToDescribe(crowd, action, group):
    return crowd


def collectCrowdDescriptions(action):
    crowds = getCrowdsUtility()
    # Mimic schooltool.securitypolicy.SchoolToolSecurityPolicy behaviour
    crowd_names = crowds.getCrowdNames(action.permission,
                                       None)
    if not crowd_names:
        crowd_names = crowds.getCrowdNames(action.permission,
                                           action.interface)

    descriptions = getDescriptionUtility()
    group = action.group

    descriptions = []
    for name in sorted(crowd_names):
        factory = crowds.getFactory(name)
        crowd = factory(None)
        descriptions.append(getCrowdDescription(crowd, action, group))
    return descriptions


def inCrowd(principal, name, context=None):
    crowds = getCrowdsUtility()
    try:
        factory = crowds.getFactory(name)
    except CrowdNotRegistered:
        return False
    crowd = factory(context)
    return crowd.contains(principal)
