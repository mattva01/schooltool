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
import persistent.dict

from decimal import Decimal

import zope.component
import zope.interface
from zope.security import proxy
from zope import annotation
from zope.app.keyreference.interfaces import IKeyReference

from schooltool import course, requirement
from schooltool.traverser import traverser
from schooltool.app.app import InitBase
from schooltool.securitypolicy.crowds import ConfigurableCrowd
from schooltool.securitypolicy.crowds import AggregateCrowd
from schooltool.securitypolicy.crowds import ManagersCrowd
from schooltool.securitypolicy.crowds import ClerksCrowd
from schooltool.securitypolicy.crowds import AdministratorsCrowd

from schooltool.gradebook import interfaces
from schooltool.gradebook.category import getCategories
from schooltool.common import SchoolToolMessage as _

GRADEBOOK_SORTING_KEY = 'schooltool.gradebook.sorting'
CURRENT_WORKSHEET_KEY = 'schooltool.gradebook.currentworksheet'


class GradebookBase(object):
    def __init__(self, context):
        self.context = context
        # To make URL creation happy
        self.__parent__ = context
        # Establish worksheets and all activities
        self.worksheets = list(interfaces.IActivities(context).values())
        self.activities = []
        for worksheet in self.worksheets:
            for activity in worksheet.values():
                self.activities.append(activity)
        self.students = list(self.context.members)

    def _checkStudent(self, student):
        if student not in self.students:
            raise ValueError(
                'Student %r is not in this section.' %student.username)
        # Remove security proxy, so that the object can be referenced and
        # adapters are not proxied. Note that the gradebook itself has
        # sufficient tight security.
        return proxy.removeSecurityProxy(student)

    def _checkActivity(self, activity):
        # Remove security proxy, so that the object can be referenced and
        # adapters are not proxied. Note that the gradebook itself has
        # sufficient tight security.
        if activity in self.activities:
            return proxy.removeSecurityProxy(activity)
        raise ValueError(
            '%r is not part of this section.' %activity.title)

    def hasEvaluation(self, student, activity):
        """See interfaces.IGradebook"""
        student = self._checkStudent(student)
        activity = self._checkActivity(activity)
        if activity in requirement.interfaces.IEvaluations(student):
            return True
        return False

    def getEvaluation(self, student, activity, default=None):
        """See interfaces.IGradebook"""
        student = self._checkStudent(student)
        activity = self._checkActivity(activity)
        evaluations = requirement.interfaces.IEvaluations(student)
        return evaluations.get(activity, default)

    def evaluate(self, student, activity, score, evaluator=None):
        """See interfaces.IGradebook"""
        student = self._checkStudent(student)
        activity = self._checkActivity(activity)
        evaluation = requirement.evaluation.Evaluation(
            activity, activity.scoresystem, score, evaluator)
        evaluations = requirement.interfaces.IEvaluations(student)
        evaluations.addEvaluation(evaluation)

    def removeEvaluation(self, student, activity):
        """See interfaces.IGradebook"""
        student = self._checkStudent(student)
        activity = self._checkActivity(activity)
        evaluations = requirement.interfaces.IEvaluations(student)
        del evaluations[activity]

    def getCurrentWorksheet(self, person):
        person = proxy.removeSecurityProxy(person)
        ann = annotation.interfaces.IAnnotations(person)
        if CURRENT_WORKSHEET_KEY not in ann:
            ann[CURRENT_WORKSHEET_KEY] = persistent.dict.PersistentDict()
        if self.worksheets:
            default = self.worksheets[0]
        else:
            default = None
        section_id = hash(IKeyReference(self.context))
        return ann[CURRENT_WORKSHEET_KEY].get(section_id, default)

    def setCurrentWorksheet(self, person, worksheet):
        person = proxy.removeSecurityProxy(person)
        worksheet = proxy.removeSecurityProxy(worksheet)
        ann = annotation.interfaces.IAnnotations(person)
        if CURRENT_WORKSHEET_KEY not in ann:
            ann[CURRENT_WORKSHEET_KEY] = persistent.dict.PersistentDict()
        section_id = hash(IKeyReference(self.context))
        ann[CURRENT_WORKSHEET_KEY][section_id] = worksheet

    def getCurrentActivities(self, person):
        worksheet = self.getCurrentWorksheet(person)
        if worksheet:
            return list(worksheet.values())
        else:
            return []

    def getCurrentEvaluationsForStudent(self, person, student):
        """See interfaces.IGradebook"""
        self._checkStudent(student)
        evaluations = requirement.interfaces.IEvaluations(student)
        activities = self.getCurrentActivities(person)
        for activity, evaluation in evaluations.items():
            if activity in activities:
                yield activity, evaluation

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

    def getTotalScoreForStudent(self, student):
        """See interfaces.IGradebook"""
        fractions = [
            evaluation.scoreSystem.getFractionalValue(evaluation.value)
            for activity, evaluation in self.getEvaluationsForStudent(student)]
        return sum(fractions) / Decimal(len(fractions)) * Decimal(100)

    def getSortKey(self, person):
        person = proxy.removeSecurityProxy(person)
        ann = annotation.interfaces.IAnnotations(person)
        if GRADEBOOK_SORTING_KEY not in ann:
            ann[GRADEBOOK_SORTING_KEY] = persistent.dict.PersistentDict()
        section_id = hash(IKeyReference(self.context))
        return ann[GRADEBOOK_SORTING_KEY].get(section_id, ('student', False))

    def setSortKey(self, person, value):
        person = proxy.removeSecurityProxy(person)
        ann = annotation.interfaces.IAnnotations(person)
        if GRADEBOOK_SORTING_KEY not in ann:
            ann[GRADEBOOK_SORTING_KEY] = persistent.dict.PersistentDict()
        section_id = hash(IKeyReference(self.context))
        ann[GRADEBOOK_SORTING_KEY][section_id] = value


class Gradebook(GradebookBase):
    zope.interface.implements(interfaces.IGradebook)
    zope.component.adapts(course.interfaces.ISection)

    def __init__(self, context):
        super(Gradebook, self).__init__(context)
        # To make URL creation happy
        self.__name__ = 'gradebook'


class MyGrades(GradebookBase):
    zope.interface.implements(interfaces.IMyGrades)
    zope.component.adapts(course.interfaces.ISection)

    def __init__(self, context):
        super(MyGrades, self).__init__(context)
        # To make URL creation happy
        self.__name__ = 'mygrades'


# HTTP pluggable traverser plugins
GradebookTraverserPlugin = traverser.AdapterTraverserPlugin(
    'gradebook', interfaces.IGradebook)

MyGradesTraverserPlugin = traverser.AdapterTraverserPlugin(
    'mygrades', interfaces.IMyGrades)


def getGradebookSection(gradebook):
    """Adapt IGradebook to ISection."""
    return course.interfaces.ISection(gradebook.context)


class GradebookEditorsCrowd(AggregateCrowd, ConfigurableCrowd):
    setting_key = 'administration_can_grade_students'

    def crowdFactories(self):
        return [ManagersCrowd, AdministratorsCrowd, ClerksCrowd]

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        return (ConfigurableCrowd.contains(self, principal) and
                AggregateCrowd.contains(self, principal))


class GradebookInit(InitBase):
    def __call__(self):
        from schooltool.app.interfaces import ISchoolToolApplication
        dict = getCategories(self.app)
        dict.addValue('assignment', 'en', _('Assignment'))
        dict.addValue('essay', 'en', _('Essay'))
        dict.addValue('exam', 'en', _('Exam'))
        dict.addValue('homework', 'en', _('Homework'))
        dict.addValue('journal', 'en', _('Journal'))
        dict.addValue('lab', 'en', _('Lab'))
        dict.addValue('presentation', 'en', _('Presentation'))
        dict.addValue('project', 'en', _('Project'))
        dict.setDefaultLanguage('en')
        dict.setDefaultKey('assignment')

