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
Level-related Tests

$Id$
"""

__docformat__ = 'restructuredtext'

import datetime
import persistent
from BTrees.OOBTree import OOBTree

import zope.component
import zope.event
from zope.app import annotation
from zope.app import container
from zope.app import zapi
from zope.app.location import location
from zope.app.keyreference.interfaces import IKeyReference

from schooltool.requirement import interfaces


EVALUATIONS_KEY = "schooltool.evaluations"


def getRequirementList(req, recurse=True):
    result = []
    for value in req.values(): # loop through your children
        if recurse:
            result += getRequirementList(value) # append their children...
        else:
            result.append(value) # just append the child
    result.append(req) # append the object itself
    return result


class Evaluations(persistent.Persistent, container.contained.Contained):
    """Evaluations mapping.

    This particular implementation uses the ``zope.app.keyreference`` package
    to generate the keys of the requirements. Any key that is passed in could
    be the requirement or the ``IKeyReference`` of the requirement. This
    implementation will always convert the key to provide ``IKeyReference``
    before treating it as a true key.

    Another feature of this implementation is that if you set an evaluation
    for a requirement that has already an evaluation, then the old evaluation
    is simply overridden. The ``IContainer`` interface would raise a duplicate
    name error.
    """
    zope.interface.implements(interfaces.IEvaluations)

    def __init__(self, items=None):
        super(Evaluations, self).__init__()
        self._btree = OOBTree()
        for name, value in items or []:
            self[name] = value

    def __getitem__(self, key):
        """See zope.interface.common.mapping.IItemMapping"""
        return self._btree[IKeyReference(key)]

    def __delitem__(self, key):
        """See zope.interface.common.mapping.IWriteMapping"""
        value = self[key]
        del self._btree[IKeyReference(key)]
        event = container.contained.ObjectRemovedEvent(value, self)
        zope.event.notify(event)

    def __setitem__(self, key, value):
        """See zope.interface.common.mapping.IWriteMapping"""
        self._btree[IKeyReference(key)] = value
        value, event = container.contained.containedEvent(value, self)
        zope.event.notify(event)

    def get(self, key, default=None):
        """See zope.interface.common.mapping.IReadMapping"""
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        """See zope.interface.common.mapping.IReadMapping"""
        return IKeyReference(key) in self._btree

    def keys(self):
        """See zope.interface.common.mapping.IEnumerableMapping"""
        # For now I decided to return the activities (as I think it is more
        # natural), though they are not the true keys as we know
        return [key() for key in self._btree.keys()]

    def __iter__(self):
        """See zope.interface.common.mapping.IEnumerableMapping"""
        return iter(self.keys())

    def values(self):
        """See zope.interface.common.mapping.IEnumerableMapping"""
        return self._btree.values()

    def items(self):
        """See zope.interface.common.mapping.IEnumerableMapping"""
        return [(key(), value) for key, value in self._btree.items()]

    def __len__(self):
        """See zope.interface.common.mapping.IEnumerableMapping"""
        return len(self._btree)

    def addEvaluation(self, evaluation):
        """See interfaces.IEvaluations"""
        self[evaluation.requirement] = evaluation

    def getEvaluationsForRequirement(self, req, recurse=True):
        """See interfaces.IEvaluations"""
        requirements = getRequirementList(req, recurse)
        result = [(name, ev)
                  for name, ev in self.items()
                  if ev.requirement in requirements]
        result = Evaluations(result)
        location.locate(result, zapi.getParent(self), zapi.name(self))
        return result

    def getEvaluationsOfEvaluator(self, evaluator):
        """See interfaces.IEvaluations"""
        result = [(name, ev)
                  for name, ev in self.items()
                  if ev.evaluator == evaluator]
        result = Evaluations(result)
        location.locate(result, zapi.getParent(self), zapi.name(self))
        return result

    def __repr__(self):
        try:
            parent = zapi.getParent(self)
        except TypeError:
            parent = None
        return '<%s for %r>' % (self.__class__.__name__, parent)


class Evaluation(container.contained.Contained):

    zope.interface.implements(interfaces.IEvaluation)

    def __init__(self, requirement, scoreSystem, value, evaluator):
        self._value = None
        self.requirement = requirement
        self.scoreSystem = scoreSystem
        self.value = value
        self.evaluator = evaluator

    @apply
    def value():
        def get(self):
            return self._value

        def set(self, value):
            if not self.scoreSystem.isValidScore(value):
                raise ValueError('%r is not a valid score.' %value)
            self._value = value
            # XXX mg: since it is a very bad idea to mix datetimes with tzinfo
            # and datetimes without tzinfo, I suggest using datetimes with
            # tzinfo everywhere.  Most of SchoolTool follows this convention,
            # (with the painful exception of schooltool.timetable).
            self.time = datetime.datetime.utcnow()

        return property(get, set)

    @property
    def evaluatee(self):
        try:
            return zapi.getParent(zapi.getParent(self))
        except TypeError:
            raise ValueError('Evaluation is not yet assigned to a evaluatee')

    def __repr__(self):
        return '<%s for %r, value=%r>' % (self.__class__.__name__,
                                          self.requirement, self.value)


class AbstractQueryAdapter(object):

    zope.component.adapts(interfaces.IEvaluations)
    zope.interface.implements(interfaces.IEvaluationsQuery)

    def __init__(self, context):
        self.context = context

    def _query(self, *args, **kwargs):
        raise NotImplemented

    def __call__(self, *args, **kwargs):
        """See interfaces.IEvaluationsQuery"""
        result = Evaluations(self._query(*args, **kwargs))
        location.locate(
            result, zapi.getParent(self.context), zapi.name(self.context))
        return result


def getEvaluations(context):
    """Adapt an ``IHaveEvaluations`` object to ``IEvaluations``."""
    annotations = annotation.interfaces.IAnnotations(context)
    try:
        return annotations[EVALUATIONS_KEY]
    except KeyError:
        evaluations = Evaluations()
        annotations[EVALUATIONS_KEY] = evaluations
        location.locate(evaluations, zope.proxy.removeAllProxies(context),
                        '++evaluations++')
        return evaluations
# Convention to make adapter introspectable
getEvaluations.factory = Evaluations

