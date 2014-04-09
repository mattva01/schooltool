#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005-2010 Shuttleworth Foundation
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
SchoolTool application
"""
import calendar
import os
import pytz

from persistent import Persistent
from persistent.dict import PersistentDict

from zope.location.location import LocationProxy
from zope.component import adapter, adapts
from zope.i18n import translate
from zope.interface import implementer, implements, implementsOnly

from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.app.applicationcontrol.interfaces import IApplicationControl
from zope.app.applicationcontrol.applicationcontrol import applicationController
from zope.component.hooks import getSite
from zope.site import SiteManagerContainer
from zope.container import sample
from zope.container.contained import NameChooser
from zope.container.interfaces import INameChooser
from zope.traversing.interfaces import IContainmentRoot

from schooltool.app.interfaces import IPluginInit, IPluginStartUp
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences, IApplicationTabs
from schooltool.app import relationships
from schooltool.app.interfaces import IAsset
from schooltool.relationship.relationship import RelationshipProperty
from schooltool.common import getRequestFromInteraction
from schooltool.common import SchoolToolMessage as _


class SchoolToolApplication(Persistent, sample.SampleContainer,
                            SiteManagerContainer):
    """The main application object.

    This object can be added as a regular content object to a folder,
    or it can be used as the application root object.
    """

    implements(ISchoolToolApplication, IAttributeAnnotatable, IContainmentRoot)

    def __init__(self):
        super(SchoolToolApplication, self).__init__()

    def _newContainerData(self):
        return PersistentDict()

    def _title(self):
        """This is required for the site calendar views to work.

        Calendar views expect that their underlying objects (calendar
        parents) have an attribute named `title`.
        """
        return IApplicationPreferences(self).title

    title = property(_title)


@adapter(None)
@implementer(ISchoolToolApplication)
def getSchoolToolApplication(ignore=None):
    """Return the nearest ISchoolToolApplication.

    This function is also registered as an adapter, so you
    can use it like this:

        app = ISchoolToolApplication(None)

    and stub it in unit tests.
    """
    candidate = getSite()
    if ISchoolToolApplication.providedBy(candidate):
        return candidate
    return None


class SimpleNameChooser(NameChooser):
    """A name chooser that uses object titles as names.

    SimpleNameChooser is an adapter for containers

        >>> class ContainerStub(dict):
        ...     __name__ = 'resources'
        >>> container = ContainerStub()
        >>> chooser = SimpleNameChooser(container)

    It expects objects to have a `title` attribute, so only register it
    as an adapter for containers that limit their contents to objects
    with such attribute.

    `chooseName` uses the title of the object to be added, converts it to
    lowercase, strips punctuation, and replaces spaces with hyphens:

        >>> from schooltool.person.person import Person
        >>> obj = Person(title='Mr. Smith')
        >>> chooser.chooseName('', obj)
        u'mr-smith'

    If the name is already taken, SimpleNameChooser adds a number at the end

        >>> container['mr-smith'] = 42
        >>> chooser.chooseName('', obj)
        u'mr-smith-2'

    If you provide a suggested name, it uses that one.

        >>> chooser.chooseName('suggested-name', obj)
        'suggested-name'

    Even if it has "illegal" characters:

        >>> chooser.chooseName('suggested name', obj)
        'suggested name'

    But it will add a number at the end:

        >>> chooser.chooseName('mr-smith', obj)
        u'mr-smith-2'

    Bad names cause errors

        >>> chooser.chooseName('@notallowed', obj)
        Traceback (most recent call last):
          ...
        ValueError: Names cannot begin with '+' or '@' or contain '/'

    If the name generated from the title gets shortened too much, we
    generate a name from the name of the context container instead:

        >>> obj.title = "foo-bar-baz-boo"
        >>> chooser.chooseName('', obj)
        'resource'

    So objects with semi empty titles get ids for them too:

        >>> obj.title = '---'
        >>> chooser.chooseName('', obj)
        'resource'

    """

    implements(INameChooser)

    def chooseName(self, name, obj):
        """See INameChooser."""
        if not name:
            name = u''.join([c for c in obj.title.lower()
                             if c.isalnum() or c == ' ']).replace(' ', '-')
            if len(name) + 2 < len(obj.title) or name == '':
                name = self.context.__name__[:-1]
        n = name
        i = 1
        while n in self.context:
            i += 1
            n = name + u'-' + unicode(i)
        # Make sure the name is valid
        self.checkName(n, obj)
        return n


class ApplicationPreferences(Persistent):
    """Object for storing any application-wide preferences we have.

    See schooltool.app.interfaces.ApplicationPreferences.
    """

    implements(IApplicationPreferences)

    __name__ = 'preferences'

    def getTitle(self):
        title = self.__dict__.get('title', None)
        if title:
            return title
        request = getRequestFromInteraction()
        return translate(_('Your School'), context=request)

    def setTitle(self, value):
        self.__dict__['title'] = value

    title = property(getTitle, setTitle)

    timezone = 'UTC'

    # XXX: initialize from locale
    dateformat = '%Y-%m-%d'
    timeformat = '%H:%M'
    weekstart = calendar.MONDAY

    frontPageCalendar = True

    logo = None

    name_sorting = 'last_name'

    def __init__(self):
        self.timezone = self._get_localzone()

    def _get_localzone(self):
        """Tries to find the local timezone configuration.

        Taken from https://github.com/regebro/tzlocal/
        only the part needed for Ubuntu.
        """
        tzpath = '/etc/timezone'
        if os.path.exists(tzpath):
            with open(tzpath, 'rb') as tzfile:
                data = tzfile.read()
                if data[:5] != 'TZif2':
                    etctz = data.strip().decode()
                    # Get rid of host definitions and comments:
                    if ' ' in etctz:
                        etctz, dummy = etctz.split(' ', 1)
                    if '#' in etctz:
                        etctz, dummy = etctz.split('#', 1)
                    if 'Etc/UTC' == etctz:
                        etctz = 'UTC'
                    try:
                        pytz.timezone(etctz)
                        return etctz
                    except pytz.UnknownTimeZoneError:
                        pass

        return 'UTC'


class ApplicationTabs(PersistentDict):
    """Object for storing application tab preferences.

    See schooltool.app.interfaces.ApplicationTabs.
    """

    implements(IApplicationTabs)

    default = 'calendar'


class Asset(object):
    """A mixin for objects that may act as assets."""

    implements(IAsset)

    leaders = RelationshipProperty(relationships.URILeadership,
                                   relationships.URIAsset,
                                   relationships.URILeader)


def getApplicationPreferences(app):
    """Adapt a SchoolToolApplication to IApplicationPreferences."""

    annotations = IAnnotations(app)
    key = 'schooltool.app.ApplicationPreferences'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = ApplicationPreferences()
        annotations[key].__parent__ = app
        return annotations[key]


def getApplicationTabs(app):
    """Adapt a SchoolToolApplication to IApplicationTabs."""

    annotations = IAnnotations(app)
    key = 'schooltool.app.ApplicationTabs'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = ApplicationTabs()
        annotations[key].__parent__ = app
        return annotations[key]


class SchoolToolInitializationUtility(object):

    def initializeApplication(self, app):
        """Perform school specific initialization.

        By default schooltool does not do any specific initialization.
        """


class ActionBase(object):
    adapts(ISchoolToolApplication)
    implements(IPluginInit)

    after = ()
    before = ()

    def __init__(self, app):
        self.app = app

    def __call__(self):
        raise NotImplementedError("This method should be overriden by"
                                  " inheriting classes")


class InitBase(ActionBase):
    implementsOnly(IPluginInit)


class StartUpBase(ActionBase):
    implementsOnly(IPluginStartUp)


@adapter(ISchoolToolApplication)
@implementer(IApplicationControl)
def getApplicationControl(app=None):
    return LocationProxy(applicationController, app, 'control')
