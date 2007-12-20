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
"""
Sample courses generation

$Id: sampledata.py 6565 2007-01-11 16:43:11Z ignas $
"""

from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.sampledata import PortableRandom
from schooltool.course.section import Section
from schooltool.gradebook.category import CategoryVocabulary
from schooltool.gradebook.interfaces import IActivities, IGradebook
from schooltool.gradebook.activity import Worksheet, Activity
from schooltool.requirement.interfaces import IEvaluations
from schooltool.requirement.evaluation import Evaluation, Evaluations, EVALUATIONS_KEY
from schooltool.requirement.scoresystem import PercentScoreSystem


class SampleGrades(object):

    implements(ISampleDataPlugin)

    name = 'grades'
    dependencies = ('sections',)

    def generate(self, app, seed=None):
        self.random = PortableRandom(str(seed) + self.name)
        categories = CategoryVocabulary()
        project = [term for term in categories if term.title == 'Project'][0]
        exam = [term for term in categories if term.title == 'Exam'][0]
        
        for section in app['sections'].values():
            # first create the worksheets and activities
            worksheets = IActivities(section)
            worksheet1 = Worksheet('Semester 1')
            worksheet2 = Worksheet('Semester 2')
            worksheets['worksheet1'] = worksheet1
            worksheets['worksheet2'] = worksheet2
            activity1A = Activity('First Semester Project', project, PercentScoreSystem)
            activity1B = Activity('Midterm Exam', exam, PercentScoreSystem)
            activity2A = Activity('Second Semester Project', project, PercentScoreSystem)
            activity2B = Activity('Final Exam', exam, PercentScoreSystem)
            worksheet1['activity1A'] = activity1A
            worksheet1['activity1B'] = activity1B
            worksheet2['activity2A'] = activity2A
            worksheet2['activity2B'] = activity2B

            # next we will evalluate each student in the section for each activity
            activities = [activity1A, activity1B, activity2A, activity2B]
            teacher = list(section.instructors)[0]
            for student in section.members:
                annotations = IAnnotations(removeSecurityProxy(student))
                try:
                    evaluations = annotations[EVALUATIONS_KEY]
                except KeyError:
                    evaluations = Evaluations()
                    annotations[EVALUATIONS_KEY] = evaluations
                for activity in activities:
                    score = self.random.randrange(60) + 41
                    evaluation = Evaluation(activity, activity.scoresystem, 
                        score, removeSecurityProxy(teacher))
                    evaluations.addEvaluation(evaluation)

