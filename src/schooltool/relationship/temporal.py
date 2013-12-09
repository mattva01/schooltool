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
from schooltool.relationship.relationship import BoundRelationshipProperty
from schooltool.relationship.relationship import relate, unrelate
from schooltool.relationship.relationship import RelationshipInfo
from schooltool.relationship.uri import URIObject

ACTIVE = 'a'
INACTIVE = 'i'
ACTIVE_CODE = 'a'
INACTIVE_CODE = 'i'


class TemporalStateAccessor(object):

    def __init__(self, state):
        self.state = state
        if 'tmp' not in state:
            state['tmp'] = ()

    def all(self):
        all = self.state['tmp']
        return [(date, meaning, code)
                for date, (meaning, code) in reversed(all)]

    def set(self, date, meaning=ACTIVE, code=ACTIVE_CODE):
        data = dict(self.state['tmp'])
        data[date] = meaning, code
        self.state['tmp'] = tuple(reversed(data.items()))

    def get(self, date):
        data = self.state['tmp']
        if not data:
            return ACTIVE, ACTIVE_CODE
        for sd, result in data:
            if sd <= date:
                return result
        return None

    def has(self, date=None, states=(), meanings=''):
        if not self.state['tmp']:
            if meanings == ACTIVE:
                return (ACTIVE_CODE in states or
                        not states)
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
        if not meanings:
            return True
        for val in meanings:
            if val in meaning:
                return True
        return False

    @property
    def latest(self):
        data = self.state['tmp']
        if not data:
            return ACTIVE, ACTIVE_CODE
        day, state = data[0]
        return state

    @property
    def today(self):
        dateman = queryUtility(IDateManager)
        if dateman is not None:
            today = dateman.today
        else:
            today = datetime.date.today()
        return self.get(today)


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
        return link.rel_type_hash == hash(self.rel_type)

    def _filter_latest_meanings(self, link):
        if link.rel_type_hash != hash(self.rel_type):
            return False
        for v in link.state.latest[0]:
            if v in self.filter_meanings:
                return True
        return False

    def _filter_everything(self, link):
        if link.rel_type_hash != hash(self.rel_type):
            return False
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
            if (link.rel_type_hash == hash(self.rel_type) and self._filter(link)):
                yield link

    def __contains__(self, other):
        if other is None:
            return False
        linkset = IRelationshipLinks(self.this)
        for link in linkset.getCachedLinksByTarget(other):
            if (link.rel_type_hash == hash(self.rel_type) and
                link.my_role_hash == hash(self.my_role) and
                link.role_hash == hash(self.other_role) and
                self._filter(link)):
                return True
        return False

    def __iter__(self):
        links = IRelationshipLinks(self.this).getCachedLinksByRole(self.other_role)
        for link in links:
            if self._filter(link):
                yield link.target

    @property
    def relationships(self):
        links = IRelationshipLinks(self.this).getCachedLinksByRole(self.other_role)
        for link in links:
            if self._filter(link):
                yield RelationshipInfo(self.this, link)

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

    def state(self, other):
        links = IRelationshipLinks(self.this)
        try:
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        except ValueError:
            return None
        return link.state

    def unrelate(self, other):
        unrelate(self.rel_type, (self.this, self.my_role),
                                (other, self.other_role))


class TemporalURIObject(URIObject):

    def access(self, state):
        return TemporalStateAccessor(state)

    def bind(self, instance, my_role, rel_type, other_role):
        return BoundTemporalRelationshipProperty(
            instance, rel_type, my_role, other_role)

    @property
    def filter(self):
        dateman = queryUtility(IDateManager)
        if dateman is not None:
            today = dateman.today
        else:
            today = datetime.date.today()
        def filter(link):
            if link.rel_type_hash != hash(self):
                return False
            state = self.access(link.shared_state)
            return state.has(date=today, meanings=ACTIVE)
        return filter


def shareTemporalState(event):
    if not isinstance(event.rel_type, TemporalURIObject):
        return
    event.shared['tmp'] = ()
