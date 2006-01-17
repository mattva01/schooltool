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
"""ScoreSystem Interfaces

$Id$
"""
__docformat__ = 'restructuredtext'
import decimal
import zope.interface
import zope.schema

from schooltool.requirement import interfaces


class UNSCORED(object):
    """This object behaves like a string.

    We want this to behave as a global, meaning it's pickled by name, rather
    than value. We need to arrange that it has a suitable __reduce__.
    """

    def __reduce__(self):
        return 'UNSCORED'

    def __repr__(self):
        return 'UNSCORED'

UNSCORED = UNSCORED()


class AbstractScoreSystem(object):
    zope.interface.implements(interfaces.IScoreSystem)

    def __init__(self, title, description=None):
        self.title = title
        self.description = description

    def isPassingScore(self, score):
        """See interfaces.IScoreSystem"""
        raise NotImplementedError

    def isValidScore(self, score):
        """See interfaces.IScoreSystem"""
        raise NotImplementedError

    def getBestScore(self):
        """See interfaces.IScoreSystem"""
        raise NotImplementedError

    def fromUnicode(self, rawScore):
        """See interfaces.IScoreSystem"""
        raise NotImplementedError

    def getNumericalValue(self, score):
        """See interfaces.IScoreSystem"""
        raise NotImplementedError

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.title)


class DiscreteValuesScoreSystem(AbstractScoreSystem):
    """Abstract Discrete Values Score System"""

    zope.interface.implements(interfaces.IDiscreteValuesScoreSystem)

    # See interfaces.IDiscreteValuesScoreSystem
    scores = None
    _minPassingScore = None
    _bestScore = None

    def __init__(self, title=None, description=None,
                 scores=None, bestScore=None, minPassingScore=None):
        self.title = title
        self.description = description
        self.scores = scores or []
        self._bestScore = bestScore
        self._minPassingScore = minPassingScore

    def isPassingScore(self, score):
        """See interfaces.IScoreSystem"""
        if score is UNSCORED:
            return None
        if self._minPassingScore is None:
            return None
        scores = dict(self.scores)
        return scores[score] >= scores[self._minPassingScore]

    def isValidScore(self, score):
        """See interfaces.IScoreSystem"""
        scores = dict(self.scores).keys()
        return score in scores + [UNSCORED]

    def getBestScore(self):
        """See interfaces.IScoreSystem"""
        return self._bestScore

    def fromUnicode(self, rawScore):
        """See interfaces.IScoreSystem"""
        if rawScore is '':
            return UNSCORED

        if not self.isValidScore(rawScore):
            raise zope.schema.ValidationError(
                "'%s' is not a valid score." %rawScore)
        return rawScore

    def getNumericalValue(self, score):
        """See interfaces.IScoreSystem"""
        if score is UNSCORED:
            return None
        scores = dict(self.scores)
        return scores[score]


class GlobalDiscreteValuesScoreSystem(DiscreteValuesScoreSystem):

    def __init__(self, name, *args, **kwargs):
        self.__name__ = name
        super(GlobalDiscreteValuesScoreSystem, self).__init__(*args, **kwargs)

    def __reduce__(self):
        return self.__name__

PassFail = GlobalDiscreteValuesScoreSystem(
    'PassFail',
    u'Pass/Fail', u'Pass or Fail score system.',
    [(u'Pass', 1), (u'Fail', 0)], u'Pass', u'Pass')

AmericanLetterScoreSystem = GlobalDiscreteValuesScoreSystem(
    'AmericanLetterScoreSystem',
    u'Letter Grade', u'American Letter Grade',
    [('A', 4), ('B', 3), ('C', 2), ('D', 1), ('F', 0)], 'A', 'D')

ExtendedAmericanLetterScoreSystem = GlobalDiscreteValuesScoreSystem(
    'ExtendedAmericanLetterScoreSystem',
    u'Extended Letter Grade', u'American Extended Letter Grade',
    [('A+', 4.0), ('A', 4.0), ('A-', 3.7),
     ('B+', 3.3), ('B', 3.0), ('B-', 2.7),
     ('C+', 2.3), ('C', 2.0), ('C-', 1.7),
     ('D+', 1.3), ('D', 1.0), ('D-', 0.7),
     ('F',  0.0)], 'A+', 'D-')


class RangedValuesScoreSystem(AbstractScoreSystem):
    """Abstract Ranged Values Score System"""

    zope.interface.implements(interfaces.IRangedValuesScoreSystem)

    # See interfaces.IRangedValuesScoreSystem
    min = None
    max = None
    _minPassingScore = None

    def __init__(self, title=None, description=None,
                 min=0, max=100, minPassingScore=None):
        self.title = title
        self.description = description
        self.min, self.max = min, max
        self._minPassingScore = minPassingScore

    def isPassingScore(self, score):
        """See interfaces.IScoreSystem"""
        if score is UNSCORED or self._minPassingScore is None:
            return None
        return score >= self._minPassingScore

    def isValidScore(self, score):
        """See interfaces.IScoreSystem"""
        if score is UNSCORED:
            return True
        return score >= self.min and score <= self.max

    def getBestScore(self):
        """See interfaces.IScoreSystem"""
        return self.max

    def fromUnicode(self, rawScore):
        """See interfaces.IScoreSystem"""
        if rawScore is '':
            return UNSCORED

        if '.' not in rawScore:
            score = int(rawScore)
        else:
            score = decimal.Decimal(rawScore)

        if not self.isValidScore(score):
            raise zope.schema.ValidationError(
                "%r is not a valid score." %score)
        return score

    def getNumericalValue(self, score):
        """See interfaces.IScoreSystem"""
        if score is UNSCORED:
            return None
        return score


class GlobalRangedValuesScoreSystem(RangedValuesScoreSystem):

    def __init__(self, name, *args, **kwargs):
        self.__name__ = name
        super(GlobalRangedValuesScoreSystem, self).__init__(*args, **kwargs)

    def __reduce__(self):
        return self.__name__


PercentScoreSystem = GlobalRangedValuesScoreSystem(
    'PercentScoreSystem',
    u'Percent', u'Percent Score System', 0, 100, 60)

HundredPointsScoreSystem = GlobalRangedValuesScoreSystem(
    'HundredPointsScoreSystem',
    u'100 Points', u'100 Points Score System', 0, 100, 60)

