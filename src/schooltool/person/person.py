#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Person implementation and support objects
"""

import hashlib
from persistent import Persistent

from zope.interface import implements, implementer
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container import btree
from zope.container.contained import Contained
from zope.component import adapts, adapter

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.membership import URIMembership, URIMember, URIGroup
from schooltool.app.overlay import OverlaidCalendarsProperty
from schooltool.person import interfaces
from schooltool.relationship import RelationshipProperty
from schooltool.securitypolicy.crowds import Crowd, AdministratorsCrowd
from schooltool.securitypolicy.crowds import ClerksCrowd, ManagersCrowd
from schooltool.person.interfaces import IPerson
from schooltool.app.security import ICalendarParentCrowd
from schooltool.securitypolicy.crowds import ConfigurableCrowd
from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.interfaces import IPasswordWriter
from schooltool.securitypolicy.crowds import OwnerCrowd, AggregateCrowd


class PersonContainer(btree.BTreeContainer):
    """Container of persons."""

    implements(interfaces.IPersonContainer, IAttributeAnnotatable)

    super_user = None

    def __setitem__(self, key, person):
        """See `IWriteContainer`

        Ignores `key` and uses `person.username` as the key.
        """
        key = person.username
        btree.BTreeContainer.__setitem__(self, key, person)


class Person(Persistent, Contained):
    """Person."""

    implements(interfaces.IPersonContained, IAttributeAnnotatable)

    photo = None
    username = None
    _hashed_password = None

    groups = RelationshipProperty(URIMembership, URIMember, URIGroup)
    overlaid_calendars = OverlaidCalendarsProperty()

    def __init__(self, username=None, title=None):
        self.title = title
        self.username = username

    def setPassword(self, password):
        self._hashed_password = hash_password(password)

    def checkPassword(self, password):
        return (self._hashed_password is not None
                and hash_password(password) == self._hashed_password)

    def hasPassword(self):
        return self._hashed_password is not None

    def __eq__(self, other):
        if not IPerson.providedBy(other):
            return False
        return self.username == other.username


def hash_password(password):
    r"""Compute a SHA-1 hash of a given password.

        >>> hash_password('secret')
        '\xe5\xe9\xfa\x1b\xa3\x1e\xcd\x1a\xe8Ou\xca\xaaGO:f?\x05\xf4'

    Passwords should be ASCII or Unicode strings.

        >>> hash_password('\u263B')
        '\xe4\x13\xef\x8dv3\xba*P\xbb1\xa2k\x9c|,n\xe3mL'

    To avoid problems with a multitude of 8-bit encodings, they are forbidden

        >>> hash_password('\xFF') # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        UnicodeDecodeError: 'ascii' codec can't decode byte 0xff in ...

    None means "no password set, account is locked":

        >>> hash_password(None) is None
        True

    Security note: passwords are not salted, so it is possible to detect
    users that have the same password.
    """
    if password is None:
        return None
    return hashlib.sha1(password.encode('UTF-8')).digest()


def personAppCalendarOverlaySubscriber(person, event):
    """Add application calendar to overlays of all new persons.
    """
    app = ISchoolToolApplication(None, None)
    if app is None:
        # If we get this we are probably in the initial new-site setup
        # or creating a new manager during startup.  This should be
        # safe to ignore since it will happen very infrequently
        # (perhaps only once) and the manager can easily add the site
        # calendar to his/her overlay in the overlay selection view.
        return
    person.overlaid_calendars.add(ISchoolToolCalendar(app))


from schooltool.app.app import InitBase
class PersonInit(InitBase):

    def __call__(self):
        self.app['persons'] = PersonContainer()


class PublicCalendarCrowd(Crowd):
    def contains(self, principal):
        cal_public = IPersonPreferences(self.context).cal_public
        return cal_public


class PersonCalendarCrowd(AggregateCrowd):
    adapts(IPerson)
    implements(ICalendarParentCrowd)

    def crowdFactories(self):
        return [PublicCalendarCrowd, ManagersCrowd, ClerksCrowd,
                AdministratorsCrowd, OwnerCrowd]


def getCalendarOwner(calendar):
    return IPerson(calendar.__parent__, None)


@adapter(IPerson)
@implementer(interfaces.IPersonContainer)
def getContainerOfPerson(person):
    return person.__parent__


class PersonPasswordWriter(object):
    """Adapter of person to IPasswordWriter."""
    adapts(IPerson)
    implements(IPasswordWriter)

    def __init__(self, person):
        self.person = person

    def setPassword(self, password):
        """See IPasswordWriter."""
        self.person.setPassword(password)


class PersonListViewersCrowd(ConfigurableCrowd):
    """The crowd of people who can view the person list."""

    setting_key = 'everyone_can_view_person_list'


class PasswordWriterCrowd(ConfigurableCrowd):

    setting_key = 'persons_can_change_their_passwords'

    def contains(self, principal):
        from schooltool.app.browser import same # XXX
        app = ISchoolToolApplication(None)
        super_user = app['persons'].super_user
        if self.context.person is super_user:
            person = IPerson(principal, None)
            return same(person, super_user)
        if (ManagersCrowd(self.context.person).contains(principal) or
            ClerksCrowd(self.context.person).contains(principal)):
            return True
        return (ConfigurableCrowd.contains(self, principal) and
                OwnerCrowd(self.context.person).contains(principal))
