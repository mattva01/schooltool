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
from zope.interface import Interface, moduleProvides
from zope.interface.interfaces import IInterface
from schooltool.interfaces import IModuleSetup, ComponentLookupError
from schooltool.common import dedent
from schooltool.translation import gettext

__metaclass__ = type


#
# URIs
#

class ISpecificURI(Interface):
    """Base interface for URIs.

    All interfaces derived from this must have the URI they map on
    to as the first line of their docstring.  The second paragraph
    should contain just a short user-visible name.

    Examples::

        class URITutor(ISpecificURI):
            '''http://schooltool.org/ns/tutor

            Tutor
            '''

        class URITutor(ISpecificURI):
            '''http://schooltool.org/ns/tutor

            Tutor

            A person who is responsible for a registration class.
            '''

    The suggested naming convention for URIs is to prefix the
    interface names with 'URI'.
    """


class IURIAPI(Interface):

    def inspectSpecificURI(uri, translate=True):
        """Return a tuple of a URI, title and the description of an
        ISpecificURI.

        If translate is True, the title and the description are 
        returned translated.

        Raises a TypeError if the argument is not ISpecificURI.
        Raises a ValueError if the URI's docstring does not conform.
        """

    def strURI(uri):
        """Return the URI of ISpecificURI as a string."""

    def nameURI(uri):
        """Return the user-visible title of ISpecificURI as a string.

        Returns None if the URI does not have a title.
        """

    def isURI(uri):
        """Check if the argument looks like a URI.

        Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
        We're only approximating to the spec.
        """

    def registerURI(uri):
        """Add a URI to the registry so it can be queried by the URI string."""

    def getURI(str):
        """Return an ISpecificURI for a given URI string."""


#
# URI API
#

def inspectSpecificURI(uri, translate=True):
    """See IURIAPI."""
    if not IInterface.providedBy(uri):
        raise TypeError("URI must be an interface (got %r)" % (uri,))

    if not uri.extends(ISpecificURI, True):
        raise TypeError("URI must strictly extend ISpecificURI (got %r)" %
                        (uri,))

    segments = uri.__doc__.split("\n\n", 2)
    uri = segments[0].strip()
    if not isURI(uri):
        raise ValueError("This does not look like a URI: %r" % uri)

    if len(segments) > 1:
        title = segments[1].strip()
    else:
        title = None

    if len(segments) > 2:
        doc = dedent(segments[2]).strip()
    else:
        doc = ""

    if translate:
        title, doc = gettext(title), gettext(doc)

    return uri, title, doc


def isURI(uri):
    """Checks if the argument looks like a URI.

    Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
    We're only approximating to the spec.
    """
    uri_re = re.compile(r"^[A-Za-z][A-Za-z0-9+-.]*:\S\S*$")
    return uri_re.search(uri)


def strURI(uri):
    """See IURIAPI."""
    return inspectSpecificURI(uri)[0]


def nameURI(uri):
    """See IURIAPI."""
    return inspectSpecificURI(uri)[1]


_uri_registry = {}


def resetURIRegistry():
    """Replace the URI registry with an empty one."""
    global _uri_registry
    _uri_registry = {}


def registerURI(uri):
    """Adds an ISpecificURI to the registry so it can be queried by
    the URI string."""
    str_uri = strURI(uri)
    if str_uri in _uri_registry:
        if _uri_registry[str_uri] is not uri:
            raise ValueError("Two interfaces with one URI:  "
                             "%r, %r" % (_uri_registry[str_uri], uri))
        else:
            return
    else:
        _uri_registry[str_uri] = uri


def getURI(str):
    """Returns and ISpecificURI with a given URI string."""
    try:
        return _uri_registry[str]
    except KeyError:
        raise ComponentLookupError(str)


#
# Concrete URIs
#

class URIGroup(ISpecificURI):
    """http://schooltool.org/ns/membership/group

    Group

    A role of a containing group.
    """


class URIMember(ISpecificURI):
    """http://schooltool.org/ns/membership/member

    Member

    A group member role.
    """


class URIMembership(ISpecificURI):
    """http://schooltool.org/ns/membership

    Membership

    The membership relationship.
    """


class URITeaching(ISpecificURI):
    """http://schooltool.org/ns/teaching

    Teaching
    """


class URITeacher(ISpecificURI):
    """http://schooltool.org/ns/teaching/teacher

    Teacher
    """


class URITaught(ISpecificURI):
    """http://schooltool.org/ns/teaching/taught

    Taught
    """


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
