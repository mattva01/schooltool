
import datetime

from zope.component import queryUtility

from schooltool.term.interfaces import IDateManager
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.relationship import RelationshipInfo
from schooltool.relationship.relationship import BoundRelationshipProperty
from schooltool.relationship.relationship import relate, unrelate
from schooltool.relationship.uri import URIObject

RELATIONSHIP_ACTIVE = 'a'
RELATIONSHIP_INACTIVE = 'i'


class TemporalStateAccessor(object):

    def __init__(self, data):
        self.data = data

    def all(self):
        return [(date, active, code)
                for date, (active, code) in sorted(self.data.items())]

    def set(self, date, active=True, code=RELATIONSHIP_ACTIVE):
        self.data[date] = active, code

    def get(self, date):
        if not self.data:
            return None
        for sd in sorted(self.data.keys(), reverse=True):
            if sd <= date:
                return self.data[sd]
        return None

    def __contains__(self, date):
        return date in self.data

    def has(self, date, states):
        if not self.data:
            return RELATIONSHIP_ACTIVE in states
        state = self.get(date)
        if state is None:
            return False
        code = state[1]
        return code in states

    @property
    def latest(self):
        if not self.data:
            return True, RELATIONSHIP_ACTIVE
        day, state = sorted(self.data.items())[-1]
        return state


_today = object()

class BoundTemporalRelationshipProperty(BoundRelationshipProperty):
    """Temporal relationship property bound to an object."""

    def __init__(self, this, rel_type, my_role, other_role,
                 filter_date=_today, filter_codes=(RELATIONSHIP_ACTIVE,)):
        BoundRelationshipProperty.__init__(
            self, this, rel_type, my_role, other_role)
        if filter_date is _today:
            self.filter_date = self.today
        else:
            self.filter_date = filter_date
        self.filter_codes = set(filter_codes)

    @property
    def today(self):
        dateman = queryUtility(IDateManager)
        if dateman is not None:
            return dateman.today
        return datetime.date.today()

    def filter(self, links):
        on_date = self.filter_date
        any_code = self.filter_codes
        if not any_code and on_date is None:
            filter = lambda link: True
        elif on_date is None:
            filter = lambda link: link.state.latest[1] in any_code
        else:
            filter = lambda link: link.state.has(on_date, any_code)
        for link in links:
            if (link.rel_type == self.rel_type and filter(link)):
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
            filter_date=date, filter_codes=self.filter_codes)

    def any(self):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_date=None, filter_codes=())

    def all(self, *codes):
        return self.__class__(
            self.this, self.rel_type, self.my_role, self.other_role,
            filter_date=self.filter_date, filter_codes=self.filter_codes)

    def relate(self, other, active=True, code=RELATIONSHIP_ACTIVE):
        links = IRelationshipLinks(self.this)
        try:
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        except ValueError:
            relate(self.rel_type,
                   (self.this, self.my_role),
                   (other, self.other_role))
            link = links.find(self.my_role, other, self.other_role, self.rel_type)
        link.state.set(self.filter_date, active=active, code=code)

    def add(self, other, code=RELATIONSHIP_ACTIVE):
        self.relate(other, active=True, code=code)

    def remove(self, other, code=RELATIONSHIP_INACTIVE):
        self.relate(other, active=False, code=code)

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
