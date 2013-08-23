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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for schooltool.resource.sampledata
"""

import unittest
import doctest

from zope.interface.verify import verifyObject
from zope.app.testing import setup

from schooltool.testing import setup as stsetup


def setUp(test):
    setup.placefulSetUp()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleResources():
    """A sample data plugin that generates resources

        >>> from schooltool.resource.interfaces import ILocation
        >>> from schooltool.resource.sampledata import SampleResources
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleResources()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> app = stsetup.setUpSchoolToolSite()
        >>> len(app['resources'])
        0

        >>> plugin.generate(app, 42)

        >>> len(app['resources'])
        88

        >>> for i in range(64):
        ...     location = app['resources']['room%02d' % i]
        ...     assert ILocation.providedBy(location)
        ...     assert location.type == 'Classroom'

        >>> for i in range(24):
        ...     projector = app['resources']['projector%02d' % i]
        ...     assert not ILocation.providedBy(projector)
        ...     assert projector.type == "Projector"


    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
