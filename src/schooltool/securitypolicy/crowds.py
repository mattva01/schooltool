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
SchoolTool security policy crowds.
"""

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy
from zope.component import queryAdapter, queryMultiAdapter
from zope.container.contained import Contained

from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.securitypolicy.interfaces import ICrowdToDescribe
from schooltool.securitypolicy.interfaces import (
    IDescription, IDescriptionGroup, IGroupAction, ICrowdDescription)

from schooltool.common import SchoolToolMessage as _


class Description(Contained):
    implements(IDescription)

    title = u''
    description = u''


class DescriptionGroup(Description):
    implements(IDescriptionGroup)


class GroupAction(Description):
    implements(IGroupAction)

    interface = None
    permission = None


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


def defaultCrowdToDescribe(crowd, action, group):
    return crowd

