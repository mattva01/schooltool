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
__docformat__='restructuredtext'

import zope.interface

from schooltool.requirement import interfaces

class UNSCORED(object):
    """This object behaves like a string.

    We want this to behave as a global, meaning it's pickled
    by name, rather than value. We need to arrange that it has a suitable
    __reduce__.
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
        raise NotImplemented

    def isValidScore(self, score):
        """See interfaces.IScoreSystem"""
        raise NotImplemented

    def __repr__(self):
        return '<ScoreSystem %r>' %self.title


class DiscreteValuesScoreSystem(AbstractScoreSystem):
    """Abstract Discrete Values Score System"""
    zope.interface.implements(interfaces.IDiscreteValuesScoreSystem)

    # See interfaces.IDiscreteValuesScoreSystem
    values = None
    _minPassingScore = None

    def __init__(self, title=None, description=None,
                 values=None, minPassingScore=None):
        self.title = title
        self.description = description
        self.values = values or []
        self._minPassingScore = minPassingScore

    def isPassingScore(self, score):
        """See interfaces.IScoreSystem"""
        if score is UNSCORED:
            return None
        if self._minPassingScore is None:
            return None
        index = self.values.index
        return index(score) <= index(self._minPassingScore)

    def isValidScore(self, score):
        """See interfaces.IScoreSystem"""
        return score in self.values + [UNSCORED]

    def __repr__(self):
        return '<ScoreSystem %r>' %self.title


PassFail = DiscreteValuesScoreSystem(
    u'Pass/Fail', u'Pass or Fail score system.',
    [True, False], True)
PassFail.PASS = True
PassFail.FAIL = False

AmericanLetterScoreSystem = DiscreteValuesScoreSystem(
    u'Letter Grade', u'American Letter Grade',
    ['A', 'B', 'C', 'D', 'F'], 'D')

ExtendedAmericanLetterScoreSystem = DiscreteValuesScoreSystem(
    u'Extended Letter Grade', u'American Extended Letter Grade',
    ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'],
    'D-')

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


PercentScoreSystem = RangedValuesScoreSystem(
    u'Percent', u'Percent Score System', 0, 100, 60)
