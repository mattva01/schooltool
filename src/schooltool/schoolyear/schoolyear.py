#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
School year implementation
"""
import rwproperty

from zope.event import notify
from zope.exceptions.interfaces import UserError
from zope.component import queryUtility
from zope.component import adapter
from zope.component import adapts
from zope.interface import implementer
from zope.interface import implements
from zope.app.container.btree import BTreeContainer

from schooltool.common import DateRange
from schooltool.common import IDateRange
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import InitBase
from schooltool.term.interfaces import IDateManager
from schooltool.term.interfaces import ITermContainer
from schooltool.schoolyear.subscriber import EventAdapterSubscriber
from schooltool.schoolyear.interfaces import TermOverlapError
from schooltool.schoolyear.interfaces import SchoolYearOverlapError
from schooltool.schoolyear.interfaces import ISubscriber
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer

SCHOOLYEAR_CONTAINER_KEY = 'schooltool.schoolyear'


class SchoolYearBeforeChangeEvent(object):

    def __init__(self, schoolyear, old_dates, new_dates):
        self.schoolyear = schoolyear
        self.old_dates = old_dates
        self.new_dates = new_dates


class SchoolYearAfterChangeEvent(object):

    def __init__(self, schoolyear, old_dates, new_dates):
        self.schoolyear = schoolyear
        self.old_dates = old_dates
        self.new_dates = new_dates


class SchoolYearContainer(BTreeContainer):
    implements(ISchoolYearContainer)

    _active_id = None

    def _set_active_id(self, new_id):
        if new_id is not None and new_id not in self:
            raise ValueError("School Year %r does not exist" % new_id)
        self._active_id = new_id

    active_id = property(lambda self: self._active_id)

    def __delitem__(self, schoolyear_id):
        if schoolyear_id == self.active_id:
            if len(self.values()) > 1:
                raise ValueError("Can not delete an active schoolyear, unless"
                                 " it is the last school year available!")
            else:
                self._set_active_id(None)
        BTreeContainer.__delitem__(self, schoolyear_id)

    def validateForOverlap(self, schoolyear):
        overlapping_schoolyears = []
        for other_schoolyear in self.values():
            if IDateRange(schoolyear).overlaps(IDateRange(other_schoolyear)):
                overlapping_schoolyears.append(other_schoolyear)

        if overlapping_schoolyears:
            raise SchoolYearOverlapError(schoolyear, overlapping_schoolyears)

    def __setitem__(self, key, schoolyear):
        self.validateForOverlap(schoolyear)
        BTreeContainer.__setitem__(self, key, schoolyear)
        if self.active_id is None:
            self._set_active_id(key)

    def getActiveSchoolYear(self):
        if self.active_id:
            return self[self.active_id]
        return None

    @property
    def sorted_schoolyears(self):
        return sorted(self.values(), key=lambda s: s.last)

    def activateNextSchoolYear(self):
        next_school_year = self.getNextSchoolYear()
        if next_school_year is not None:
            self._set_active_id(next_school_year.__name__)

    def getSchoolYearForToday(self):
        dtm = queryUtility(IDateManager)
        today = dtm.today
        for year in self.sorted_schoolyears:
            if today in year:
                return year

    def getNextSchoolYear(self):
        if self.getActiveSchoolYear() is None:
            return None

        this_schoolyear_index = self.sorted_schoolyears.index(self.getActiveSchoolYear())
        next_schoolyear_index = this_schoolyear_index + 1
        if next_schoolyear_index < len(self.sorted_schoolyears):
            return self.sorted_schoolyears[next_schoolyear_index]

        return None


class SchoolYear(BTreeContainer):
    implements(ITermContainer, ISchoolYear)

    def __init__(self, title, first, last):
        self.title = title
        self._first = first
        self._last = last
        if last < first:
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))
        BTreeContainer.__init__(self)

    @rwproperty.getproperty
    def first(self):
        return self._first

    @rwproperty.setproperty
    def first(self, new_first_date):
        old_dates = (self._first, self._last)
        new_dates = (new_first_date, self._last)

        if self._last < new_first_date:
            raise ValueError("Last date %r less than first date %r" %
                             (self._last, new_first_date))

        notify(SchoolYearBeforeChangeEvent(self, old_dates, new_dates))
        self._first = new_first_date
        notify(SchoolYearAfterChangeEvent(self, old_dates, new_dates))

    @rwproperty.getproperty
    def last(self):
        return self._last

    @rwproperty.setproperty
    def last(self, new_last_date):
        old_dates = (self._first, self._last)
        new_dates = (self._first, new_last_date)

        if new_last_date < self._first:
            raise ValueError("Last date %r less than first date %r" %
                             (new_last_date, self._first))

        notify(SchoolYearBeforeChangeEvent(self, old_dates, new_dates))
        self._last = new_last_date
        notify(SchoolYearAfterChangeEvent(self, old_dates, new_dates))

    def validateForOverlap(self, term):
        overlapping_terms = []
        for other_term in self.values():
            if term.overlaps(other_term):
                overlapping_terms.append(other_term)

        if overlapping_terms:
            raise TermOverlapError(term, overlapping_terms)

    def __setitem__(self, key, term):
        self.validateForOverlap(term)
        if term.first < self.first:
            raise UserError("Term can't start before the school year starts!")
        if term.last > self.last:
            raise UserError("Term can't end after the school year ends!")
        BTreeContainer.__setitem__(self, key, term)


class SchoolYearDateRangeAdapter(DateRange):
    adapts(ISchoolYear)
    implements(IDateRange)

    def __init__(self, context):
        self.context = context

    @rwproperty.setproperty
    def first(self, new_first_date):
        self.context.first = new_first_date

    @rwproperty.getproperty
    def first(self):
        return self.context.first

    @rwproperty.setproperty
    def last(self, new_last_date):
        self.context.first = new_last_date

    @rwproperty.getproperty
    def last(self):
        return self.context.last


@adapter(ISchoolToolApplication)
@implementer(ISchoolYearContainer)
def getSchoolYearContainer(app):
    return app[SCHOOLYEAR_CONTAINER_KEY]


class SchoolYearInit(InitBase):

    adapts(ISchoolToolApplication)

    def __call__(self):
        self.app[SCHOOLYEAR_CONTAINER_KEY] = SchoolYearContainer()


class SchoolYearOverlapValidationSubscriber(EventAdapterSubscriber):
    adapts(SchoolYearBeforeChangeEvent)
    implements(ISubscriber)

    def __call__(self):
        dr = DateRange(*self.event.new_dates)
        syc = self.event.schoolyear.__parent__
        if syc:
            overlapping_schoolyears = []
            for other_schoolyear in syc.values():
                if (other_schoolyear is not self.event.schoolyear and
                    dr.overlaps(IDateRange(other_schoolyear))):
                    overlapping_schoolyears.append(other_schoolyear)
            if overlapping_schoolyears:
                raise SchoolYearOverlapError(self.event.schoolyear,
                                             overlapping_schoolyears)

# @adapter(TermBeforeChangeEvent)
# @implementer(ISubscriber)
# def termOverlapValidationSubscriber(term, new_dates, old_dates):
#     dr = DateRange(*new_dates)
#     term_container = term.__parent__
#     for other_term in term_container.values():
#         if dr.overlaps(other_term):
#             raise ValueError("WTF OMG!")
