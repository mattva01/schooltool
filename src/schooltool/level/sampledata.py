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
Timetable sample data generation

$Id$
"""

import random

from zope.app import zapi
from zope.interface import implements
from zope.wfmc.interfaces import IProcessDefinition
from zope.security.proxy import removeSecurityProxy

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.level.level import Level
from schooltool.level.interfaces import IManagerWorkItems, IAcademicRecord
from schooltool.level.promotion import SelectInitialLevel


class SampleLevels(object):

    implements(ISampleDataPlugin)

    name = 'levels'
    dependencies = ('students', )

    def generate(self, app, seed=None):
        self.random = random.Random()
        self.random.seed(str(seed) + self.name)
        levels = removeSecurityProxy(app['levels'])
        levels['12th-grade'] = Level('12th grade')
        levels['11th-grade'] = Level('11th grade',
                                     nextLevel=levels['12th-grade'])
        levels['10th-grade'] = Level('10th grade',
                                     nextLevel=levels['11th-grade'])
        levels['9th-grade'] = Level('9th grade', isInitial=True,
                                    nextLevel=levels['10th-grade'])

        pd = zapi.getUtility(IProcessDefinition, 'schooltool.promotion')

        for personid in app['persons']:
            if personid.startswith('student'):
                person = removeSecurityProxy(app['persons'][personid])
                process = pd()
                process.start(person, None, None)
                IAcademicRecord(person).levelProcess = process

        work = IManagerWorkItems(removeSecurityProxy(app['groups']['manager']))
        for item in tuple(work.values()):
            if isinstance(item, SelectInitialLevel):
                level = self.random.choice(levels.values())
                item.finish(level)
