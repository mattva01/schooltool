#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
SchoolTool package URI definitions

$Id$
"""

from zope.interface import moduleProvides, implements
from schooltool.common import looks_like_a_uri
from schooltool.interfaces import IModuleSetup, ComponentLookupError
from schooltool.interfaces import IURIAPI, IURIObject
from schooltool.translation import TranslatableString as _

__metaclass__ = type


#
# URIs
#

class URIObject:
    """See IURIObject.

    The suggested naming convention for URIs is to prefix the
    interface names with 'URI'.
    """

    implements(IURIObject)

    def __init__(self, uri, name=None, description=''):
        if not looks_like_a_uri(uri):
            raise ValueError("This does not look like a URI: %r" % uri)
        self._uri = uri
        self._name = name
        self._description = description
        # `name` and `description` may be TranslatableStrings, so the
        # properties have to explicitly convert them to unicode to avoid
        # problems.  Do not convert them to unicode in the constructor,
        # because that could be too early.

    uri = property(lambda self: self._uri)
    name = property(lambda self: self._name and unicode(self._name))
    description = property(lambda self: self._description and
                           unicode(self._description))

    def __eq__(self, other):
        return self.uri == other.uri

    def __ne__(self, other):
        return self.uri != other.uri

    def __hash__(self):
        return hash(self.uri)

    def __repr__(self):
        return '<URIObject %s>' % (self.name or self.uri)


#
# URI API
#

def verifyURI(uri):
    """Raise TypeError if uri is not an IURIObject."""
    if not IURIObject.providedBy(uri):
        raise TypeError("URI must be an IURIObject (got %r)" % (uri,))


_uri_registry = {}


def resetURIRegistry():
    """Replace the URI registry with an empty one."""
    global _uri_registry
    _uri_registry = {}


def registerURI(uriobject):
    """Add a URI to the registry so it can be queried by the URI string."""
    if uriobject.uri not in _uri_registry:
        _uri_registry[uriobject.uri] = uriobject
    elif _uri_registry[uriobject.uri] is not uriobject:
        raise ValueError("Two objects with one URI:  "
                         "%r, %r" % (_uri_registry[uriobject.uri], uriobject))


def getURI(str):
    """Return an URI object for a given URI string."""
    try:
        return _uri_registry[str]
    except KeyError:
        raise ComponentLookupError(str)


def listURIs():
    """Return a list of all registered URIs."""
    return _uri_registry.values()


#
# Concrete URIs
#

URIMembership = URIObject(
                "http://schooltool.org/ns/membership",
                _("Membership"),
                _("The membership relationship."))

URIGroup = URIObject(
                "http://schooltool.org/ns/membership/group",
                _("Group"),
                _("A role of a containing group."))

URIMember = URIObject(
                "http://schooltool.org/ns/membership/member",
                _("Member"),
                _("A group member role."))


URITeaching = URIObject(
                "http://schooltool.org/ns/teaching",
                _("Teaching"),
                _("The teaching relationship."))

URITeacher = URIObject(
                "http://schooltool.org/ns/teaching/teacher",
                _("Teacher"),
                _("A role of a teacher."))

URITaught = URIObject(
                "http://schooltool.org/ns/teaching/taught",
                _("Taught"),
                _("A role of a group that has a teacher."))


URIOccupies = URIObject(
                "http://schooltool.org/ns/occupies",
                _("Occupies"),
                _("The occupation relationship"))

URICurrentlyResides = URIObject(
                "http://schooltool.org/ns/occupies/currentlyresides",
                _("Resides"),
                _("The role of a person in Occupies"))

URICurrentResidence = URIObject(
                "http://schooltool.org/ns/occupies/currentresidence",
                _("Residence"),
                _("The role of an Address in Occupies"))


URICalendarSubscription = URIObject(
                "http://schooltool.org/ns/calendar_subscription",
                _("Calendar subscription"),
                _("The calendar subscription relationship."))

URICalendarProvider = URIObject(
                "http://schooltool.org/ns/calendar_subscription/provider",
                _("Calendar provider"),
                _("A role of an object providing a calendar."))

URICalendarSubscriber = URIObject(
                "http://schooltool.org/ns/calendar_subscription/subscriber",
                _("Calendar subscriber"),
                _("A role of an object that subscribes to a calendar."))


URINoted = URIObject(
                "http://schooltool.org/ns/noted",
                _("Noted"),
                _("The notation relationship"))

URINotation = URIObject(
                "http://schooltool.org/ns/noted/notation",
                _("Notation"),
                _("The role of a note in Noted"))

URINotandum = URIObject(
                "http://schooltool.org/ns/noted/notandum",
                _("Notandum"),
                _("The role of a object in Noted"))

#
#  Configuration
#

def setUp():
    """See IModuleSetup"""
    registerURI(URIMembership)
    registerURI(URIMember)
    registerURI(URIGroup)
    registerURI(URITeacher)
    registerURI(URITeaching)
    registerURI(URITaught)
    registerURI(URIOccupies)
    registerURI(URICurrentlyResides)
    registerURI(URICurrentResidence)
    registerURI(URICalendarSubscription)
    registerURI(URICalendarProvider)
    registerURI(URICalendarSubscriber)
    registerURI(URINoted)
    registerURI(URINotation)
    registerURI(URINotandum)

moduleProvides(IModuleSetup, IURIAPI)
