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
"""Gradebook Views

$Id$
"""
__docformat__ = 'reStructuredText'
from zope.security import proxy
from zope.app import zapi
from zope.app.keyreference.interfaces import IKeyReference

from schooltool.app import app

class GradebookOverview(object):
    """Gradebook Overview/Table"""

    def activities(self):
        result = [
            {'title': activity.title,
             'max':activity.scoresystem.getBestScore(),
             'hash': IKeyReference(activity).__hash__()}
            for activity in self.context.activities]
        return sorted(result, key=lambda x: x['title'])

    def table(self):
        activities = sorted(self.context.activities,
                            key=lambda x: x.title)
        activities = [(IKeyReference(activity).__hash__(), activity)
                      for activity in activities]
        gradebook = proxy.removeSecurityProxy(self.context)
        for student in self.context.students:
            grades = []
            for hash, activity in activities:
                ev = gradebook.getEvaluation(student, activity)
                if ev is not None:
                    grades.append({'activity': hash, 'value': ev.value})
                else:
                    grades.append({'activity': hash, 'value': '-'})

            yield {'student': {'title': student.title, 'id': student.username},
                   'grades': grades}


class GradeStudent(object):
    """Grading a single student."""

    @property
    def student(self):
        id = self.request['student']
        school = app.getSchoolToolApplication()
        return school['persons'][id]

    @property
    def activities(self):
        result = [
            {'title': activity.title,
             'max': activity.scoresystem.getBestScore(),
             'hash': IKeyReference(activity).__hash__()}
            for activity in self.context.activities]
        return sorted(result, key=lambda x: x['title'])

    def grades(self):
        activities = sorted(self.context.activities,
                            key=lambda x: x.title)
        activities = [(IKeyReference(activity).__hash__(), activity)
                      for activity in activities]
        student = self.student
        gradebook = proxy.removeSecurityProxy(self.context)
        for hash, activity in activities:
            ev = gradebook.getEvaluation(student, activity)
            if ev is not None:
                yield {'activity': hash, 'value': ev.value}
            else:
                yield {'activity': hash, 'value': ''}

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect('index.html')

        elif 'UPDATE_SUBMIT' in self.request:
            student = self.student
            evaluator = zapi.getName(self.request.principal._person)
            gradebook = proxy.removeSecurityProxy(self.context)
            # Iterate through all activities
            for activity in self.context.activities:
                # Create a hash and see whether it is in the request
                hash = str(IKeyReference(activity).__hash__())
                if hash in self.request:

                    # If a value is present, create an evaluation, if the
                    # score is different
                    score = activity.scoresystem.fromUnicode(self.request[hash])
                    ev = gradebook.getEvaluation(student, activity)
                    if ev is None or score != ev.value:
                        self.context.evaluate(
                            student, activity, score, evaluator)

            self.request.response.redirect('index.html')


class GradeActivity(object):
    """Grading a single activity"""

    @property
    def activity(self):
        if hasattr(self, '_activity'):
            return self._activity
        hash = int(self.request['activity'])
        for activity in self.context.activities:
            if IKeyReference(activity).__hash__() == hash:
                self._activity = activity
                return activity

    @property
    def grades(self):
        gradebook = proxy.removeSecurityProxy(self.context)
        for student in self.context.students:
            ev = gradebook.getEvaluation(student, self.activity)
            if ev is not None:
                value = ev.value
            else:
                value = ''

            yield {'student': {'title': student.title, 'id': student.username},
                   'value': value}

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect('index.html')

        elif 'UPDATE_SUBMIT' in self.request:
            activity = self.activity
            evaluator = zapi.getName(self.request.principal._person)
            gradebook = proxy.removeSecurityProxy(self.context)
            # Iterate through all students
            for student in self.context.students:
                id = student.username
                if id in self.request:

                    # If a value is present, create an evaluation, if the
                    # score is different
                    score = activity.scoresystem.fromUnicode(self.request[id])
                    ev = gradebook.getEvaluation(student, activity)
                    if ev is None or score != ev.value:
                        self.context.evaluate(
                            student, activity, score, evaluator)

            self.request.response.redirect('index.html')


class Grade(object):
    """Grading a specific activity for a student."""

    @property
    def student(self):
        id = self.request['student']
        school = app.getSchoolToolApplication()
        return school['persons'][id]

    @property
    def activity(self):
        if hasattr(self, '_activity'):
            return self._activity
        hash = int(self.request['activity'])
        for activity in self.context.activities:
            if IKeyReference(activity).__hash__() == hash:
                self._activity = activity
                return activity

    @property
    def activityInfo(self):
        formatter = self.request.locale.dates.getFormatter('date', 'short')
        return {'title': self.activity.title,
                'date': formatter.format(self.activity.date),
                'maxScore': self.activity.scoresystem.getBestScore()}

    @property
    def evaluationInfo(self):
        formatter = self.request.locale.dates.getFormatter('dateTime', 'short')
        gradebook = proxy.removeSecurityProxy(self.context)
        ev = gradebook.getEvaluation(self.student, self.activity)
        if ev is not None:
            return {'value': ev.value,
                    'time': formatter.format(ev.time)}
        else:
            return {'value': '', 'time': ''}

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect('index.html')

        elif 'DELETE' in self.request:
            self.context.removeEvaluation(self.student, self.activity)

        elif 'UPDATE_SUBMIT' in self.request:
            evaluator = zapi.getName(self.request.principal._person)

            score = self.activity.scoresystem.fromUnicode(self.request['grade'])
            gradebook = proxy.removeSecurityProxy(self.context)
            ev = gradebook.getEvaluation(self.student, self.activity)
            if ev is None or score != ev.value:
                self.context.evaluate(
                    self.student, self.activity, score, evaluator)

            self.request.response.redirect('index.html')
