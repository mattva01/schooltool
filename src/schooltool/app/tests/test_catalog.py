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
from zope.interface import implements, Interface
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
        return '<%s %r>' % (self.__class__.__name__, self.name)


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


def doctest_CatalogImplementing():
    """Tests for CatalogImplementing.  This is a factory of catalogs that
    contain only objects implementing given interface.

    Say we have two objects implementing very similar interfaces.

        >>> from zope.schema import TextLine

        >>> class TitledObject(object):
        ...    def __init__(self, title):
        ...        self.title = title
        ...    def __repr__(self):
        ...        return '<%s (%r)>' % (self.__class__.__name__, self.title)

        >>> class IFoo(Interface):
        ...     title = TextLine(title=u"Title")
        >>> class Foo(TitledObject):
        ...     implements(IFoo)

        >>> class IBar(Interface):
        ...     title = TextLine(title=u"Title")
        >>> class Bar(TitledObject):
        ...     implements(IBar)

        >>> app = provideApplicationStub()
        >>> app['objects'] = {
        ...     1: Foo('one'),
        ...     2: Bar('two'),
        ...     3: Foo('three'),
        ...     }

    Let's create a catalog that indexes titles of IFoo.

        >>> from zope.container.contained import Contained
        >>> from schooltool.app.catalog import CatalogImplementing

        >>> class TitleIndex(Contained):
        ...     def __init__(self):
        ...         self.data = []
        ...     def index_doc(self, id, value):
        ...         self.data.append((id, value))

        >>> class CatalogTitles(CatalogImplementing):
        ...    version = 1
        ...    interface = IFoo
        ...    def setIndexes(self, catalog):
        ...        catalog['title'] = TitleIndex()

        >>> factory = CatalogTitles(app)
        >>> factory()

        >>> catalog = CatalogTitles.get()
        >>> print catalog.__parent__
        <VersionedCatalog v.
            u'interface:schooltool.app.tests.test_catalog.IFoo,
              version:1'>:
        <zc.catalog.extentcatalog.Catalog object at ...>

    This catalog only indexes objects implementing IFoo.

        >>> def index_app(catalog):
        ...     for docid, doc in app['objects'].items():
        ...         catalog.index_doc(docid, doc)
        ...     print sorted(catalog['title'].data)

        >>> index_app(CatalogTitles.get())
        [(1, <Foo ('one')>), (3, <Foo ('three')>)]

    Catalog indexes are untouched after app restart.

        >>> factory = CatalogTitles(app)
        >>> factory()

        >>> CatalogTitles.get() is catalog
        True

        >>> print sorted(CatalogTitles.get()['title'].data)
        [(1, <Foo ('one')>), (3, <Foo ('three')>)]

    If we change the version, catalog will be re-created, as expected.

        >>> class CatalogTitles(CatalogImplementing):
        ...    version = 2
        ...    interface = IFoo
        ...    def setIndexes(self, catalog):
        ...        catalog['title'] = TitleIndex()

        >>> factory = CatalogTitles(app)
        >>> factory()

        >>> catalog2 = CatalogTitles.get()
        >>> catalog2 is catalog
        False

    We trust other machinery to reindex the catalog.

        >>> print sorted(CatalogTitles.get()['title'].data)
        []

    If we change the interface, catalog also gets re-created.

        >>> index_app(CatalogTitles.get())
        [(1, <Foo ('one')>), (3, <Foo ('three')>)]

        >>> class CatalogTitles(CatalogImplementing):
        ...    version = 2
        ...    interface = IBar
        ...    def setIndexes(self, catalog):
        ...        catalog['title'] = TitleIndex()

        >>> factory = CatalogTitles(app)
        >>> factory()

        >>> CatalogTitles.get() is catalog2
        False

        >>> index_app(CatalogTitles.get())
        [(2, <Bar ('two')>)]

        >>> catalog3 = CatalogTitles.get()
        >>> print catalog3.__parent__
        <VersionedCatalog v.
            u'interface:schooltool.app.tests.test_catalog.IBar,
              version:2'>:
        <zc.catalog.extentcatalog.Catalog object at ...>

    """


def doctest_AttributeCatalog():
    """Tests for AttributeCatalog.  This is a factory of catalogs that
    index attributes of objects implementing given interface.

    Say we have an object we want to catalog.

        >>> from zope.schema import TextLine

        >>> class ITriplet(Interface):
        ...     a = TextLine(title=u"Title")
        ...     b = TextLine(title=u"Title")
        ...     c = TextLine(title=u"Title")
        >>> class Triplet(object):
        ...     implements(ITriplet)
        ...     def __init__(self, a, b, c):
        ...         self.a, self.b, self.c = a, b, c
        ...     def __repr__(self):
        ...         return '<%s (%s:%s:%s)>' % (
        ...             self.__class__.__name__,
        ...             self.a, self.b, self.c)

        >>> class Foo(object):
        ...     implements(Interface)
        ...     a = b = c = 0

        >>> app = provideApplicationStub()
        >>> app['objects'] = {
        ...     0: Foo(),
        ...     1: Triplet('one', 'eins', 'I'),
        ...     2: Triplet('two', 'zwei', 'II'),
        ...     3: Triplet('three', 'drei', 'III'),
        ...     }

    Let's create a catalog that indexes few attributes of the triplet.

        >>> from schooltool.app.catalog import AttributeCatalog

        >>> class CatalogTriplets(AttributeCatalog):
        ...    version = 1
        ...    interface = ITriplet
        ...    attributes = ('a', 'c')

        >>> factory = CatalogTriplets(app)
        >>> factory()

    And index some objects.

        >>> def index_app(catalog):
        ...     for docid, doc in app['objects'].items():
        ...         catalog.index_doc(docid, doc)
        ...     for name, index in catalog.items():
        ...         print 'catalog[%r]: %s' % (
        ...             name,
        ...             sorted(index.documents_to_values.items()))

        >>> index_app(CatalogTriplets.get())
        catalog[u'a']: [(1, 'one'), (2, 'two'), (3, 'three')]
        catalog[u'c']: [(1, 'I'), (2, 'II'), (3, 'III')]

    We can see that version of the catalog also includes the list of attributes,
    so the catalog will be recreated when attributes, interface or version changes.

        >>> catalog = CatalogTriplets.get()
        >>> print catalog.__parent__
        <VersionedCatalog v.
            u"attributes:('a', 'c'),
              interface:schooltool.app.tests.test_catalog.ITriplet,
              version:1">:
        <zc.catalog.extentcatalog.Catalog object at ...>

        >>> class CatalogTriplets(AttributeCatalog):
        ...    version = 1
        ...    interface = ITriplet
        ...    attributes = ('b')

        >>> factory = CatalogTriplets(app)
        >>> factory()

        >>> CatalogTriplets.get() is catalog
        False

        >>> index_app(CatalogTriplets.get())
        catalog[u'b']: [(1, 'eins'), (2, 'zwei'), (3, 'drei')]

    """


def doctest_catalog_subscribers():
    """Tests for catalog subscribers.

    Let's provide our subscribers.

        >>> from zope.component import provideHandler
        >>> from schooltool.app.catalog import indexDocSubscriber
        >>> from schooltool.app.catalog import reindexDocSubscriber
        >>> from schooltool.app.catalog import unindexDocSubscriber

        >>> provideHandler(indexDocSubscriber)
        >>> provideHandler(reindexDocSubscriber)
        >>> provideHandler(unindexDocSubscriber)

    And set up the event firing helpers.

        >>> from zope.component import provideUtility, queryUtility
        >>> from zope.event import notify
        >>> from zope.intid.interfaces import (
        ...     IIntIds, IntIdAddedEvent, IntIdRemovedEvent)
        >>> from zope.lifecycleevent import (
        ...     ObjectAddedEvent, ObjectRemovedEvent, ObjectModifiedEvent)

        >>> def addAndNotify(obj, obj_id):
        ...     util = queryUtility(IIntIds)
        ...     if util is None:
        ...         print "No IIntIds utility, so don't fire IntIdAddedEvent"
        ...         return
        ...     util[obj] = obj_id
        ...     print 'firing IntIdAddedEvent'
        ...     notify(IntIdAddedEvent(obj, ObjectAddedEvent(obj)))

        >>> def notifyModified(obj):
        ...     print 'firing ObjectModifiedEvent'
        ...     notify(ObjectModifiedEvent(obj))

        >>> def notifyAndRemove(obj):
        ...     util = queryUtility(IIntIds)
        ...     if util is None:
        ...         print "No IIntIds utility, so don't fire IntIdRemovedEvent"
        ...         return
        ...     print 'firing IntIdRemovedEvent'
        ...     notify(IntIdRemovedEvent(obj, ObjectAddedEvent(obj)))
        ...     del util[obj]

    When database is being set up, we may have no SchoolToolApplication and
    no IntIds utility.

        >>> class TestObj(object):
        ...     __parent__ = __name__ = None
        ...     def __init__(self, name):
        ...         self.name = name
        ...     def __repr__(self):
        ...         return '<%s %r>' % (self.__class__.__name__, self.name)

        >>> test_one = TestObj('missing_one')
        >>> addAndNotify(test_one, 1)
        No IIntIds utility, so don't fire IntIdAddedEvent

        >>> notifyModified(test_one)
        firing ObjectModifiedEvent

        >>> notifyAndRemove(test_one)
        No IIntIds utility, so don't fire IntIdRemovedEvent

    Having IntIds utility is not enough as catalogs live within the application
    itself.  Subscribers handle this case also.

        >>> class IntIdsStub(dict):
        ...     def getId(self, obj):
        ...         return self[obj]
        ...     def queryId(self, obj):
        ...         return self.get(obj)

        >>> provideUtility(IntIdsStub(), IIntIds)

        >>> test_two = TestObj('two')
        >>> addAndNotify(test_two, 2)
        firing IntIdAddedEvent

        >>> notifyModified(test_two)
        firing ObjectModifiedEvent

        >>> notifyAndRemove(test_two)
        firing IntIdRemovedEvent

    Let's provide an application and set up a catalog.

        >>> from schooltool.app.catalog import VersionedCatalog

        >>> class PrintingCatalogStub(CatalogStub):
        ...      def index_doc(self, doc_id, doc):
        ...          print 'CatalogStub(%r) indexed doc %s (%s)' % (
        ...              self.name, doc_id, doc)
        ...      def unindex_doc(self, doc_id):
        ...          print 'CatalogStub(%r) unindexed doc %s' % (
        ...              self.name, doc_id)

        >>> app = provideApplicationStub()
        >>> catalogs = ICatalogs(app)
        >>> catalogs['demo'] = VersionedCatalog(PrintingCatalogStub('demo'), 'v1')

    We can now see objects being indexed.

        >>> test_three = TestObj('three')
        >>> addAndNotify(test_three, 3)
        firing IntIdAddedEvent
        CatalogStub('demo') indexed doc 3 (<TestObj 'three'>)

        >>> test_three.name='three and a half'
        >>> notifyModified(test_three)
        firing ObjectModifiedEvent
        CatalogStub('demo') indexed doc 3 (<TestObj 'three and a half'>)

        >>> notifyAndRemove(test_three)
        firing IntIdRemovedEvent
        CatalogStub('demo') unindexed doc 3

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
    zcml.include('schooltool.common', file='zcmlfiles.zcml')
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
