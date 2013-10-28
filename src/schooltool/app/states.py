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


RELATIONSHIP_STATES_APP_KEY = 'schooltool.app.relationships-states'


class RelationshipState(Persistent, Contained):
    implements(IRelationshipState)

    title = None
    active = True

    def __init__(self, title, active, code=None):
        self.title = title
        self.active = active
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

    def __init__(self, title):
        self.title = title
        self.states = OrderedContainer()
        locate(self.states, self, 'states')

    def add(self, title, active, code):
        self.states[code] = RelationshipState(title, active, code=code)


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
        raise NotImplementedError()

    def __call__(self):
        if self.states_name is None:
            raise NotImplementedError()
        container = IRelationshipStateContainer(self.app)
        if self.states_name not in container:
            try:
                container[self.states_name] = RelationshipStates(self.states_title)
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
