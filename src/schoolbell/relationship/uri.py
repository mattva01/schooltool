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
URI objects.

Relationship types and roles are identified by URIs (the idea was borrowed
from XLink and RDF).  Instead of dealing with strings directly,
schoolbell.relationship uses introspectable URI objects that also have an
optional short name and a description in addition to the URI itself.

By convention, names of global URI object constants start with 'URI'.
"""

import re

from zope.interface import Interface, implements
from zope.schema import Text, TextLine, URI


class IURIObject(Interface):
    """An opaque identifier of a role or a relationship type.

    Roles and relationships are identified by URIs in XML representation.
    URI objects let the application assign human-readable names to roles
    and relationship types.

    URI objects are equal iff their uri attributes are equal.

    URI objects are hashable.
    """

    uri = URI(title=u"URI",
            description=u"The URI (as a string).")

    name = TextLine(title=u"Name",
            description=u"Human-readable name.")

    description = Text(title=u"Description",
            description=u"Human-readable description.")


class URIObject(object):
    """See IURIObject."""

    implements(IURIObject)

    def __init__(self, uri, name=None, description=''):
        if not looks_like_a_uri(uri):
            raise ValueError("This does not look like a URI: %r" % uri)
        self._uri = uri
        self._name = name
        self._description = description

    uri = property(lambda self: self._uri)
    name = property(lambda self: self._name)
    description = property(lambda self: self._description)

    def __eq__(self, other):
        return self.uri == other.uri

    def __ne__(self, other):
        return self.uri != other.uri

    def __hash__(self):
        return hash(self.uri)

    def __repr__(self):
        return '<URIObject %s>' % (self.name or self.uri)


def looks_like_a_uri(uri):
    r"""Check if the argument looks like a URI string.

    Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
    We're only approximating to the spec.

    Some examples of valid URI strings:

        >>> looks_like_a_uri('http://foo/bar?baz#quux')
        True
        >>> looks_like_a_uri('HTTP://foo/bar?baz#quux')
        True
        >>> looks_like_a_uri('mailto:root')
        True

    These strings are all invalid URIs:

        >>> looks_like_a_uri('2HTTP://foo/bar?baz#quux')
        False
        >>> looks_like_a_uri('\nHTTP://foo/bar?baz#quux')
        False
        >>> looks_like_a_uri('mailto:postmaster ')
        False
        >>> looks_like_a_uri('mailto:postmaster text')
        False
        >>> looks_like_a_uri('nocolon')
        False
        >>> looks_like_a_uri(None)
        False

    """
    uri_re = re.compile(r"^[A-Za-z][A-Za-z0-9+-.]*:\S\S*$")
    return bool(uri and uri_re.match(uri) is not None)

