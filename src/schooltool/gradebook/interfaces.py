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
"""Gradebook interfaces

$Id$
"""
__docformat__ = 'reStructuredText'

import zope.interface
from schooltool.requirement import interfaces, scoresystem
from schooltool.common import SchoolToolMessage as _


class IActivities(interfaces.IRequirement):
    '''A list of worksheets containing activities that must be fulfilled in a
       course or section.'''

    def getCurrentWorksheet():
        """Get the currently active worksheet."""

    def setCurrentWorksheet(worksheet):
        """Set the currently active worksheet."""

    def getCurrentActivities():
        """Get the activities for the currently active worksheet."""


class IWorksheet(interfaces.IRequirement):
    '''A list of activities that must be fulfilled in a course or section.'''


class IActivity(interfaces.IRequirement):
    '''An activity to be graded'''

    description = zope.schema.Text(
        title=_("Description"),
        description=_("A detailed description of the activity."),
        required=False)

    category = zope.schema.Choice(
        title=_("Category"),
        description=_("The activity category"),
        vocabulary="schooltool.gradebook.categories",
        required=True)

    scoresystem = scoresystem.ScoreSystemField(
        title=_("Scoresystem"),
        description=_("The activity scoresystem."),
        required=True)

    date = zope.schema.Date(
        title=_("Date"),
        description=_("The date the activity was created."),
        required=True)


class IEditGradebook(zope.interface.Interface):

    def evaluate(student, activity, score, evaluator=None):
        """Evaluate a student for an activity"""

    def removeEvaluation(student, activity):
        """Remove evaluation."""
        
    def setFinalGradeAdjustment(person, student, adjustment, reason):
        """Set the final grade adjustment for the given student."""
    

class IReadGradebook(zope.interface.Interface):

    worksheets = zope.schema.List(
        title=_('Worksheets'),
        description=_('Worksheets in this gradebook.'))

    activities = zope.schema.List(
        title=_('Activities'),
        description=_('Activities in this gradebook.'))

    students = zope.schema.List(
        title=_('Students'),
        description=_('Students in this gradebook.'))

    def hasEvaluation(student, activity):
        """Check whether an evaluation exists for a student-activity pair."""

    def getEvaluation(student, activity, default=None):
        """Get the evaluation of a student for a given activity."""

    def getCurrentEvaluationsForStudent(student):
        """Get the evaluations of the curretn worksheet for this student.

        Return iterable of 2-tuples of the form (activity, evaluation).
        """
    def getEvaluationsForStudent(student):
        """Get the evaluations of the section for this student.

        Return iterable of 2-tuples of the form (activity, evaluation).
        """

    def getEvaluationsForActivity(activity):
        """Get the evaluations of a particular activity in the section.

        Return iterable of 2-tuples of the form (student, evaluation).
        """

    def getWorksheetActivities(worksheet):
        """Get the activities for the given worksheet."""

    def getWorksheetAverage(worksheet, student):
        """Calculate the average for the worksheet, student pair."""

    def getCurrentWorksheet(person):
        """Get the user's currently active worksheet."""

    def setCurrentWorksheet(person, worksheet):
        """Set the user's currently active worksheet."""

    def getCurrentActivities(person):
        """Get the activities for the user's currently active worksheet."""

    def getSortKey(person):
        """Get the sortkey for the gradebook table."""

    def setSortKey(person, value):
        """Set the sortkey for the gradebook table.

        The value is a 2-tuple. The entry in the tuple is either "student" to
        sort by student title or the hash of the activity. The second entry
        specifies whether the sorting is reversed.
        """

    def getFinalGradeAdjustment(person, student):
        """Get the final grade adjustment for the given student."""

    def getFinalGrade(student):
        """Get the final grade for the given student."""

    def getAdjustedFinalGrade(person, student):
        """Get the adjusted final grade for the given student."""


class IGradebook(IReadGradebook, IEditGradebook):
    """The gradebook of a section.

    The gradebook provides an API that allows the user to treat it like a
    gradebook spreadsheet/table.
    """


class IMyGrades(zope.interface.Interface):
    """The students gradebook for a section.

    This interface provides an API that allows the studentto see their
    grades for a section.
    """
    worksheets = zope.schema.List(
        title=_('Worksheets'),
        description=_('Worksheets in this gradebook.'))

    def getEvaluation(student, activity, default=None):
        """Get the evaluation of a student for a given activity."""

    def getCurrentWorksheet():
        """Get the currently active worksheet."""

    def getCurrentActivities():
        """Get the activities for the currently active worksheet."""

    def setCurrentWorksheet(worksheet):
        """Set the currently active worksheet."""

