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
__docformat__='restructuredtext'

import datetime
import zope.component
from zope.app import container
from zope.app import zapi
from zope.app.location import location
from zope.app import annotation
from schooltool.requirement import interfaces

EVALUATIONS_KEY = "schooltool.evaluations"

def getRequirementList(req, recurse=True):
    result = []
    if interfaces.IGroupRequirement.providedBy(req):
        for value in req.values():
            if recurse:
                result += getRequirementList(value)
            else:
                result.append(value)
    else:
        result.append(req)
    return result

class Evaluations(container.btree.BTreeContainer,
                  container.contained.Contained):
    zope.interface.implements(interfaces.IEvaluations)

    def __init__(self, items=None):
        super(Evaluations, self).__init__()
        for name, value in items or []:
            self[name] = value

    def addEvaluation(self, ev):
        '''See interfaces.IEvaluations'''
        chooser = container.interfaces.INameChooser(self)
        name = chooser.chooseName('eval', ev)
        self[name] = ev
        return name

    def getEvaluationsForRequirement(self, req, recurse=True):
        '''See interfaces.IEvaluations'''
        requirements = getRequirementList(req, recurse)
        result = [(name, ev)
                  for name, ev in self.items()
                  if ev.requirement in requirements]
        result = Evaluations(result)
        location.locate(result, zapi.getParent(self), zapi.name(self))
        return result

    def getEvaluationsOfEvaluator(self, evaluator):
        '''See interfaces.IEvaluations'''
        result = [(name, ev)
                  for name, ev in self.items()
                  if ev.evaluator == evaluator]
        result = Evaluations(result)
        location.locate(result, zapi.getParent(self), zapi.name(self))
        return result

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, zapi.getParent(self))


class Evaluation(container.contained.Contained):
    zope.interface.implements(interfaces.IEvaluations)

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
            self._value = value
            self.time = datetime.datetime.utcnow()

        return property(get, set)

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
        '''See interfaces.IEvaluationsQuery'''
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