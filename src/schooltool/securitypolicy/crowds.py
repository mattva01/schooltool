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
from schooltool.securitypolicy.interfaces import ICrowd


class Crowd(object):
    """An abstract base class for crowds."""

    implements(ICrowd)

    def __init__(self, context):
        self.context = context

    def contains(self, principal):
        raise NotImplementedError()


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


class ManagerBackdoorCrowd(Crowd):

    # XXX At the moment the manager is not always a member of the manager group.
    # This hack will go away soon.

    def contains(self, principal):
        return (hasattr(principal, '_person')
                and principal._person.__name__ == 'manager')
