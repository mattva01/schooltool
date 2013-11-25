#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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

import datetime

from zope.component import queryUtility

from schooltool.term.interfaces import IDateManager
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.relationship import RelationshipInfo
from schooltool.relationship.relationship import BoundRelationshipProperty
from schooltool.relationship.relationship import relate, unrelate, share_state
from schooltool.relationship.uri import URIObject

ACTIVE = 'a'
INACTIVE = 'i'
ACTIVE_CODE = 'a'
INACTIVE_CODE = 'i'


class TemporalStateAccessor(object):

    def __init__(self, data):
        self.data = data

    def all(self):
        return [(date, meaning, code)
                for date, (meaning, code) in sorted(self.data.items())]

    def set(self, date, meaning=ACTIVE, code=ACTIVE_CODE):
        self.data[date] = meaning, code

    def get(self, date):
        if not self.data:
            return None
        for sd in sorted(self.data.keys(), reverse=True):
            if sd <= date:
                return self.data[sd]
        return None

    def __contains__(self, date):
        return date in self.data

    def has(self, date=None, states=(), meanings=''):
        if not self.data:
            if meanings == ACTIVE:
                return ACTIVE_CODE in states
            else:
                return False
        if date is not None:
            state = self.get(date)
        else:
            state = self.latest
        if state is None:
            return False
        meaning = state[0]
        code = state[1]
        if states and code not in states:
            return False
        for val in meanings:
            if val in meaning:
                return True
        return False

    @property
    def latest(self):
        if not self.data:
            return ACTIVE, ACTIVE_CODE
        day, state = sorted(self.data.items())[-1]
        return state


_today = object()


class BoundTemporalRelationshipProperty(BoundRelationshipProperty):
    """Temporal relationship property bound to an object."""

    def __init__(self, this, rel_type, my_role, other_role,
                 filter_meanings=ACTIVE, filter_date=_today,
                 filter_codes=()):
        BoundRelationshipProperty.__init__(
            self, this, rel_type, my_role, other_role)
        if filter_date is _today:
            self.filter_date = self.today
        else:
            self.filter_date = filter_date
        self.filter_codes = set(filter_codes)
        self.filter_meanings = filter_meanings
        self.init_filter()

    @property
    def today(self):
        dateman = queryUtility(IDateManager)
        if dateman is not None:
            return dateman.today
        return datetime.date.today()

    def _filter_nothing(self, link):
        return True

    def _filter_latest_meanings(self, link):
        for v in link.state.latest[0]:
            if v in self.filter_meanings:
                return True
        return False

    def _filter_everything(self, link):
        return link.state.has(
            date=self.filter_date, states=self.filter_codes,
            meanings=self.filter_meanings)

    def init_filter(self):
        on_date = self.filter_date
        any_code = self.filter_codes
        is_active = self.filter_meanings
        if not any_code and on_date is None:
            if not is_active:
                self._filter = self._filter_nothing
            else:
                self._filter = self._filter_latest_meanings
        else:
            self._filter = self._filter_everything


    def filter(self, links):
        for link in links:
            if (link.rel_type == self.rel_type and self._filter(link)):
                yield link

    def __iter__(self):
        linkset = IRelationshipLinks(self.this).getLinksByRole(self.other_role)
        for link in self.filter(linkset):
            yield link.target

    @property
    def relationships(self):
        linkset = IRelationshipLinks(self.this).getLinksByRole(self.other_role)
        return [RelationshipInfo(self.this, link)
                for link in self.filter(linkset)]

    def on(self, date):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_meanings=self.filter_meanings,
            filter_date=date,
            filter_codes=self.filter_codes)

    def any(self, meanings=ACTIVE):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_meanings=meanings, filter_date=self.filter_date,
            filter_codes=self.filter_codes)

    def coded(self, *codes):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_meanings=self.filter_meanings, filter_date=self.filter_date,
            filter_codes=codes)

    def all(self):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_meanings='', filter_date=None,
            filter_codes=())

    def relate(self, other, meaning=ACTIVE, code=ACTIVE_CODE):
        links = IRelationshipLinks(self.this)
        try:
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        except ValueError:
            relate(self.rel_type,
                   (self.this, self.my_role),
                   (other, self.other_role))
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        link.state.set(self.filter_date, meaning=meaning, code=code)

    def add(self, other, code=ACTIVE_CODE):
        self.relate(other, meaning=ACTIVE, code=code)

    def remove(self, other, code=INACTIVE_CODE):
        self.relate(other, meaning=INACTIVE, code=code)

    def states(self, other):
        links = IRelationshipLinks(self.this)
        try:
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        except ValueError:
            return None
        return link.state.all()

    def state(self, other):
        links = IRelationshipLinks(self.this)
        try:
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        except ValueError:
            return None
        if self.filter_date is None:
            return link.state.latest
        return link.state.get(self.filter_date)

    def unrelate(self, other):
        unrelate(self.rel_type, (self.this, self.my_role),
                                (other, self.other_role))


class TemporalURIObject(URIObject):

    def access(self, state):
        return TemporalStateAccessor(state)

    def bind(self, instance, my_role, rel_type, other_role):
        return BoundTemporalRelationshipProperty(
            instance, rel_type, my_role, other_role)


def shareTemporalState(event):
    if not isinstance(event.rel_type, TemporalURIObject):
        return
    links = event.getLinks()
    share_state(*links)
