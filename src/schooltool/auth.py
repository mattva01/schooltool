#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
SchoolTool authentication service.

$Id$
"""

import sha
import time
import random
import datetime
import itertools

from persistent import Persistent
from BTrees.OOBTree import OOBTree
from zope.interface import implements
from sets import Set

from persistent.dict import PersistentDict
from schooltool.db import PersistentPairKeysDict
from schooltool.interfaces import AuthenticationError, IACL, ILocation
from schooltool.interfaces import Everybody, ViewPermission
from schooltool.interfaces import ModifyPermission, AddPermission
from schooltool.interfaces import IACLOwner, IRelatable
from schooltool.component import getRelatedObjects
from schooltool.uris import URIGroup

__metaclass__ = type


class TicketService(Persistent):
    """Ticket service for authentication.

    The idea of using a ticket service for authentication is that once the
    credentials are verified in a login form, the user gets a ticket for this
    session.  The ticket is usually stored as a browser cookie.

      >>> service = TicketService()
      >>> ticket = service.newTicket(('rms', ''))

    The ticket can be used to extract the credentials from the ticket service:

      >>> service.verifyTicket(ticket)
      ('rms', '')

      >>> service.verifyTicket('fake ticket')
      Traceback (most recent call last):
        ...
      AuthenticationError

    The ticket itself is a random string, so it is not possible to extract the
    username and password from the ticket if it gets stolen.  Also, the ticket
    can expire after a certain duration.  We will demonstrate it by specifying
    a ridiculously low duration of zero seconds:

      >>> import datetime
      >>> ticket2 = service.newTicket(('user', 'password'),
      ...                             datetime.timedelta(0))
      >>> service.verifyTicket(ticket2)
      Traceback (most recent call last):
        ...
      AuthenticationError

    (If you see test failures here, make sure that your clock does not go
    backwards.  It has happened to some people!  Note that ZODB is known to be
    unhappy with nonmonotonic clocks.)

    Note that we did not specify a duration in the first example -- in that
    case the ticket will never expire automatically.

    It is always possible to forcefully expire a ticket before its expiration
    deadline is reached:

      >>> service.verifyTicket(ticket)
      ('rms', '')
      >>> service.expire(ticket)
      >>> service.verifyTicket(ticket)
      Traceback (most recent call last):
        ...
      AuthenticationError

    It is a very good idea to expire a user's ticket when the user logs out.

    It is also possible to change the expiration time for a ticket if it is
    being used, by passing a duration argument to verifyTicket:

      >>> ticket = service.newTicket(('user', 'password'),
      ...                            datetime.timedelta(minutes=1))
      >>> service.verifyTicket(ticket, datetime.timedelta(minutes=2))
      ('user', 'password')

    We could now do time.sleep(61) and call verifyTicket to make sure the
    expiration time is updated, but that would slow down unit tests
    considerably.  Instead, we'll shorten the expiration time to 0 seconds:

      >>> service.verifyTicket(ticket, datetime.timedelta(minutes=0))
      ('user', 'password')
      >>> service.verifyTicket(ticket)
      Traceback (most recent call last):
        ...
      AuthenticationError

    """

    def __init__(self):
        self._tickets = OOBTree()

    def newTicket(self, credentials, duration=None):
        """Allocate a new ticket for given credentials.

        Returns the ticket -- a hard-to-guess random alphanumeric string.

        The ticket will automatically expire after a specified duration.  If
        duration is None, the ticket will not expire automatically.  A given
        ticket can expire earlier, if expire method is called.

        Credentials can be any object -- usually it will be a tuple containing
        the username and password.  Do not put persistent objects into the
        ticket service.
        """
        ticket = sha.new('%s-%s' % (random.random(), time.time())).hexdigest()
        if duration is None:
            expires = datetime.datetime.max
        else:
            expires = datetime.datetime.now() + duration
        self._tickets[ticket] = (credentials, expires)
        return ticket

    def verifyTicket(self, ticket, duration=None):
        """Verify a ticket and return the credentials associated with it.

        Raises AuthenticationError if the ticket is not valid or has expired.

        If the 'duration' argument is not None, and the ticket is valid, its
        expiration time is updated to be a specified duration from now.
        """
        try:
            credentials, expires = self._tickets[ticket]
        except KeyError:
            raise AuthenticationError
        else:
            if datetime.datetime.now() >= expires:
                try:
                    del self._tickets[ticket]
                except KeyError:
                    # just in case two threads access the same expired ticket
                    # at the same time
                    pass
                raise AuthenticationError
            else:
                if duration is not None:
                    expires = datetime.datetime.now() + duration
                    self._tickets[ticket] = (credentials, expires)
                    # There is a very small race condition.  It is possible,
                    # that after we verify a ticket just before its expiration,
                    # but before we update the new expiration time in the
                    # store, another thread might try to verify the same ticket
                    # and decide that it is expired.
                return credentials

    def expire(self, ticket):
        """Forcefully expire a ticket.

        Let's create a ticket first:

          >>> service = TicketService()
          >>> ticket = service.newTicket(('u', 'p'),
          ...                            datetime.timedelta(hours=2))
          >>> service.verifyTicket(ticket)
          ('u', 'p')

        Once you expire the ticket, it is no longer valid:

          >>> service.expire(ticket)
          >>> service.verifyTicket(ticket)
          Traceback (most recent call last):
            ...
          AuthenticationError

        You can call expire on tickets that are not valid or have expired
        already:

          >>> service.expire(ticket)

        """
        try:
            del self._tickets[ticket]
        except KeyError:
            pass


class ACL(Persistent):
    """Access coltrol list

    I'd like to put the 'Everybody' marker into _data, but our
    principals have to be persistent.  So I'm going the simplest way
    -- special case Everybody in this class.  The alternative would be
    to create MaybePersistentPairKeysDict (see schooltool.db).
    """

    implements(IACL, ILocation)

    __name__ = 'acl'
    __parent__ = None

    def __init__(self):
        self._data = PersistentPairKeysDict()
        self._everybody = PersistentDict()

    def __iter__(self):
        """Iterate over tuples of (principal, permission)."""
        return itertools.chain(iter(self._data),
                               iter([(Everybody, perm)
                                     for perm in self._everybody]))

    def __contains__(self, (principal,  permission)):
        """Return True iff principal has permission."""
        if not permission in (ViewPermission, ModifyPermission, AddPermission):
            raise ValueError("Bad permission: %r" % (permission,))
        if principal == Everybody:
            return permission in self._everybody
        if principal is None:
            return False
        else:
            return (principal, permission) in self._data

    def add(self, (principal, permission)):
        """Grant permission to principal."""
        if not permission in (ViewPermission, ModifyPermission, AddPermission):
            raise ValueError("Bad permission: %r" % (permission,))
        if principal == Everybody:
            self._everybody[permission] = 1
        else:
            self._data[(principal, permission)] = 1

    def remove(self, (principal, permission)):
        """Revoke permission from principal."""
        if not permission in (ViewPermission, ModifyPermission, AddPermission):
            raise ValueError("Bad permission: %r" % (permission,))
        if principal == Everybody:
            del self._everybody[permission]
        else:
            del self._data[(principal, permission)]

    def allows(self, principal, permission):
        """Tell if principal has permission."""
        if permission in self._everybody:
            return True
        if principal is not None:
            for group in getAncestorGroups(principal):
                if (group, permission) in self:
                    return True
        return (principal, permission) in self

    def clear(self):
        """Revoke all access from all principals."""
        self._data.clear()
        self._everybody.clear()


def getAncestorGroups(person):
    """Returns a set of ancestor groups of a person"""
    if not IRelatable.providedBy(person):
        return ()
    ancestors = Set()
    def getAncestors(obj):
        for parent in getRelatedObjects(obj, URIGroup):
            if parent not in ancestors:
                ancestors.add(parent)
                getAncestors(parent)
    getAncestors(person)
    return ancestors


def getACL(context):
    """Returns the ACL used for the context.

    Raises a ValueError if context does not have an ACL.
    """
    obj = context
    while True:
        if IACLOwner.providedBy(obj):
            return obj.acl
        if ILocation.providedBy(obj):
            obj = obj.__parent__
            continue
        raise ValueError("Could not find ACL for %r" % (context, ))
