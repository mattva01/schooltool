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
"""Requirement Interfaces

$Id$
"""
__docformat__='restructuredtext'

import zope.interface
import zope.schema
import zope.app.container.constraints
import zope.app.container.interfaces


class IRequirement(zope.app.container.interfaces.IContainer):
    '''Something a student can do.'''
    #zope.app.container.constraints.contains(IRequirement)
    #zope.app.container.constraints.containers('.IRequirement')

    title = zope.schema.TextLine(
        title=u'Title',
        description=u'A brief title of the requirement.',
        required=True)

    bases = zope.schema.List(
        title=u'Bases',
        description=u'An enumeration of base requirements.',
        readonly=True)

    def addBase(definition):
        '''Add a group requirement as a base definition.'''

    def removeBase(definition):
        '''Remove a group requirement from the bases.

        This method is responsible for notifying its contained requirements
        about the removal of this requirement.
        '''


class IHaveRequirement(zope.interface.Interface):
    '''Marker interface for objects having requirements'''


class IScoreSystem(zope.interface.Interface):
    '''A Score System'''

    title = zope.schema.TextLine(
        title=u'Title',
        description=u'A brief title of the score system.',
        required=True)

    description = zope.schema.TextLine(
        title=u'Description',
        description=u'A brief description of the score system.',
        required=True)

    def isPassingScore(score):
        '''Return whether score meets a passing threshold.

        The return value is a boolean.
        '''

    def isValidScore(score):
        '''Return whether score is a valid score.

        The return value is a boolean.  The ``UNSCORED`` value is a valid score.
        '''


class IHaveEvaluations(zope.interface.Interface):
    '''A marker interface for objects that can have evaluations'''


class IEvaluation(zope.app.container.interfaces.IContained):
    '''An Evaluation'''
    zope.app.container.constraints.containers(".IEvaluations")

    scoreSystem = zope.schema.Object(
        title=u'Score System',
        description=u'The score system used for grading.',
        schema=IScoreSystem)

    requirement = zope.schema.Object(
        title=u'Requirement',
        description=u'The requirement being evaluated.',
        schema=IRequirement)

    value = zope.interface.Attribute(
        'The value of the grade')

    time = zope.schema.Datetime(
        title=u'Time',
        description=u'The time the evaluation was made')

    evaluator = zope.interface.Attribute(
        'The entity doing the evaluation')


class IEvaluations(zope.app.container.interfaces.IContainer):
    '''An Evaluation Container'''
    zope.app.container.constraints.contains(IEvaluation)

    def __init__(self, items=None):
        '''Initialize object.

        The items should be a list of tuples or dictionary of evaluation names
        and objects.
        '''

    def getEvaluationsForRequirement(requirement, recursive=True):
        '''Match all evaluations that satisfy the requirement.

        The return value is another ``IEvaluations`` object.  This allows for
        chained queries.  For recursive queries, evaluations for all sub
        requirements will be returned as well.
        '''

    def getEvaluationsOfEvaluator(evaluator):
        '''Match all evaluations done by the specified evaluator.

        The return value is another ``IEvaluations`` object.  This allows for
        chained queries.  For recursive queries, evaluations for all sub
        requirements will be returned as well.
        '''


class IEvaluationsQuery(zope.interface.Interface):
    '''Evaluation Query

    These objects query evaluations and return another evaluations object.
    '''

    def __call__(self, *args, **kwargs):
        '''Execute the query and return an ``IEvaluations`` object.

        The returned ``IEvaluations`` object *must* have the same parent and
        name that the original ``IEvaluations`` object had.
        '''
