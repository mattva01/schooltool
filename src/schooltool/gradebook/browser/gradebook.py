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
import zope.schema
from zope.security import proxy
from zope.app import zapi
from zope.app.keyreference.interfaces import IKeyReference

from schooltool.app import app
from schooltool.gradebook import interfaces
from schooltool.person.interfaces import IPerson
from schooltool.requirement.scoresystem import UNSCORED
from schooltool import SchoolToolMessage as _


class GradebookOverview(object):
    """Gradebook Overview/Table"""

    def update(self):
        """Retrieve sorting information and store changes of it."""
        person = IPerson(self.request.principal)
        if 'sort_by' in self.request:
            sort_by = self.request['sort_by']
            key, reverse = self.context.getSortKey(person)
            if sort_by == key:
                reverse = not reverse
            else:
                reverse=False
            self.context.setSortKey(person, (sort_by, reverse))
        self.sortKey = self.context.getSortKey(person)

    def activities(self):
        """Get  a list of all activities."""
        result = [
            {'title': activity.title,
             'max':activity.scoresystem.getBestScore(),
             'hash': hash(IKeyReference(activity))}
            for activity in self.context.activities]
        return result

    def table(self):
        """Generate the table of grades."""
        activities = [(hash(IKeyReference(activity)), activity)
                      for activity in self.context.activities]
        gradebook = proxy.removeSecurityProxy(self.context)
        rows = []
        for student in self.context.students:
            grades = []
            for act_hash, activity in activities:
                ev = gradebook.getEvaluation(student, activity)
                if ev is not None:
                    grades.append({'activity': act_hash, 'value': ev.value})
                else:
                    grades.append({'activity': act_hash, 'value': '-'})

            rows.append(
                {'student': {'title': student.title, 'id': student.username},
                 'grades': grades})

        # Do the sorting
        key, reverse = self.sortKey
        def generateKey(row):
            if key != 'student':
                grades = dict([(str(grade['activity']), grade['value'])
                               for grade in row['grades']])
                return grades.get(key, row['student']['title'])
            return row['student']['title']

        return sorted(rows, key=generateKey, reverse=reverse)

    def statistics(self):
        """Calculate various statistical quantities for all activities."""
        statistics = interfaces.IStatistics(self.context)
        activities = self.context.activities
        decimal = self.request.locale.numbers.getFormatter('decimal')
        percent = self.request.locale.numbers.getFormatter('decimal')
        stats = [
            {'name': _('Average'), 'formatter': decimal,
             'function': statistics.calculateAverage, 'values': []},
            {'name': _('Percent Average'), 'formatter': percent,
             'function': statistics.calculatePercentAverage, 'values': []},
            {'name': _('Median'), 'formatter': decimal,
             'function': statistics.calculateMedian, 'values': []},
            {'name': _('Standard Deviation'), 'formatter': decimal,
             'function': statistics.calculateStandardDeviation, 'values': []},
            {'name': _('Variance'), 'formatter': decimal,
             'function': statistics.calculateVariance, 'values': []},
            ]
        for act in activities:
            for stat in stats:
                value = stat['function'](act)
                if not value:
                    stat['values'].append(_('N/A'))
                else:
                    stat['values'].append(stat['formatter'].format(value))
        return stats

class GradeStudent(object):
    """Grading a single student."""

    message = ''

    @property
    def student(self):
        id = self.request['student']
        school = app.getSchoolToolApplication()
        return school['persons'][id]

    @property
    def activities(self):
        return [
            {'title': activity.title,
             'max': activity.scoresystem.getBestScore(),
             'hash': hash(IKeyReference(activity))}
            for activity in self.context.activities]

    def grades(self):
        activities = [(hash(IKeyReference(activity)), activity)
                      for activity in self.context.activities]
        student = self.student
        gradebook = proxy.removeSecurityProxy(self.context)
        for act_hash, activity in activities:
            ev = gradebook.getEvaluation(student, activity)
            value = self.request.get(str(act_hash))
            if ev is not None and ev.value is not UNSCORED:
                yield {'activity': act_hash, 'value': value or ev.value}
            else:
                yield {'activity': act_hash, 'value': value or ''}

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect('index.html')

        elif 'UPDATE_SUBMIT' in self.request:
            student = self.student
            evaluator = zapi.getName(IPerson(self.request.principal))
            gradebook = proxy.removeSecurityProxy(self.context)
            # Iterate through all activities
            for activity in self.context.activities:
                # Create a hash and see whether it is in the request
                act_hash = str(hash(IKeyReference(activity)))
                if act_hash in self.request:

                    # If a value is present, create an evaluation, if the
                    # score is different
                    try:
                        score = activity.scoresystem.fromUnicode(
                            self.request[act_hash])
                    except (zope.schema.ValidationError, ValueError):
                        self.message = _(
                            'The grade $value for activity $name is not valid.',
                            mapping={'value': self.request[act_hash],
                                     'name': activity.title})
                        return
                    ev = gradebook.getEvaluation(student, activity)
                    # Delete the score
                    if ev is not None and score is UNSCORED:
                        self.context.removeEvaluation(student, activity)
                    # Do nothing
                    elif ev is None and score is UNSCORED:
                        continue
                    # Replace the score or add new one/
                    elif ev is None or score != ev.value:
                        self.context.evaluate(
                            student, activity, score, evaluator)

            self.request.response.redirect('index.html')


class GradeActivity(object):
    """Grading a single activity"""

    message = ''

    @property
    def activity(self):
        if hasattr(self, '_activity'):
            return self._activity
        act_hash = int(self.request['activity'])
        for activity in self.context.activities:
            if hash(IKeyReference(activity)) == act_hash:
                self._activity = activity
                return activity

    @property
    def grades(self):
        gradebook = proxy.removeSecurityProxy(self.context)
        for student in self.context.students:
            ev = gradebook.getEvaluation(student, self.activity)
            value = self.request.get(student.username)
            if ev is not None:
                value = value or ev.value
            else:
                value = value or ''

            yield {'student': {'title': student.title, 'id': student.username},
                   'value': value}

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect('index.html')

        elif 'UPDATE_SUBMIT' in self.request:
            activity = self.activity
            evaluator = zapi.getName(IPerson(self.request.principal))
            gradebook = proxy.removeSecurityProxy(self.context)
            # Iterate through all students
            for student in self.context.students:
                id = student.username
                if id in self.request:

                    # If a value is present, create an evaluation, if the
                    # score is different
                    try:
                        score = activity.scoresystem.fromUnicode(
                            self.request[id])
                    except (zope.schema.ValidationError, ValueError):
                        self.message = _(
                            'The grade $value for $name is not valid.',
                            mapping={'value': self.request[id],
                                     'name': student.title})
                        return
                    ev = gradebook.getEvaluation(student, activity)
                    # Delete the score
                    if ev is not None and score is UNSCORED:
                        self.context.removeEvaluation(student, activity)
                    # Do nothing
                    elif ev is None and score is UNSCORED:
                        continue
                    # Replace the score or add new one/
                    elif ev is None or score != ev.value:
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
        act_hash = int(self.request['activity'])
        for activity in self.context.activities:
            if hash(IKeyReference(activity)) == act_hash:
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
            evaluator = zapi.getName(IPerson(self.request.principal))

            score = self.activity.scoresystem.fromUnicode(self.request['grade'])
            gradebook = proxy.removeSecurityProxy(self.context)
            ev = gradebook.getEvaluation(self.student, self.activity)
            if ev is None or score != ev.value:
                self.context.evaluate(
                    self.student, self.activity, score, evaluator)

            self.request.response.redirect('index.html')
