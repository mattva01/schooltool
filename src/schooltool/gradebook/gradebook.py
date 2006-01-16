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
"""Gradebook Implementation

$Id$
"""
__docformat__ = 'reStructuredText'

import zope.component
import zope.interface

from schooltool.gradebook import interfaces
from schooltool import course, requirement

class Gradebook(object):

    zope.interface.implements(interfaces.IGradebook)
    zope.component.adapts(course.interfaces.ISection)

    def __init__(self, context):
        self.context = context
        # Make sure we are not having inherited requirements
        self.activities = []
        for activity in interfaces.IActivities(context).values():
            if isinstance(
                activity, requirement.requirement.InheritedRequirement):
                activity = activity.original
            self.activities.append(activity)

    def _checkStudent(self, student):
        if student not in self.context.members:
            raise ValueError(
                'Student %r is not in this section.' %student.username)

    def _checkActivity(self, activity):
        if activity not in self.activities:
            raise ValueError(
                '%r is not part of this section.' %activity.title)

    def hasEvaluation(self, student, activity):
        """See interfaces.IGradebook"""
        self._checkStudent(student)
        self._checkActivity(activity)
        if activity in requirement.interfaces.IEvaluations(student):
                return True
        return False

    def getEvaluation(self, student, activity):
        """See interfaces.IGradebook"""
        self._checkStudent(student)
        self._checkActivity(activity)
        evaluations = requirement.interfaces.IEvaluations(student)
        return evaluations[activity]

    def evaluate(self, student, activity, score):
        """See interfaces.IGradebook"""
        self._checkStudent(student)
        self._checkActivity(activity)
        # XXX: Determine evaluator
        evaluation = requirement.evaluation.Evaluation(
            activity, activity.scoresystem, score, None)
        evaluations = requirement.interfaces.IEvaluations(student)
        evaluations.addEvaluation(evaluation)

    def removeEvaluation(self, student, activity):
        """See interfaces.IGradebook"""
        self._checkStudent(student)
        self._checkActivity(activity)
        evaluations = requirement.interfaces.IEvaluations(student)
        del evaluations[activity]

    def getEvaluationsForStudent(self, student):
        """See interfaces.IGradebook"""
        self._checkStudent(student)
        evaluations = requirement.interfaces.IEvaluations(student)
        for activity, evaluation in evaluations.items():
            if activity in self.activities:
                yield activity, evaluation

    def getEvaluationsForActivity(self, activity):
        """See interfaces.IGradebook"""
        self._checkActivity(activity)
        for student in self.context.members:
            evaluations = requirement.interfaces.IEvaluations(student)
            if activity in evaluations:
                yield student, evaluations[activity]
