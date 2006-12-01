#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve20

$Id$
"""

import unittest

from zope.app.component.hooks import setSite
from zope.app.component.site import LocalSiteManager
from zope.app.component.site import SiteManagerContainer
from zope.app.container.interfaces import IContained
from zope.app.testing import setup
from zope.component import queryUtility
from zope.interface import Interface
from zope.interface import implements
from zope.location.interfaces import ILocation
from zope.testing import doctest

from schooltool.person.interfaces import IPersonFactory
from schooltool.app.interfaces import IHaveCalendar
from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(SiteManagerContainer):
    implements(ISchoolToolApplication, ILocation)
    __parent__ = None
    __name__ = None


class UtilityStub(object):
    implements(IContained)

    def __init__(self, name):
        self.__name__ = name
        self.__parent__ = None

    def __repr__(self):
        return '<UtilityStub %s>' % self.__name__


def doctest_evolve():
    r"""Doctest for evolution to generation 20.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()

    We are doing the placeful setup by hand as we want our schooltool
    application to be the site:

      >>> setup.placelessSetUp()
      >>> setup.zope.app.component.hooks.setHooks()
      >>> setup.setUpAnnotations()
      >>> setup.setUpDependable()
      >>> setup.setUpTraversal()
      >>> setup.setUpSiteManagerLookup()
      >>> manager = LocalSiteManager(app)
      >>> app.setSiteManager(manager)
      >>> setSite(app)

      >>> from zope.app import zapi
      >>> default = zapi.traverse(app, '++etc++site/default')

      >>> utility = UtilityStub('Local_utility_1')
      >>> default['Local_utility_1'] = utility
      >>> manager.registerUtility(utility, IPersonFactory)

      >>> utility = UtilityStub('Local_utility_2')
      >>> default['Local_utility_2'] = utility
      >>> manager.registerUtility(utility, Interface)

      >>> sorted(dict(default).items())
      [(u'Local_utility_1', <UtilityStub Local_utility_1>),
       (u'Local_utility_2', <UtilityStub Local_utility_2>)]
      >>> queryUtility(IPersonFactory)
      <UtilityStub Local_utility_1>
      >>> queryUtility(Interface)
      <UtilityStub Local_utility_2>

      >>> from schooltool.generations.evolve20 import evolve
      >>> setSite(None)
      >>> evolve(context)
      >>> setSite(app)

      >>> sorted(dict(default).items())
      [(u'Local_utility_2', <UtilityStub Local_utility_2>)]
      >>> queryUtility(IPersonFactory, default=None) is None
      True
      >>> queryUtility(Interface)
      <UtilityStub Local_utility_2>

    I am registering a global utility to check that nothing is being
    done with it:

      >>> queryUtility(IPersonFactory, default=None) is None
      True

      >>> utility = UtilityStub('Global_utility_1')
      >>> zapi.getGlobalSiteManager().registerUtility(utility, IPersonFactory)

      >>> setSite(None)
      >>> evolve(context)
      >>> setSite(app)

      >>> queryUtility(IPersonFactory, default=None)
      <UtilityStub Global_utility_1>

      >>> setup.placefulTearDown()

    """

def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE
                                |doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
