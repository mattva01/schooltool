from zope.app import zapi
from zope.app.component.site import LocalSiteManager
from zope.app.component.interfaces import ISite
from zope.app.intid.interfaces import IIntIds
from zope.app.intid import IntIds
from zope.app.catalog.interfaces import ICatalog
from zope.app.catalog.catalog import Catalog
from zope.app.catalog.text import TextIndex
from zope.app.catalog.field import FieldIndex
from zope.app.catalog.field import FieldIndex
from zope.interface import Interface, implements
from zope.component import adapts, getUtility
from zope.app.component.hooks import setSite
from schooltool.demographics.interfaces import ISearch
from schooltool.person.interfaces import IPerson

class Search(object):
    implements(ISearch)
    adapts(IPerson)
    
    def __init__(self, context):
        self.context = context

    @property
    def fulltext(self):
        return [self.context.title]

def catalogSetUpSubscriber(site, event):
    # go to the site management folder
    default = zapi.traverse(site, '++etc++site/default')
    manager = site.getSiteManager()
    setSite(site)
    # need this so that intids can be looked up later on
    setUpIntIds(default, manager)
    setUpCatalog(default, manager, site)
    # we clean up as other bootstrapping code might otherwise get
    # confused...
    setSite(None)
    
def setUpIntIds(default, manager):
    if 'schooltool_intids' in default:
        return
    intids = IntIds()
    default['schooltool_intids'] = intids
    manager.registerUtility(intids, IIntIds)
    
def setUpCatalog(default, manager, site):
    if 'demographics_catalog' in default:
        return
    catalog = Catalog()
    default['demographics_catalog'] = catalog
    manager.registerUtility(catalog, ICatalog, 'demographics_catalog')
    index = TextIndex('fulltext', ISearch)
    catalog['fulltext'] = TextIndex('fulltext', ISearch)
