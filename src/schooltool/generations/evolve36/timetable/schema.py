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
Timetable Schemas
"""
import cPickle
from StringIO import StringIO
from persistent import Persistent
from persistent.dict import PersistentDict

from zope.component import adapts
from zope.component import adapter
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import implements
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.container.btree import BTreeContainer
from zope.container.contained import Contained
from zope.traversing.api import getParent, getName
from zope.location.pickling import CopyPersistent

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.term.interfaces import ITerm
from schooltool.timetable import Timetable, TimetableDay, findRelatedTimetables

from schooltool.timetable.interfaces import ITimetableSchema
from schooltool.timetable.interfaces import ITimetableSchemaContained
from schooltool.timetable.interfaces import ITimetableSchemaContainerContainer
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.interfaces import ITimetableSchemaDay
from schooltool.timetable.interfaces import ITimetableSchemaWrite
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber


class TimetableSchemaDay(Persistent):
    """A day in a timetable schema.

    A timetable day is an ordered collection of periods.

    Different days within the same timetable schema may have different periods.

    ITimetableSchemaDay has keys, items and __getitem__ for interface
    compatibility with ITimetableDay -- so that, for example, views for
    ITimetable can be used to render ITimetableSchemas.
    """

    implements(ITimetableSchemaDay)

    periods = None # list of period IDs for this day
    homeroom_period_ids = None # list of homeroom period IDs

    def __init__(self, periods=(), homeroom_period_ids=None):
        """
        periods: list of titles/IDs
        homeroom_period_ids: non-persistent list of homeroom IDs
        """

    def keys(self):
        return self.periods

    def items(self):
        return [(period, set()) for period in self.periods]

    def __getitem__(self, period):
        # XXX: wow...
        if period not in self.periods:
            raise KeyError(period)
        return set()


class TimetableSchema(Persistent, Contained):
    """A timetable schema.

    A timetable schema is an ordered collection of timetable days that contain
    periods.
    """
    implements(ITimetableSchemaContained, ITimetableSchemaWrite)

    title = None
    model = None # timetable model
    timezone = None

    day_ids = None # day IDs within this timetable

    # PersistentDict
    # keys - only from day_ids
    # values - implementing ITimetableDay only
    days = None


    def __init__(self, day_ids, title=None, model=None, timezone='UTC'):
        """Create a new empty timetable schema.

        day_ids is a sequence of the day ids of this timetable.

        The caller must then assign a TimetableDay for each day ID and
        set the model before trying to use the timetable.
        """
        self.title = title
        if self.title is None:
            self.title = "Schema"
        self.day_ids = day_ids
        self.days = PersistentDict()
        self.model = model
        self.timezone = timezone

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days[day]) for day in self.day_ids]

    def __getitem__(self, key):
        return self.days[key]

    def createTimetable(self, term):
        """Return a new empty timetable with the same structure.

        The new timetable has the same set of day_ids, and the sets of
        period ids within each day.  It has no activities.

        The new timetable is bound to the term passed as the argument.
        """


class TimetableSchemaContainerContainer(BTreeContainer):
    """Container  of Timetable Schema Containers [for each school year]."""
    implements(ITimetableSchemaContainerContainer,
               IAttributeAnnotatable)


class TimetableSchemaContainer(BTreeContainer):
    """Container of schemas for a school year."""
    implements(ITimetableSchemaContainer, IAttributeAnnotatable)

    _default_id = None # default schema for calendars

    default_id = property(lambda self: self._default_id)

    def __delitem__(self, schema_id):
        BTreeContainer.__delitem__(self, schema_id)
        if schema_id == self.default_id:
            self.default_id = None

    def getDefault(self):
        """Default schema for the school year.
        Used in resource booking calendar
        and in daily calendar views to display default periods.
        """
        return self[self.default_id]


#
# Integration
#
#


def clearTimetablesOnDeletion(obj, event):
    """Integration: on term deletion, remove all timetables for the term"""
    for tt in findRelatedTimetables(obj):
        ttdict = getParent(tt)
        del ttdict[getName(tt)]


@adapter(ISchoolYear)
@implementer(ITimetableSchemaContainer)
def getTimetableSchemaContainer(sy):
    """Integration: schema containers for all school years"""
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    cc = app['schooltool.timetable.schooltt'].get(sy_id, None)
    if cc is None:
        cc = app['schooltool.timetable.schooltt'][sy_id] = TimetableSchemaContainer()
    return cc


#def locationCopy(loc):
#    tmp = StringIO()
#    persistent = CopyPersistent(loc)
#
#    # Pickle the object to a temporary file
#    pickler = cPickle.Pickler(tmp, 2)
#    pickler.persistent_id = persistent.id
#    pickler.dump(loc)
#
#    # Now load it back
#    tmp.seek(0)
#    unpickler = cPickle.Unpickler(tmp)
#    unpickler.persistent_load = persistent.load
#    return unpickler.load()
