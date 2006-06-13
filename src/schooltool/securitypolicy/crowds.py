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

$Id$

"""

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations


class Crowd(object):
    """An abstract base class for crowds."""

    implements(ICrowd)

    def __init__(self, context):
        # As crowds are used in our security policy we have to trust
        # them
        self.context = removeSecurityProxy(context)

    def contains(self, principal):
        raise NotImplementedError()


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


class ConfigurableCrowd(Crowd):
    """A base class for calendar parent crowds.

    You only need to override `setting_key` which indicates the key
    of the corresponding security setting.
    """

    setting_key = None # override in subclasses

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        # XXX avoid a circular import
        from schooltool.app.interfaces import ISchoolToolApplication
        app = ISchoolToolApplication(None)
        customizations = IAccessControlCustomisations(app)
        return customizations.get(self.setting_key)


class EverybodyCrowd(Crowd):
    """A crowd that contains absolutely everybody."""

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

    group = 'zope.Authenticated'

class AnonymousCrowd(Crowd):
    """Anonymous users."""

    group = 'zope.Anybody'

class ManagersCrowd(_GroupCrowd):
    group = 'sb.group.manager'

class AdministratorsCrowd(_GroupCrowd):
    group = 'sb.group.administrators'

class ClerksCrowd(_GroupCrowd):
    group = 'sb.group.clerks'

class TeachersCrowd(_GroupCrowd):
    group = 'sb.group.teachers'

