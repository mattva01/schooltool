from zope.app.intid.interfaces import IIntIds
from zope.app.intid import IntIds
from zope.app.catalog.interfaces import ICatalog
from zope.app.catalog.catalog import Catalog
from zope.app.catalog.text import TextIndex
from zope.app.catalog.field import FieldIndex
from zope.interface import implements
from zope.component import adapts

from schooltool.utility import UtilitySpecification, MultiUtilitySetUp

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
    
def catalogSetUp(catalog):
    catalog['fulltext'] = TextIndex('fulltext', ISearch)

catalogSetUpSubscriber = MultiUtilitySetUp(
    UtilitySpecification(IntIds, IIntIds),
    UtilitySpecification(Catalog, ICatalog, 'demographics_catalog',
                         setUp=catalogSetUp),
    )
