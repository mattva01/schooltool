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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Relationship states
"""
from persistent import Persistent

import zope.schema.vocabulary
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer
from zope.container.ordered import OrderedContainer
from zope.interface import implements, implementer, implementsOnly
from zope.interface import Interface
from zope.component import adapts, adapter
from zope.location.location import locate

import z3c.form.term
import z3c.form.widget
import z3c.form.interfaces
from z3c.form.browser.select import SelectWidget

from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.interfaces import IRelationshipState
from schooltool.app.interfaces import IRelationshipStateChoice
from schooltool.app.interfaces import IRelationshipStates
from schooltool.app.interfaces import IRelationshipStateContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.temporal import ACTIVE, INACTIVE

from schooltool.common import SchoolToolMessage as _


RELATIONSHIP_STATES_APP_KEY = 'schooltool.app.relationships-states'


class RelationshipState(Persistent, Contained):
    implements(IRelationshipState)

    title = None
    active = ACTIVE

    def __init__(self, title, active, code=None):
        self.title = title
        self.active = ''.join(sorted(set(active)))
        self.__name__ = code

    @property
    def code(self):
        return self.__name__

    @code.setter
    def code(self, name):
        if name == self.__name__:
            return
        container = self.__parent__
        if container is None:
            return
        del container[self.__name__]
        container[name] = self


class RelationshipStates(Persistent, Contained):
    implements(IRelationshipStates)

    title = None
    states = None
    system_titles = None
    factory = RelationshipState

    def __init__(self, title):
        self.title = title
        self.states = OrderedContainer()
        locate(self.states, self, 'states')
        self.system_titles = OrderedContainer()
        locate(self.system_titles, self, 'system_titles')

    def __iter__(self):
        return iter(self.states.values())

    def getState(self, state_tuple):
        if state_tuple is None:
            return None
        meaning, code = state_tuple
        state = self.states.get(code)
        return state

    def getTitle(self, state_tuple):
        state = self.getState(state_tuple)
        if state is None:
            return None
        return state.title

    def getDescription(self, state_tuple):
        if state_tuple is None:
            return None
        meaning, code = state_tuple
        state = self.system_titles.get(meaning)
        return state

    @classmethod
    def overlap(cls, codes, other):
        for code in codes:
            if code in other:
                return True
        return False

    def add(self, *args, **kw):
        state = self.factory(*args, **kw)
        self.states[state.code] = state

    def describe(self, active, title):
        active = ''.join(sorted(set(active)))
        self.system_titles[active] = title


class RelationshipStateContainer(BTreeContainer):
    implements(IRelationshipStateContainer)


class VivifyStateContainer(object):

    def __call__(self):
        if RELATIONSHIP_STATES_APP_KEY not in self.app:
            self.app[RELATIONSHIP_STATES_APP_KEY] = RelationshipStateContainer()


class StateInit(VivifyStateContainer, InitBase):
    pass


class StateStartUp(VivifyStateContainer, StartUpBase):
    pass


class StateStartUpBase(StartUpBase):

    after = ('schooltool.app.states', )
    states_name = None
    states_title = u''

    def populate(self, states):
        states.describe(ACTIVE, _('Active'))
        states.describe(INACTIVE, _('Inactive'))

    def create(self, title):
        return RelationshipStates(title)

    def __call__(self):
        if self.states_name is None:
            raise NotImplementedError()
        container = IRelationshipStateContainer(self.app)
        if self.states_name not in container:
            try:
                container[self.states_name] = self.create(self.states_title)
                self.populate(container[self.states_name])
            except Exception, e:
                try:
                    del container[self.states_name]
                except Exception:
                    pass
                raise e


@adapter(ISchoolToolApplication)
@implementer(IRelationshipStateContainer)
def getStateContainer(app):
    return app[RELATIONSHIP_STATES_APP_KEY]


class RelationshipStateTerms(z3c.form.term.Terms):

    adapts(Interface, z3c.form.interfaces.IFormLayer, Interface,
           IRelationshipStateChoice, z3c.form.interfaces.IWidget)
    implementsOnly(z3c.form.interfaces.ITerms)

    def __init__(self, context, request, form, field, widget):
        self.context = context
        self.request = request
        self.form = form
        self.field = field
        self.widget = widget
        self.terms = self.getVocabulary()

    def getVocabulary(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        relationships = container.get(self.field.source)
        terms = [
            zope.schema.vocabulary.SimpleTerm(
                state, token=state.__name__, title=state.title)
            for state in relationships.states.values()]
        vocabulary = zope.schema.vocabulary.SimpleVocabulary(terms)
        return vocabulary


class RelationshipStateChoice(zope.schema.Field):
    implements(IRelationshipStateChoice)

    source = None

    def __init__(self, source=None, **kw):
        self.source = source
        zope.schema.Field.__init__(self, **kw)


@adapter(IRelationshipStateChoice, z3c.form.interfaces.IFormLayer)
@implementer(z3c.form.interfaces.IFieldWidget)
def RelationshipStateFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, SelectWidget(request))


class GroupMembershipStatesStartup(StateStartUpBase):

    states_name = 'group-membership'
    states_title = _('Group Membership')

    def populate(self, states):
        super(GroupMembershipStatesStartup, self).populate(states)
        states.add(_('Pending'), INACTIVE, 'i')
        states.add(_('Member'), ACTIVE, 'a')
        states.add(_('Suspended'), INACTIVE, 's')
        states.add(_('Removed'), INACTIVE, 'r')
        states.add(_('Added in error'), INACTIVE, 'e')


GRADUATED = 'c'
PREENROLLED = 'p'


class StudentMembershipStatesStartup(StateStartUpBase):

    states_name = 'student-enrollment'
    states_title = _('Student Enrollment')

    def populate(self, states):
        super(StudentMembershipStatesStartup, self).populate(states)
        states.add(_('Pending'), INACTIVE, 'i')
        states.add(_('Pre-enrolled'), INACTIVE+PREENROLLED, 'p')
        states.add(_('Enrolled'), ACTIVE, 'a')
        states.add(_('Graduated/Active'), ACTIVE+GRADUATED, 'c')
        states.add(_('Graduated/Inactive'), INACTIVE+GRADUATED, 'r')
        states.add(_('Withdrawn'), INACTIVE, 'w')
        states.add(_('Added in error'), INACTIVE, 'e')
        states.describe(INACTIVE+PREENROLLED, _('Pre-enrolled'))
        states.describe(ACTIVE+GRADUATED, _('Graduated/Active'))
        states.describe(INACTIVE+GRADUATED, _('Graduated/Inactive'))


class LeadershipStatesStartUp(StateStartUpBase):

    states_name = 'asset-leaders'
    states_title = _('Leaders')

    def populate(self, states):
        super(LeadershipStatesStartUp, self).populate(states)
        states.add(_('Active'), ACTIVE, 'a')
        states.add(_('Inactive'), INACTIVE, 'i')
        states.add(_('Added in error'), INACTIVE, 'e')


class StudentLevelsStatesStartup(StateStartUpBase):

    states_name = 'student-levels'
    states_title = _('Student Levels')

    def populate(self, states):
        super(StudentLevelsStatesStartup, self).populate(states)
        states.add(_('Pre-enrolled'), INACTIVE+PREENROLLED, 'p')
        states.add(_('Enrolled'), ACTIVE, 'a')
        states.add(_('Graduated'), INACTIVE+GRADUATED, 'c')
        states.add(_('Inactive'), INACTIVE, 'i')
        states.add(_('Added in error'), INACTIVE, 'e')
        states.describe(INACTIVE+PREENROLLED, _('Pre-enrolled'))
        states.describe(INACTIVE+GRADUATED, _('Graduated'))
