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

from persistent import Persistent
from zope.component import queryUtility
from zope.container.contained import Contained
from zope.event import notify
from zope.interface import implementer
from zope.interface import Interface

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

    def __iter__(self):
        all = self.state['tmp']
        for date, (meaning, code) in reversed(all):
            yield date, meaning, code

    def __delitem__(self, date):
        data = dict(self.state['tmp'])
        del data[date]
        self.state['tmp'] = tuple(sorted(data.items(), reverse=True))

    def all(self):
        return list(self)

    def set(self, date, meaning=ACTIVE, code=ACTIVE_CODE):
        meaning = ''.join(sorted(set(meaning)))
        data = dict(self.state['tmp'])
        data[date] = meaning, code
        self.state['tmp'] = tuple(sorted(data.items(), reverse=True))

    def replace(self, states):
        data = dict(states)
        self.state['tmp'] = tuple(sorted(data.items(), reverse=True))

    def closest(self, date):
        data = self.state['tmp']
        if not data:
            return ACTIVE, ACTIVE_CODE
        for sd, result in data:
            if sd <= date:
                return sd
        return None

    def get(self, date):
        data = self.state['tmp']
        if not data:
            return ACTIVE, ACTIVE_CODE
        for sd, result in data:
            if sd <= date:
                return result
        return None

    def has(self, date=None, states=(), meanings=()):
        if not self.state['tmp']:
            if ACTIVE in meanings:
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


class ILinkStateModifiedEvent(Interface):

    pass


@implementer(ILinkStateModifiedEvent)
class LinkStateModifiedEvent(object):

    def __init__(self, link, this, other, date, meaning, code):
        self.link = link
        self.this = this
        self.other = other
        self.date = date
        self.meaning = meaning
        self.code = code


class BoundTemporalRelationshipProperty(BoundRelationshipProperty):
    """Temporal relationship property bound to an object."""

    def __init__(self, this, rel_type, my_role, other_role,
                 filter_meanings=(ACTIVE,), filter_date=_today,
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
        for meaning in link.state.latest[0]:
            for val in self.filter_meanings:
                if val in meaning:
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

    def _iter_filtered_links(self):
        links = IRelationshipLinks(self.this).getCachedLinksByRole(self.other_role)
        for link in links:
            if self._filter(link):
                yield link

    def __nonzero__(self):
        for link in self._iter_filtered_links():
            return True
        return False

    def __len__(self):
        n = 0
        for link in self._iter_filtered_links():
            n += 1
        return n

    def __iter__(self):
        for link in self._iter_filtered_links():
            if self._filter(link):
                yield link.target

    @property
    def relationships(self):
        for link in self._iter_filtered_links():
            yield RelationshipInfo(self.this, link)

    def on(self, date):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_meanings=self.filter_meanings,
            filter_date=date,
            filter_codes=self.filter_codes)

    def any(self, *args, **kw):
        meanings = tuple(
            [''.join(sorted(set(meaning))) for meaning in args] +
            [''.join(sorted(set(meaning))) for meaning in kw.values()]
            )
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
            filter_meanings=(), filter_date=None,
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
        notify(LinkStateModifiedEvent(
                link, self.this, other, self.filter_date, meaning, code))

    def unrelate(self, other):
        """Delete state on filtered date or unrelate completely if
        no states left or filtered date is .all()
        """
        links = IRelationshipLinks(self.this)
        link = links.find(self.my_role, other, self.other_role, self.rel_type)
        if self.filter_date is None:
            unrelate(self.rel_type,
                     (self.this, self.my_role),
                     (other, self.other_role))
            return
        state = link.state
        date = state.closest(self.filter_date)
        if date is None:
            raise KeyError(self.filter_date)
        del state[date]
        try:
            iter(state).next()
        except StopIteration:
            unrelate(self.rel_type,
                     (self.this, self.my_role),
                     (other, self.other_role))

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


class TemporalURIObject(URIObject):

    def persist(self):
        return PersistentTemporalURIObject(
            self, self._uri, name=self._name, description=self._description)

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
            return state.has(date=today, meanings=(ACTIVE,))
        return filter


class PersistentTemporalURIObject(Persistent, Contained, TemporalURIObject):

    __name__ = None
    __parent__ = None


def shareTemporalState(event):
    if not isinstance(event.rel_type, TemporalURIObject):
        return
    if 'tmp' not in event.shared:
        event.shared['tmp'] = ()
