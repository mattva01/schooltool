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
Testing helper functions for this package

$Id$
"""

import os

import zope.wfmc.interfaces
import zope.component
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema import vocabulary
from zope.wfmc import xpdl, adapter

from schooltool.group.interfaces import IGroup
import schooltool.level.level
import schooltool.level.browser.promotion
from schooltool.level import interfaces, level, promotion, record, browser


def setUpPromotionWorkflow():
    xpdl_dir = os.path.dirname(__file__)

    package = xpdl.read(open(os.path.join(xpdl_dir, 'promotion.xpdl')))
    pd = package['promotion']
    pd.id = 'schooltool.promotion'
    pd.integration = adapter.integration
    zope.component.provideUtility(pd, name='schooltool.promotion')

    zope.component.provideAdapter(promotion.Manager,
                                  provides=zope.wfmc.interfaces.IParticipant,
                                  name='.manager')
    zope.component.provideAdapter(promotion.ProgressToNextLevel,
                                  name='.progressToNextLevel')
    zope.component.provideAdapter(promotion.SelectInitialLevel,
                                  provides=zope.wfmc.interfaces.IWorkItem,
                                  name='.selectInitialLevel')
    zope.component.provideAdapter(promotion.SetLevelOutcome,
                                  provides=zope.wfmc.interfaces.IWorkItem,
                                  name='.setLevelOutcome')
    zope.component.provideAdapter(promotion.UpdateStatus,
                                  name='.updateStatus')
    zope.component.provideAdapter(promotion.WriteRecord,
                                  name='.writeRecord')

    zope.component.provideAdapter(promotion.getManagerWorkItems,
                                  adapts=(IGroup,),
                                  provides=interfaces.IManagerWorkItems)
    zope.component.provideAdapter(record.AcademicRecord)

    zope.component.provideHandler(promotion.addProcessToStudent,
                                  (zope.wfmc.interfaces.IProcessStarted,))

    zope.component.provideHandler(promotion.removeProcessFromStudent,
                                  (zope.wfmc.interfaces.IProcessFinished,))

    zope.component.provideAdapter(
        browser.promotion.SchemaWorkItemView,
        adapts=(promotion.SelectInitialLevel, IBrowserRequest),
        provides=browser.promotion.IFinishSchemaWorkitem)

    zope.component.provideAdapter(
        browser.promotion.SetLevelOutcomeView,
        adapts=(promotion.SetLevelOutcome, IBrowserRequest),
        provides=browser.promotion.IFinishSchemaWorkitem)

    registry = vocabulary.getVocabularyRegistry()
    registry.register('Levels', level.LevelVocabulary)


def setUpLevels(app):
    app['levels']['level1'] = level.Level('1st Grade', isInitial=True)

    app['levels']['level2'] = level.Level('2nd Grade')
    app['levels']['level1'].nextLevel = app['levels']['level2']

    app['levels']['level3'] = level.Level('3rd Grade')
    app['levels']['level2'].nextLevel = app['levels']['level3']
