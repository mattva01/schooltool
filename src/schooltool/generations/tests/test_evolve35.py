#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve35
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.component import queryUtility, provideUtility
from zope.component.hooks import getSite, setSite
from zope.intid import IntIds
from zope.intid.interfaces import IIntIds
from zope.traversing.api import traverse
from zope.site import LocalSiteManager
from zope.site.folder import Folder
from zope.location import Location
from zope.catalog.interfaces import ICatalog

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.generations.tests import ContextStub
from schooltool.generations.evolve35 import CATALOG_KEYS


def registerLocalUtility(site, utility, name):
   manager = site.getSiteManager()
   default = traverse(site, '++etc++site/default')
   default['storage.key:'+name] = utility
   manager.registerUtility(utility, ICatalog, name)


class UtilityStub(Folder):
    def __init__(self, name):
        super(UtilityStub, self).__init__()
        self.name = name

    def __repr__(self):
        return '<%s (%s)>' % (self.__class__.__name__, self.name)


class AppStub(Folder):
    implements(ISchoolToolApplication)


def doctest_evolve35():
    """Test evolution to generation 35.

    We'll need int ids.

        >>> provideUtility(IntIds(), IIntIds)

    First, let's build ST app with local catalog utilities.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()
        >>> app.setSiteManager(LocalSiteManager(app))

        >>> for name in CATALOG_KEYS:
        ...     registerLocalUtility(app, UtilityStub(name), name)

        >>> setSite(app)
        >>> for name in CATALOG_KEYS:
        ...     print queryUtility(ICatalog, name=name, default=None)
        <UtilityStub (schooltool.basicperson)>
        <UtilityStub (schooltool.contact)>
        <UtilityStub (schooltool.person)>

    Set the site to something else and evolve.

        >>> context.root_folder['frob'] = frob = Folder()
        >>> frob.setSiteManager(LocalSiteManager(frob))
        >>> setSite(frob)

        >>> from schooltool.generations.evolve35 import evolve
        >>> evolve(context)

    Active site was kept.

        >>> getSite() is frob
        True

    And catalogs in our app were unregistered.

        >>> setSite(app)
        >>> for name in CATALOG_KEYS:
        ...     print queryUtility(ICatalog, name=name, default=None)
        None
        None
        None

    """


def setUp(test):
    setup.placefulSetUp()
    setup.setUpTraversal()


def tearDown(test):
    setup.placefulTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
