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

import re
from zope.interface import moduleProvides, implements
from schooltool.common import looks_like_a_uri
from schooltool.interfaces import IModuleSetup, ComponentLookupError
from schooltool.interfaces import IURIAPI, IURIObject
from schooltool.translation import ugettext as _

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
        self.uri = uri
        self.name = name
        self.description = description
        if not looks_like_a_uri(uri):
            raise ValueError("This does not look like a URI: %r" % uri)

    def __eq__(self, other):
        return self.uri == other.uri

    def __ne__(self, other):
        return self.uri != other.uri

    def __hash__(self):
        return hash(self.uri)


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

URIMembership = URIObject("http://schooltool.org/ns/membership",
                          _("Membership"),
                          _("The membership relationship."))


URIGroup = URIObject("http://schooltool.org/ns/membership/group",
                     _("Group"),
                     _("A role of a containing group."))


URIMember = URIObject("http://schooltool.org/ns/membership/member",
                      _("Member"),
                      _("A group member role."))


URITeaching = URIObject("http://schooltool.org/ns/teaching",
                        _("Teaching"),
                        _("The teaching relationship."))


URITeacher = URIObject("http://schooltool.org/ns/teaching/teacher",
                       _("Teacher"),
                       _("A role of a teacher."))


URITaught = URIObject("http://schooltool.org/ns/teaching/taught",
                      _("Taught"),
                      _("A role of a group that has a teacher."))


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

moduleProvides(IModuleSetup, IURIAPI)
