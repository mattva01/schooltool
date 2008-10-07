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
from sets import Set

from zope.component import adapts
from zope.component import adapter
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import implements
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.intid.interfaces import IIntIds
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.container.btree import BTreeContainer
from zope.app.container.contained import Contained
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

    implements(ITimetableSchemaDay)

    def __init__(self, periods=(), homeroom_period_ids=None):
        if homeroom_period_ids is not None:
            for id in homeroom_period_ids:
                assert id in periods, "%s not in %s" % (id, periods)
        else:
            homeroom_period_ids = []

        self.periods = periods
        self.homeroom_period_ids = homeroom_period_ids

    def keys(self):
        return self.periods

    def items(self):
        return [(period, Set()) for period in self.periods]

    def __getitem__(self, period):
        if period not in self.periods:
            raise KeyError(period)
        return Set()

    def __eq__(self, other):
        if ITimetableSchemaDay.providedBy(other):
            return (self.periods, self.homeroom_period_ids) == \
                    (other.periods, other.homeroom_period_ids)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


class TimetableSchema(Persistent, Contained):

    implements(ITimetableSchemaContained, ITimetableSchemaWrite)

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

    def __setitem__(self, key, value):
        if not ITimetableSchemaDay.providedBy(value):
            raise TypeError("Timetable schema can only contain"
                            " ITimetableSchemaDay objects (got %r)" % (value,))
        elif key not in self.day_ids:
            raise ValueError("Key %r not in day_ids %r" % (key, self.day_ids))
        self.days[key] = value

    def createTimetable(self, term):
        new = Timetable(self.day_ids)
        new.model = self.model
        new.timezone = self.timezone
        new.schooltt = self
        new.term = term
        for day_id in self.day_ids:
            new[day_id] = TimetableDay(self[day_id].periods,
                                       self[day_id].homeroom_period_ids)
        return new

    def __eq__(self, other):
        if ITimetableSchema.providedBy(other):
            return (self.items() == other.items()
                    and self.model == other.model
                    and self.timezone == other.timezone)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


class TimetableSchemaContainerContainer(BTreeContainer):
    """Container of Timetable Schema Containers."""

    implements(ITimetableSchemaContainerContainer,
               IAttributeAnnotatable)


class TimetableSchemaContainer(BTreeContainer):

    implements(ITimetableSchemaContainer, IAttributeAnnotatable)

    _default_id = None

    def _set_default_id(self, new_id):
        if new_id is not None and new_id not in self:
            raise ValueError("Timetable schema %r does not exist" % new_id)
        self._default_id = new_id

    default_id = property(lambda self: self._default_id, _set_default_id)

    def __setitem__(self, schema_id, ttschema):
        assert ITimetableSchema.providedBy(ttschema)
        if self.has_key(schema_id):
            BTreeContainer.__delitem__(self, schema_id)
        BTreeContainer.__setitem__(self, schema_id, ttschema)
        if self.default_id is None:
            self.default_id = schema_id

    def __delitem__(self, schema_id):
        BTreeContainer.__delitem__(self, schema_id)
        if schema_id == self.default_id:
            self.default_id = None

    def getDefault(self):
        return self[self.default_id]

def clearTimetablesOnDeletion(obj, event):
    """
    This event subscriber for term and schema will remove all timetable
    related to the term
    """
    object = event.object
    for tt in findRelatedTimetables(obj):
        ttdict = getParent(tt)
        del ttdict[getName(tt)]


@adapter(ISchoolToolApplication)
@implementer(ITimetableSchemaContainer)
def getTimetableSchemaContainerForApp(app):
    syc = ISchoolYearContainer(app)
    sy = syc.getActiveSchoolYear()
    if sy is not None:
        return ITimetableSchemaContainer(sy)


@adapter(ISchoolYear)
@implementer(ITimetableSchemaContainer)
def getTimetableSchemaContainer(sy):
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    cc = app['schooltool.timetable.schooltt'].get(sy_id, None)
    if cc is None:
        cc = app['schooltool.timetable.schooltt'][sy_id] = TimetableSchemaContainer()
    return cc


@adapter(ITerm)
@implementer(ITimetableSchemaContainer)
def getTimetableSchemaContainerForTerm(term):
    return ITimetableSchemaContainer(ISchoolYear(term))


@adapter(ITimetableSchemaContainer)
@implementer(ISchoolYear)
def getSchoolYearForTimetableSchemaContainer(ttschema_container):
    container_id = int(ttschema_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


@adapter(ITimetableSchema)
@implementer(ISchoolYear)
def getSchoolYearForTTschema(ttschema):
    return ISchoolYear(ttschema.__parent__)


def locationCopy(loc):
    tmp = StringIO()
    persistent = CopyPersistent(loc)

    # Pickle the object to a temporary file
    pickler = cPickle.Pickler(tmp, 2)
    pickler.persistent_id = persistent.id
    pickler.dump(loc)

    # Now load it back
    tmp.seek(0)
    unpickler = cPickle.Unpickler(tmp)
    unpickler.persistent_load = persistent.load
    return unpickler.load()


class InitSchoolTimetablesForNewSchoolYear(ObjectEventAdapterSubscriber):
    adapts(IObjectAddedEvent, ISchoolYear)

    def __call__(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        active_schoolyear = syc.getActiveSchoolYear()

        if active_schoolyear is not None:
            new_container = ITimetableSchemaContainer(self.object)
            old_container = ITimetableSchemaContainer(active_schoolyear)
            for schooltt in old_container.values():
                new_schooltt = locationCopy(schooltt)
                new_schooltt.__parent__ = None
                new_container[new_schooltt.__name__] = new_schooltt
