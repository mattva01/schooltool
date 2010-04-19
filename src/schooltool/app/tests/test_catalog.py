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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for catalogs
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.component import provideAdapter
from zope.component.hooks import getSite, setSite
from zope.site import SiteManagerContainer
from zope.site.folder import rootFolder

from schooltool.testing.setup import ZCMLWrapper
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ICatalogs
from schooltool.app.catalog import getAppCatalogs


class AppStub(dict, SiteManagerContainer):
    implements(ISchoolToolApplication)


class CatalogStub(dict):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<CatalogStub %r>' % self.name


def provideApplicationStub():
    app = AppStub()
    provideAdapter(
        lambda ignored: app,
        adapts=(None,),
        provides=ISchoolToolApplication)
    return app


def doctest_Catalogs():
    """Tests for Catalogs.

        >>> app = provideApplicationStub()

    There is an adapter that sets up and returns the catalogs container for the app.

        >>> list(app.items())
        []

        >>> catalogs = ICatalogs(app)

        >>> list(app.items())
        [('schooltool.app.catalog:Catalogs',
          <schooltool.app.catalog.Catalogs object at ...>)]

        >>> verifyObject(ICatalogs, catalogs)
        True

        >>> catalogs is app.values()[0]
        True

    Catalogs is a dict-like container.

        >>> print dict(catalogs)
        {}

    """


def doctest_PrepareCatalogContainer():
    """Tests for PrepareCatalogContainer.

        >>> class VersionedCatalogStub(object):
        ...     def __init__(self, expired=False):
        ...         self.expired = expired
        ...     def __repr__(self):
        ...         return '<Stub expired=%s>' % self.expired

    Let's build an app with some catalog entries.

        >>> app = provideApplicationStub()
        >>> catalogs = ICatalogs(app)

        >>> catalogs['cat-1'] = VersionedCatalogStub(expired=False)
        >>> catalogs['cat-2'] = VersionedCatalogStub(expired=True)
        >>> catalogs['cat-3'] = VersionedCatalogStub(expired=False)

    PrepareCatalogContainer is supposed to be executed as the first action
    of application catalog startup.

        >>> from schooltool.app.interfaces import ICatalogStartUp
        >>> from schooltool.app.catalog import PrepareCatalogContainer

        >>> action = PrepareCatalogContainer(app)
        >>> verifyObject(ICatalogStartUp, action)
        True

    When executed it marks all catalogs expired.

        >>> action()

        >>> print sorted(ICatalogs(app).items())
        [(u'cat-1', <Stub expired=True>),
         (u'cat-2', <Stub expired=True>),
         (u'cat-3', <Stub expired=True>)]

    """


def doctest_ExpiredCatalogCleanup():
    """Tests for ExpiredCatalogCleanup.

        >>> class VersionedCatalogStub(object):
        ...     def __init__(self, expired=False):
        ...         self.expired = expired
        ...     def __repr__(self):
        ...         return '<Stub expired=%s>' % self.expired

    Let's build an app with some catalog entries.

        >>> app = provideApplicationStub()
        >>> catalogs = ICatalogs(app)

        >>> catalogs['cat-1'] = VersionedCatalogStub(expired=False)
        >>> catalogs['cat-2'] = VersionedCatalogStub(expired=True)
        >>> catalogs['cat-3'] = VersionedCatalogStub(expired=False)

    ExpiredCatalogCleanup is supposed to be executed as the last action
    of application catalog startup.

        >>> from schooltool.app.interfaces import ICatalogStartUp
        >>> from schooltool.app.catalog import ExpiredCatalogCleanup

        >>> action = ExpiredCatalogCleanup(app)
        >>> verifyObject(ICatalogStartUp, action)
        True

    When executed it removes expired catalogs.

        >>> action()

        >>> print sorted(ICatalogs(app).items())
        [(u'cat-1', <Stub expired=False>),
         (u'cat-3', <Stub expired=False>)]

    """


def doctest_CatalogFactory():
    """Tests for CatalogFactory.

        >>> app = provideApplicationStub()

    CatalogFactory is a base class for creating and registering versioned catalogs.

        >>> from schooltool.app.catalog import CatalogFactory
        >>> factory = CatalogFactory(app)

        >>> factory.createCatalog()
        Traceback (most recent call last):
        ...
        NotImplementedError

        >>> factory.setIndexes(None)
        Traceback (most recent call last):
        ...
        NotImplementedError

    It is also an action to be executed on application catalog startup.

        >>> from schooltool.app.interfaces import ICatalogStartUp

        >>> class CatalogFactoryForTest(CatalogFactory):
        ...    version = 1
        ...    def createCatalog(self):
        ...        return CatalogStub('test')
        ...    def setIndexes(self, catalog):
        ...        catalog['idx-1'] = 'Stub index 1'

        >>> factory = CatalogFactoryForTest(app)

        >>> verifyObject(ICatalogStartUp, factory)
        True

    It defines some control on when it wants to be executed.

        >>> factory.after
        ('prepare-catalog-container',)

        >>> factory.before
        ('expired-catalog-cleanup',)

    The class itself has some helpers to fetch the catalog from app.

        >>> print CatalogFactoryForTest.key()
        catalog:schooltool.app.tests.test_catalog.CatalogFactoryForTest

        >>> print CatalogFactoryForTest.get()
        None

    Well, the catalog was not set up yet.  Let's build it.

        >>> from schooltool.app.interfaces import IVersionedCatalog

        >>> factory()

        >>> catalog = CatalogFactoryForTest.get()

        >>> print catalog
        <CatalogStub 'test'>

        >>> sorted(catalog.items())
        [('idx-1', 'Stub index 1')]

    Both catalog and it's version entry are stored in app's catalog container.

        >>> version_entry = catalog.__parent__

        >>> print version_entry
        <VersionedCatalog v. u'1'>: <CatalogStub 'test'>

        >>> verifyObject(IVersionedCatalog, version_entry)
        True

        >>> print version_entry.__parent__
        <schooltool.app.catalog.Catalogs object at ...>

        >>> version_entry.__parent__ is ICatalogs(app)
        True

        >>> print version_entry.__name__
        catalog:schooltool.app.tests.test_catalog.CatalogFactoryForTest

        >>> print version_entry.__name__ == CatalogFactoryForTest.key()
        True

    """


def doctest_CatalogFactory_versioning():
    """Tests for CatalogFactory handling of catalog versions.

        >>> class CatalogCreatorMixin(object):
        ...    def createCatalog(self):
        ...        return CatalogStub('test-1')
        ...    def setIndexes(self, catalog):
        ...        catalog['idx-1'] = 'Stub index 1'

        >>> app = provideApplicationStub()
        >>> catalogs = ICatalogs(app)

    Let's create a catalog first.

        >>> from schooltool.app.catalog import CatalogFactory
        >>> class Factory1(CatalogCreatorMixin, CatalogFactory):
        ...    version = 1

        >>> factory1 = Factory1(app)

        >>> factory1()
        >>> catalog1 = Factory1.get()

        >>> print catalog1
        <CatalogStub 'test-1'>

        >>> print sorted(catalogs.keys())
        [u'catalog:schooltool.app.tests.test_catalog.Factory1']

    If the version stays the same, factory leaves the catalog untouched, but
    changes it's expired status.

        >>> class Factory1(CatalogCreatorMixin, CatalogFactory):
        ...    version = 1

        >>> catalog1.__parent__.expired = True

        >>> factory1 = Factory1(app)
        >>> factory1()

        >>> Factory1.get() is catalog1
        True

        >>> catalog1.__parent__.expired
        False

        >>> print sorted(catalogs.keys())
        [u'catalog:schooltool.app.tests.test_catalog.Factory1']

    If we changed the version, catalog gets re-created.

        >>> class Factory1(CatalogCreatorMixin, CatalogFactory):
        ...    version = 1.2
        ...    def setIndexes(self, catalog):
        ...        catalog['idx-1'] = 'Stub index 1 point 2'

        >>> factory12 = Factory1(app)
        >>> factory12()

        >>> catalog12 = Factory1.get()
        >>> catalog12 is catalog1
        False

        >>> print sorted(catalog12.items())
        [('idx-1', 'Stub index 1 point 2')]

    CatalogFactory actually uses the getVersion method, not the version
    attribute.  Let's override getVersion

        >>> class Factory1(CatalogCreatorMixin, CatalogFactory):
        ...    version = 1.2
        ...    def getVersion(self):
        ...        return 'stable-version'

        >>> factory = Factory1(app)
        >>> factory()

        >>> catalog_stable = Factory1.get()

        >>> catalog_stable is catalog12
        False

        >>> print Factory1.get().__parent__
        <VersionedCatalog v. 'stable-version'>: <CatalogStub 'test-1'>

        >>> class Factory1(CatalogCreatorMixin, CatalogFactory):
        ...    version = 1.314
        ...    def getVersion(self):
        ...        return 'stable-version'

        >>> factory1 = Factory1(app)
        >>> factory1()

        >>> Factory1.get() is catalog_stable
        True

    """


def setUp(test):
    setup.placefulSetUp()
    provideAdapter(getAppCatalogs)


def tearDown(test):
    setup.placefulTearDown()


def provideStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.registerAdapter(factory, required=adapts, provided=provides, name=name)


def unregisterStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.unregisterAdapter(factory, required=adapts, provided=provides, name=name)


def setUpIntegration(test):
    setup.placefulSetUp()
    zcml = ZCMLWrapper()
    zcml.setUp(
        namespaces={"": "http://namespaces.zope.org/zope"},
        i18n_domain='schooltool')
    zcml.include('zope.app.zcmlfiles')
    zcml.include('schooltool.app', file='catalog.zcml')
    root = rootFolder()
    root['app'] = provideApplicationStub()
    setup.createSiteManager(root['app'], setsite=True)
    test.globs.update({
        'zcml': zcml,
        'CatalogStub': CatalogStub,
        'provideAdapter': provideStubAdapter,
        'unregisterAdapter': unregisterStubAdapter,
        })


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=optionflags),
        doctest.DocFileSuite(
            'catalog-integration.txt',
            setUp=setUpIntegration, tearDown=tearDown,
            optionflags=optionflags),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
