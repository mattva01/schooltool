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
"""Statistics for the gradebook

$Id$
"""
__docformat__ = 'reStructuredText'
import math
import zope.component
import zope.interface

from schooltool.gradebook import interfaces


class Statistics(object):
    """Statistics adapter for the gradebook.

    This implementation only works with scoresystems that are numerical.
    """
    zope.interface.implements(interfaces.IStatistics)
    zope.component.adapts(interfaces.IGradebook)

    def __init__(self, context):
        self.context = context

    def calculateAverage(self, activity):
        """See interfaces.IStatistics"""
        scores = [ev.value
                  for s, ev in self.context.getEvaluationsForActivity(activity)]
        try:
            samples = len(scores)
        except TypeError:
            raise TypeError('Scores are not numerical.')
        return float(sum(scores))/samples

    def calculatePercentAverage(self, activity):
        """See interfaces.IStatistics"""
        total = getattr(activity.scoresystem, 'max', None)
        if total is None:
            raise TypeError('Scoresystem cannot provide max value.')
        return self.calculateAverage(activity)/total*100.0

    def calculateMedian(self, activity):
        """See interfaces.IStatistics"""
        scores = [ev.value
                  for s, ev in self.context.getEvaluationsForActivity(activity)]
        scores.sort()
        return float(scores[len(scores)/2])

    def calculateStandardDeviation(self, activity):
        """See interfaces.IStatistics"""
        return math.sqrt(self.calculateVariance(activity))

    def calculateVariance(self, activity):
        """See interfaces.IStatistics"""
        avg = self.calculateAverage(activity)
        scores = [ev.value
                  for s, ev in self.context.getEvaluationsForActivity(activity)]
        help = [(score - avg)**2 for score in scores]
        return sum(help)/(len(scores)-1)
