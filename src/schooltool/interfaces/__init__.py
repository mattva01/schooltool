#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
SchoolTool interfaces.

An interface is a formal description of the public API of an object (usually a
class instance, but sometimes a Python module as well).  Interfaces are
introspectable, that is, we can ask whether an object provides a specific
interface, or simply ask for a list of all interfaces that are provided by an
object.  As you've already gathered, a single object may provide more than one
interface.  Conversely, any given interface may be provided by many objects
that may be instances of completely unrelated classes.

We say that a class implements an interface if instances of that class provide
the interface.

Interfaces in SchoolTool are mostly used for documentation purposes.  One of
the reasons why they are all declared in a single group of modules module is to
keep the internal API documentation in one place, and to provide a coherent
picture of interactions between different objects.

$Id$
"""

from schooltool.unchanged import Unchanged  # reexport from here
from zope.interface import Interface
from zope.app.traversing.interfaces import IContainmentRoot, ITraversable
from zope.schema import Field, Object

# reexport
from schooltool.interfaces.auth import *
from schooltool.interfaces.fields import *
from schooltool.interfaces.uris import *
from schooltool.interfaces.component import *
from schooltool.interfaces.cal import *
from schooltool.interfaces.relationship import *
from schooltool.interfaces.facet import *
from schooltool.interfaces.event import *
from schooltool.interfaces.timetable import *
from schooltool.interfaces.app import *


#
# Modules
#

class IModuleSetup(Interface):
    """Module that needs initialization."""

    def setUp():
        """Initialize the module."""


#
# Exceptions
#

class AuthenticationError(Exception):
    """Bad username or password."""


#
# Services
#

class IServiceAPI(Interface):
    """Service API.

    There are a number of global services stored in the object database.  This
    API lets the code access those services.  The context argument passed to
    each of the functions in this API is an object connected to the containment
    hierarchy.  Looking up a service entails traversing up the chain of object
    parents until an object providing IServiceManager is found (usually this
    will be the root object).

    Every service has its own API defined in a separate interface.
    """

    def getEventService(context):
        """Return the global event service."""

    def getUtilityService(context):
        """Return the global utility service."""

    def getTimetableSchemaService(context):
        """Return the global timetable schema service."""

    def getTimePeriodService(context):
        """Return the global time period service."""

    def getTicketService(context):
        """Return the ticket service for authentication."""

    def getDynamicFacetSchemaService(context):
        """Return the global DynamicFacet schema service"""

    def getOptions(context):
        """Return an IOptions object found from the context."""


class IServiceManager(Interface):
    """Container of services"""

    eventService = Object(
        title=u"Event service for this application",
        schema=IEventService)

    utilityService = Object(
        title=u"Utility service for this application",
        schema=IUtilityService)

    timetableSchemaService = Object(
        title=u"Timetable schema service",
        schema=ITimetableSchemaService)

    timePeriodService = Object(
        title=u"Time period service",
        schema=ITimePeriodService)

    ticketService = Field(
        title=u"Ticket service")

    dynamicFacetSchemaService = Object(
        title=u"Info Facet schema service",
        schema=IDynamicFacetSchemaService)


#
# The main application object
#

class IApplication(IContainmentRoot, IServiceManager, ITraversable, IOptions):
    """The application object.

    Services (as given by IServiceManager) are found by attribute.

    Application objects (of which there currently are persons, groups and
    resources) form a second hierarchy in addition to the usual containment
    hierarchy that all objects form.  The second hierarchy is expressed
    by Membership relationships.  Roots of the membership hierarchy are found
    by getRoots().

    Application object containers are found by __getitem__.  They do not
    participate in the second (membership) hierarchy.  All application objects
    are children of application object containers if you look at the
    containment hierarchy.
    """

    def getRoots():
        """Return a sequence of root application objects."""

    def __getitem__(name):
        """Get the named application object container."""

    def keys():
        """List the names of application object containers."""
