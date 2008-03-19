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
"""Testing utilities for testing Term related code.

$Id$
"""
import datetime

from zope.interface import implements
from zope.component import provideUtility

from schooltool.term.interfaces import IDateManager

class DateManagerStub(object):
    implements(IDateManager)

    def __init__(self, date):
        self.date = date

    @property
    def today(self):
        return self.date


def setUpDateManagerStub(date=None):
    if not date:
        date = datetime.date(2005, 9, 20)
    provideUtility(IDateManager,
                   DateManagerStub(date))
