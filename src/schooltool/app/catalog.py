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
SchoolTool catalogs.
"""
from zope.interface import implementer, implements, implementsOnly
from zope.intid.interfaces import IIntIds, IIntIdAddedEvent, IIntIdRemovedEvent
from zope.component import adapter, queryUtility, getUtility
from zope.component.hooks import getSite
from zope.container import btree
from zope.container.contained import Contained
from zope.lifecycleevent import IObjectModifiedEvent
from zope.security.proxy import removeSecurityProxy

from zc.catalog import extentcatalog
from zc.catalog import catalogindex

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ICatalogStartUp
from schooltool.app.interfaces import ICatalogs
from schooltool.app.interfaces import IVersionedCatalog
from schooltool.app.app import ActionBase
from schooltool.table.catalog import FilterImplementing


APP_CATALOGS_KEY = 'schooltool.app.catalog:Catalogs'


class CatalogStartupBase(ActionBase):
    implementsOnly(ICatalogStartUp)


class Catalogs(btree.BTreeContainer):
    implements(ICatalogs)


@adapter(ISchoolToolApplication)
@implementer(ICatalogs)
def getAppCatalogs(app):
    if APP_CATALOGS_KEY not in app:
        app[APP_CATALOGS_KEY] = Catalogs()
    return app[APP_CATALOGS_KEY]


class VersionedCatalog(Contained):
    implements(IVersionedCatalog)

    expired = False
    version = 0
    catalog = None

    def __init__(self, catalog, version):
        self.catalog = catalog
        self.catalog.__parent__ = self
        self.catalog.__name__ = 'catalog'
        self.version = version

    def __repr__(self):
        return '<%s v. %r>: %s' % (
            self.__class__.__name__, self.version, self.catalog)


class PrepareCatalogContainer(CatalogStartupBase):

    def __call__(self):
        catalogs = ICatalogs(self.app)
        for entry in catalogs.values():
            entry.expired = True


class ExpiredCatalogCleanup(CatalogStartupBase):

    def __call__(self):
        catalogs = ICatalogs(self.app)
        for key in list(catalogs):
            if catalogs[key].expired:
                del catalogs[key]


class CatalogFactory(CatalogStartupBase):

    after = ('prepare-catalog-container', )
    before = ('expired-catalog-cleanup', )

    version = u''

    @classmethod
    def key(cls):
        return u'catalog:%s.%s' % (cls.__module__, cls.__name__)

    @classmethod
    def get(cls, ignored=None):
        app = getSite()
        catalogs = app[APP_CATALOGS_KEY]
        versioned = catalogs[cls.key()]
        return versioned.catalog

    def getVersion(self):
        return unicode(self.version)

    def createCatalog(self):
        raise NotImplementedError()

    def setIndexes(self, catalog):
        raise NotImplementedError()

    def __call__(self):
        app = ISchoolToolApplication(None)
        catalogs = ICatalogs(app)
        key = self.key()
        version = self.getVersion()

        if key in catalogs:
            if catalogs[key].version == version:
                catalogs[key].expired = False
            else:
                del catalogs[key]

        if key not in catalogs:
            catalog = self.createCatalog()
            catalogs[key] = VersionedCatalog(catalog, version)
            # XXX: if setIndexes throw, delete the catalog and rethrow
            self.setIndexes(catalog)


class CatalogImplementing(CatalogFactory):
    """Factory of catalogs containing objects implementing the given interface."""

    interface = None # override in child classes

    def createCatalog(self):
        return extentcatalog.Catalog(
            extentcatalog.FilterExtent(
                FilterImplementing(self.interface)))

    def getVersion(self):
        return u'interface:%s, version:%s' % (
            u'%s.%s' % (self.interface.__module__, self.interface.__name__),
            super(CatalogImplementing, self).getVersion())


class AttributeCatalog(CatalogImplementing):
    """Catalog indexing specified attributes of objects implementing
    the given interface."""

    attributes = ()

    def getVersion(self):
        return u'attributes:%s, %s' % (
            tuple(sorted(self.attributes)),
            super(AttributeCatalog, self).getVersion())

    def setIndexes(self, catalog):
        for name in self.attributes:
            catalog[name] = catalogindex.ValueIndex(name)


@adapter(IIntIdAddedEvent)
def indexDocSubscriber(event):
    app = ISchoolToolApplication(None, None)
    if app is None:
        return
    obj = removeSecurityProxy(event.object)
    util = getUtility(IIntIds, context=app)
    obj_id = util.getId(obj)
    catalogs = ICatalogs(app)
    for entry in catalogs.values():
        entry.catalog.index_doc(obj_id, obj)


@adapter(IObjectModifiedEvent)
def reindexDocSubscriber(event):
    app = ISchoolToolApplication(None, None)
    if app is None:
        return
    obj = removeSecurityProxy(event.object)
    util = queryUtility(IIntIds, context=app)
    if util is None:
        return
    obj_id = util.queryId(obj)
    if obj_id is None:
        return
    catalogs = ICatalogs(app)
    if obj is catalogs:
        return
    for entry in catalogs.values():
        entry.catalog.index_doc(obj_id, obj)


@adapter(IIntIdRemovedEvent)
def unindexDocSubscriber(event):
    app = ISchoolToolApplication(None, None)
    if app is None:
        return
    obj = removeSecurityProxy(event.object)
    util = getUtility(IIntIds, context=app)
    obj_id = util.queryId(obj)
    if obj_id is None:
        return
    catalogs = ICatalogs(app)
    for entry in catalogs.values():
        entry.catalog.unindex_doc(obj_id)


def appendGlobbing(text):
    words = filter(None, text.split(' '))
    return ' '.join([word.endswith('*') and word or ('%s*' % word)
                     for word in words])


def buildQueryString(text):
    terms = []
    parts = text.lower().split('"')
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # before quote
            if not part:
                continue
            alternatives = [term.strip()
                            for term in part.split(',')]
            alternatives = map(appendGlobbing, alternatives)
            alternatives = filter(None, alternatives)
            terms.append(' or '.join(alternatives))
        else:
            # insert text inside quotes verbatim
            terms.append('"%s"' % part)
    return ' '.join(terms)


def getRequestIntIds(request=None):
    return getUtility(IIntIds)
