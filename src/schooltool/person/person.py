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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Person implementation and support objects

$Id$
"""

import sha
from persistent import Persistent

from zope.interface import implements
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import btree
from zope.app.container.contained import Contained
from zope.app.container.interfaces import IObjectAddedEvent

from schooltool.app.app import getSchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.membership import URIMembership, URIMember, URIGroup
from schooltool.app.overlay import OverlaidCalendarsProperty
from schooltool.person import interfaces
from schooltool.relationship import RelationshipProperty


class PersonContainer(btree.BTreeContainer):
    """Container of persons."""

    implements(interfaces.IPersonContainer, IAttributeAnnotatable)

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
    return sha.sha(password.encode('UTF-8')).digest()


def personAppCalendarOverlaySubscriber(event):
    """Add application calendar to overlays of all new persons.
    """
    if IObjectAddedEvent.providedBy(event):
        if interfaces.IPerson.providedBy(event.object):
            try:
                app = getSchoolToolApplication()
                event.object.overlaid_calendars.add(ISchoolToolCalendar(app))
            except ValueError:
                # If we get this we are probably in the initial new-site setup
                # or creating a new manager during startup.  This should be
                # safe to ignore since it will happen very infrequently
                # (perhaps only once) and the manager can easily add the site
                # calendar to his/her overlay in the overlay selection view.
                pass


def addPersonContainerToApplication(event):
    event.object['persons'] = PersonContainer()
