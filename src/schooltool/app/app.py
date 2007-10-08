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
SchoolTool application

$Id$

"""
import calendar

from persistent import Persistent
from persistent.dict import PersistentDict

from zope.location.location import LocationProxy
from zope.component import adapter
from zope.component import adapts
from zope.event import notify
from zope.interface import implementer
from zope.interface import implements
from zope.interface import classProvides
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema.interfaces import IVocabularyFactory

from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.app.applicationcontrol.interfaces import IApplicationControl
from zope.app.applicationcontrol.applicationcontrol import applicationController
from zope.app.component.hooks import getSite
from zope.app.component.site import SiteManagerContainer
from zope.app.container import sample
from zope.app.container.contained import NameChooser
from zope.app.container.interfaces import INameChooser
from zope.traversing.interfaces import IContainmentRoot

from schooltool.traverser.traverser import AdapterTraverserPlugin
from schooltool.app.overlay import ICalendarOverlayInfo
from schooltool.app.interfaces import IPluginInit
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import IShowTimetables
from schooltool.app.interfaces import ApplicationInitializationEvent
from schooltool.app import relationships
from schooltool.app.interfaces import IAsset
from schooltool.app.interfaces import ISchoolToolInitializationUtility
from schooltool.relationship.relationship import RelationshipProperty


SHOW_TIMETABLES_KEY = 'schooltool.timetable.showTimetables'


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
    else:
        raise ValueError("can't get a SchoolToolApplication")


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
        UserError: Names cannot begin with '+' or '@' or contain '/'

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

    title = 'SchoolTool'

    timezone = 'UTC'

    dateformat = '%Y-%m-%d'

    timeformat = '%H:%M'

    weekstart = calendar.MONDAY

    frontPageCalendar = True


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


class ShowTimetables(object):
    """Adapter from ICalendarOverlayInfo to IShowTimetables.

        >>> from zope.app.testing import setup
        >>> setup.setUpAnnotations()

        >>> from zope.interface import classImplements
        >>> from schooltool.app.overlay import CalendarOverlayInfo
        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> classImplements(CalendarOverlayInfo, IAttributeAnnotatable)

        >>> calendar = object()
        >>> info = CalendarOverlayInfo(calendar, True, 'red', 'yellow')
        >>> info.__parent__ = calendar
        >>> stt = ShowTimetables(info)

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IShowTimetables, stt)
        True

        >>> stt.showTimetables
        True

    The `showTimetables` attribute is changeable:

        >>> stt.showTimetables = False
        >>> stt.showTimetables
        False

    We need a __parent__ attribute for local security grants:

        >>> stt.__parent__ is calendar
        True

    """

    adapts(ICalendarOverlayInfo)
    implements(IShowTimetables)

    def __init__(self, context):
        self.annotations = IAnnotations(context)
        self.__parent__ = context.__parent__ # for local security grants

    def getShowTimetables(self):
        return self.annotations.get(SHOW_TIMETABLES_KEY, True)

    def setShowTimetables(self, value):
        self.annotations[SHOW_TIMETABLES_KEY] = value

    showTimetables = property(getShowTimetables, setShowTimetables)


class SchoolToolInitializationUtility(object):

    def initializeApplication(self, app):
        """Perform school specific initialization.

        By default schooltool does not do any specific initialization.
        """


class InitBase(object):

    implements(IPluginInit)

    def __init__(self, app):
        self.app = app

    def __call__(self):
        raise NotImplementedError("This method should be overriden by"
                                  " inheriting classes")


ApplicationControlTraverserPlugin = AdapterTraverserPlugin(
    'control', IApplicationControl)


@adapter(ISchoolToolApplication)
@implementer(IApplicationControl)
def getApplicationControl(app=None):
    return LocationProxy(applicationController, app, 'control')
