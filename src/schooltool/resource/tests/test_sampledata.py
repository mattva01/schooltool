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
Unit tests for schooltool.resource.sampledata

$Id$
"""
import unittest
from pprint import pprint

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing.setup import setupLocalGrants
from schooltool.testing import setup as stsetup

def setUp(test):
    setup.placefulSetUp()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleResources():
    """A sample data plugin that generates resources

        >>> from schooltool.resource.sampledata import SampleResources
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleResources()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> app = stsetup.setupSchoolToolSite()
        >>> len(app['resources'])
        0

        >>> plugin.generate(app, 42)

        >>> len(app['resources'])
        88

        >>> for i in range(64):
        ...     assert app['resources']['room%02d' % i].isLocation

        >>> for i in range(24):
        ...     assert not app['resources']['projector%02d' % i].isLocation


    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
