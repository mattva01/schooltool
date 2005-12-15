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
Unit tests for schooltool.level.sampledata

$Id$
"""

import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup, ztapi

from schooltool.group.interfaces import IGroup
from schooltool.level.interfaces import IManagerWorkItems
from schooltool.testing import setup as stsetup


def setUpLevels():
    from zope.wfmc import xpdl
    import os
    package = xpdl.read(open(os.path.join(os.path.dirname(__file__),
                                          '..', 'promotion.xpdl')))
    pd = package['promotion']
    pd.id = u'schooltool.promotion'

    from zope.wfmc.interfaces import IProcessDefinition
    ztapi.provideUtility(IProcessDefinition, pd, name='schooltool.promotion')

    from zope.wfmc.adapter import integration
    pd.integration = integration

    import zope.component
    import zope.wfmc.interfaces
    from schooltool.level import promotion

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
                                  provides=IManagerWorkItems)

    from schooltool.level import record
    zope.component.provideAdapter(record.AcademicRecord)


def setUp(test):
    setup.placefulSetUp()
    setUpLevels()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleLevels():
    """A sample data plugin that generates levels

        >>> from schooltool.level.sampledata import SampleLevels
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleLevels()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin depends on the 'students' plugin, because it assigns
    students to levels:

        >>> plugin.dependencies
        ('students',)

    We'll need the manager group in app, and some persons:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
        >>> app = stsetup.setupSchoolToolSite()
        >>> app['groups']['manager'] = Group('Manager')
        >>> app['persons']['student000'] = Person('student000', 'John')
        >>> app['persons']['student001'] = Person('student001', 'Joe')
        >>> app['persons']['student002'] = Person('student002', 'Jo')

    This plugin creates 4 levels:

        >>> plugin.generate(app, 13)
        >>> len(app['levels'])
        4

    The levels are consistent:

        >>> app['levels'].validate()

    Also, all the students get promotion workflows initialized, and
    they get promoted to a random level:

        >>> from schooltool.level.interfaces import IAcademicRecord
        >>> from zope.security.proxy import removeSecurityProxy
        >>> for i in range(3):
        ...     person = app['persons']['student00' + str(i)]
        ...     proc = IAcademicRecord(person).levelProcess
        ...     print proc.workflowRelevantData.level
        <Level '10th grade'>
        <Level '11th grade'>
        <Level '12th grade'>

    """

def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
