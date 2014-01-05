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
SchoolTool application interfaces
"""

import zope.schema
import zope.schema.interfaces

from zope.component.interfaces import ObjectEvent, IObjectEvent
from zope.container.interfaces import IContainer
from zope.container.interfaces import IReadContainer
from zope.container.constraints import contains
from zope.interface import implements
from zope.interface import Interface, Attribute
from zope.location.interfaces import IContained
from zope.authentication.interfaces import IAuthentication, ILogout

from schooltool.app.utils import vocabulary
from schooltool.common.fields import Image
from schooltool.common import SchoolToolMessage as _
from schooltool.person.interfaces import ICalendarDisplayPreferences

# XXX: misplaced calendar integration
from schooltool.calendar.interfaces import ICalendarEvent
from schooltool.calendar.interfaces import ISchoolToolCalendarEvent
from schooltool.calendar.interfaces import ISchoolToolCalendar
from schooltool.calendar.interfaces import IWriteCalendar
from schooltool.calendar.interfaces import IHaveCalendar

import zope.formlib.textwidgets
zope.formlib.textwidgets._ = _
# Here we do a particulary evil thing: we override the translation (_) function
# in the textwidgets module.  This means that all the messages in that module
# are now in the 'schooltool' domain.  This is the list of the messages
# (don't remove the list, it is used in localizable string extraction).
textwidgets_strings=[_('Form input is not a file object'),
                     _("Invalid integer data"),
                     _("Invalid text data"),
                     _("Invalid textual data"),
                     _("Invalid unicode data"),
                     _("Invalid integer data"),
                     _("Invalid floating point data"),
                     _("Invalid datetime data")]


# Events

class IApplicationInitializationEvent(IObjectEvent):
    """The SchoolTool application is being initialized.

    Usually subscribers add something to the initialization process.
    """

class ApplicationInitializationEvent(ObjectEvent):
    implements(IApplicationInitializationEvent)


class IApplicationStartUpEvent(IObjectEvent):
    """The SchoolTool application has started up.

    A hook for plugin initialization.
    """

class ApplicationStartUpEvent(ObjectEvent):
    implements(IApplicationStartUpEvent)


class ICatalogSetUpEvent(IObjectEvent):
    """Old style notification that the SchoolTool catalogs are being initialized.

    Subject to deprecation.  Subscribers should no longer use this to set up their
    catalogs.
    """

class CatalogSetUpEvent(ObjectEvent):
    implements(ICatalogSetUpEvent)


class ICatalogStartUpEvent(IObjectEvent):
    """The SchoolTool catalogs has started up.

    A hook for catalog initialization.
    """

class CatalogStartUpEvent(ObjectEvent):
    implements(ICatalogStartUpEvent)


class ISchoolToolApplication(IReadContainer):
    """The main SchoolTool application object.

    The application is a read-only container with the following items:

        'persons' - IPersonContainer
        'groups' - IGroupContainer
        'resources' - IResourceContainer

    This object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """

    title = zope.schema.TextLine(
        title=_("Title"),
        required=True,
        description=_(
            "The name for the school or organization running "
            "this server.  This will be displayed on the public calendar, the "
            "bottom of all pages and in the page title."))


class IApplicationPreferences(ICalendarDisplayPreferences):
    """Preferences stored in an annotation on the SchoolToolApplication."""

    title = zope.schema.TextLine(
        title=_("Title"),
        required=True,
        description=_(
            "The name for the school or organization running "
            "this server.  This will be displayed on the public calendar, the "
            "bottom of all pages and in the page title."))

    frontPageCalendar = zope.schema.Bool(
        title=_("Front Page Calendar"),
        description=_(
            "Display site-wide calendar as the front page of the site."),
        required=False,
        default=True)

    logo = Image(
        title=_("School logo"),
        format="JPEG",
        required=False)

    name_sorting = zope.schema.Choice(
        title=_('Name sorting'),
        vocabulary=vocabulary([('first_name', _('First name')),
                               ('last_name', _('Last name'))]))


class IApplicationTabs(Interface):
    """Tab visible settings stored in an annotation on SchoolToolApplication."""


class ISchoolToolAuthentication(IAuthentication, ILogout):
    """A local authentication utility for SchoolTool"""

    def setCredentials(request, username, password):
        """Save the username and password in the session.

        If the credentials passed are invalid, ValueError is raised.
        """

    def clearCredentials(request):
        """Forget the username and password stored in a session"""


class ICalendarParentCrowd(Interface):
    """A crowd object that is used on a calendar's parent.

    This is just a marker interface.
    """

    def contains(principal):
        """Return True if principal is in the crowd."""


class IAsset(Interface):
    """An asset of a leader."""

    leaders = Attribute("Leaders of this asset")


class ICookieLanguageSelector(Interface):

    def getLanguageList():
        """Return the list of available languages."""

    def getSelectedLanguage():
        """Return the language that is currently selected."""

    def setSelectedLanguage():
        """Set the selected language into a cookie."""


class ISchoolToolInitializationUtility(Interface):

    def initializeApplication(app):
        """Perform school specific initialization. """


class IPluginAction(Interface):

    after = Attribute(
        """A list of action adapter names.
        This action must be executed after them.""")

    before = Attribute(
        """A list of action adapter names.
        This action must be executed before them.""")

    def __call__():
        """Perform plugin specific set up."""


class ICatalogStartUp(IPluginAction):
    """Set up SchoolTool catalogs."""


class IPluginInit(IPluginAction):
    """Perform plugin initialization when setting up the SchoolTool
    application."""


class IPluginStartUp(IPluginAction):
    """Execute plugin specific code on application startup."""


class ISchoolToolAuthenticationPlugin(ISchoolToolAuthentication):
    """A plugin for local schooltool authentication utility. """


class IVersionedCatalog(IContained):
    """Versioned catalog entry."""

    version = zope.schema.TextLine(
        title=u"Version",
        description=u"Current version of the catalog.")

    expired = zope.schema.Bool(
        title=u"Expired",
        description=u"Expired catalogs should be removed.")

    catalog = Attribute("""The catalog object.""")


class ICatalogs(IContainer):
    """Container of versioned catalogs."""

    contains(IVersionedCatalog)


class IRequestHelpers(Interface):
    """Easy access to common ST utils."""


class IRequestHelper(Interface):
    """Interface to query a request helper."""


class IRelationshipState(Interface):

    title = zope.schema.TextLine(
        title=_(u'Title'),
        required=True)

    code = zope.schema.TextLine(
        title=_(u'Code'),
        description=_(u"A short status code, preferably few symbols."),
        required=True)

    active = zope.schema.TextLine(
        title=_(u'Active'), required=True)


class IRelationshipStateContainer(IContainer):
    contains(IRelationshipState)


class IRelationshipStates(IContained):

    title = zope.schema.TextLine(
        title=_("Title"))

    states = zope.schema.Dict(
        title=_(u'Statuses'),
        description=_(u'Recipient addresses'),
        key_type=zope.schema.TextLine(title=u"Key"),
        value_type=zope.schema.Object(
            title=_(u"Status"),
            schema=IRelationshipState),
        min_length=1)

    system_titles = zope.schema.Dict(
        title=_(u'System state value descriptions'),
        description=_(u'Descriptions of state "active" values'),
        key_type=zope.schema.TextLine(title=u"Key"),
        value_type=zope.schema.TextLine(title=u"Description"),
        min_length=1)

    factory = Attribute(u'State factory')

    def __iter__():
        """Iterate through self.states values."""

    def getState(state_tuple):
        """Return app state given (meaning, code) tuple."""

    def getTitle(state_tuple):
        """Return state title given (meaning, code) tuple."""

    def getDescription(state_tuple):
        """Return state description given (meaning, code) tuple."""


class IRelationshipStateChoice(zope.schema.interfaces.IField):
    """A choice of temporal relationship states."""
