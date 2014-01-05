from persistent import Persistent
from zope.container.contained import Contained

import zope.catalog.interfaces
from BTrees.OOBTree import OOBTree
from zope.interface import implements
from zope.container.btree import BTreeContainer
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.intid import addIntIdSubscriber
from zope.lifecycleevent import ObjectAddedEvent
from zope.keyreference.interfaces import IKeyReference
from zope.security.proxy import removeSecurityProxy
from schooltool.relationship.interfaces import IRelationshipLink
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.catalog import AttributeCatalog
from schooltool.app.app import StartUpBase
from schooltool.table.catalog import ConvertingIndex


def link_target_keyref(link):
    return IKeyReference(link.target)


def link_this_keyref(link):
    linkset = link.__parent__
    return IKeyReference(linkset.__parent__)


def hash_this_target(link):
    return link_target_keyref(link), hash(link_this_keyref(link))


def hash_this_my_role(link):
    return hash(link.my_role), hash(link_this_keyref(link))


def hash_this_role(link):
    return hash(link.role), hash(link_this_keyref(link))


def hash_this_rel_type(link):
    return hash(link.rel_type), hash(link_this_keyref(link))


def cache_rel_type(link):
    app = ISchoolToolApplication(None)
    uris = app['schooltool.relationship.uri']
    cached = uris.cache(link.rel_type)
    return cached


def get_link_shared_uid(link):
    uid = tuple(
        [hash(link.rel_type)] +
        sorted([
            (hash(link.role), hash(IKeyReference(link.target))),
            (hash(link.my_role), hash(IKeyReference(link.__parent__.__parent__))),
            ])
        )
    return uid


class SharedIndex(Persistent, Contained):
    implements(zope.catalog.interfaces.ICatalogIndex)

    def __init__(self):
        Persistent.__init__(self)
        Contained.__init__(self)
        self.uids = OOBTree()
        self.data = OOBTree()

    def get(self, docid, key):
        uid = self.uids.get(docid)
        if uid is None:
            return None
        return self.data.get((uid, key))

    def __contains__(self, docid_key):
        docid, key = docid_key
        if docid not in self.uids:
            return False
        return (self.uids[docid], key) in self.data

    def index_doc(self, docid, link):
        self.uids[docid] = get_link_shared_uid(link)
        for key, value in link.shared.items():
            self.data[self.uids[docid], key] = value

    def unindex_doc(self, docid):
        if docid not in self.uids:
            return
        unindex_uid = self.uids[docid]
        tounindex = set()
        for uid, key in self.data:
            if uid == unindex_uid:
                tounindex.add((uid, key))
        for idx in tounindex:
            del self.data[idx]

    def clear(self):
        self.data.clear()
        self.uids.clear()

    def apply(query):
        raise NotImplemented('querying this index is not supported')


class URICache(BTreeContainer):

    def cache(self, uri):
        hashed = str(hash(uri))
        if hashed not in self:
            self[hashed] = uri
        return hashed


class URICacheStartUp(StartUpBase):

    before = ('prepare-catalog-container', )

    def __call__(self):
        if 'schooltool.relationship.uri' not in self.app:
            self.app['schooltool.relationship.uri'] = URICache()


class LinkCatalog(AttributeCatalog):

    version = '1.1 - uri cache'
    interface = IRelationshipLink
    attributes = ()

    def setIndexes(self, catalog):
        super(LinkCatalog, self).setIndexes(catalog)
        catalog['my_role_hash'] = ConvertingIndex(converter=hash_this_my_role)
        catalog['role_hash'] = ConvertingIndex(converter=hash_this_role)
        catalog['rel_type_hash'] = ConvertingIndex(converter=hash_this_rel_type)
        catalog['target'] = ConvertingIndex(converter=hash_this_target)
        catalog['shared'] = SharedIndex()


getLinkCatalog = LinkCatalog.get


def indexLinks(event):
    iids = getUtility(IIntIds)
    for link in event.getLinks():
        link = removeSecurityProxy(link)
        addIntIdSubscriber(link, ObjectAddedEvent(link))
        lid = iids.getId(link)
        getLinkCatalog().index_doc(lid, link)
        link.__parent__._lids.add(lid)
