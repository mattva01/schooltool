import unittest

from zope.testing import doctest
from zope.app.testing import setup
from zope.app.component.hooks import getSite, setSite

def doctest_utilityRegistration():
    """
    We set up the IntIds utility::

      >>> from schooltool.utility import UtilitySetUp
      >>> from zope.app.intid import IntIds
      >>> from zope.app.intid.interfaces import IIntIds
      >>> setup = UtilitySetUp(IntIds, IIntIds)

    We'll pass through None as the event, as it's not in use,
    and the site::

      >>> site = getSite()
      >>> setup(site, None)
      >>> setSite(site)

    Note that we have to restore the site - the setup functionality
    gets rid of the site using setSite() afterwards as this disrupts
    other schooltool setup code. This may be a bug somewhere in
    schooltool the utility setup code works around.
    
    We now expect the utility to be available::
    
      >>> from zope.component import getUtility
      >>> util = getUtility(IIntIds)
      >>> IIntIds.providedBy(util)
      True
    """

def doctest_multipleUtilityRegistration():
    """
    A more complex scenario where multiple dependent utilities are
    registered, the intids utility and the catalog. The catalog also
    contains indexes, so need special setup code to initialize the indexes.

    Let's import the information needed to set up the IntIds utility first::

      >>> from zope.app.intid import IntIds
      >>> from zope.app.intid.interfaces import IIntIds

    And now for the catalog::

      >>> from zope.app.catalog.catalog import Catalog
      >>> from zope.app.catalog.interfaces import ICatalog
      >>> from zope.app.catalog.field import FieldIndex

    We'll define the catalog setup function that creates the index::

      >>> from zope.interface import Interface
      >>> def catalogSetUp(catalog):
      ...     catalog['myindex'] = FieldIndex(Interface, 'foo')
      
    Now let's set these up as utilities::

      >>> from schooltool.utility import UtilitySpecification
      >>> from schooltool.utility import MultiUtilitySetUp
      >>> setup = MultiUtilitySetUp(
      ...    UtilitySpecification(IntIds, IIntIds),
      ...    UtilitySpecification(Catalog, ICatalog, setUp=catalogSetUp))
      >>> site = getSite()
      >>> setup(site, None)
      >>> setSite(site)
      
    We'll check whether the utilities are available::

      >>> from zope.component import getUtility
      >>> intids = getUtility(IIntIds)
      >>> IIntIds.providedBy(intids)
      True
      >>> catalog = getUtility(ICatalog)
      >>> ICatalog.providedBy(catalog)
      True
      
    """

def doctest_utilityOverride():
    """
    Let's create a utility::

      >>> from persistent import Persistent
      >>> from zope.app.container.contained import Contained
      >>> from zope.interface import Interface, implements
      >>> class IMyUtility(Interface):
      ...     pass
      >>> class MyUtility1(Persistent, Contained):
      ...     implements(IMyUtility)

    Let's register it::

      >>> from schooltool.utility import UtilitySetUp
      >>> setup = UtilitySetUp(MyUtility1, IMyUtility)
      >>> from zope.app.component.hooks import getSite, setSite
      >>> site = getSite()
      >>> setup(site, None)
      >>> setSite(site)

    And let's register another one, overriding the first::

      >>> class MyUtility2(Persistent, Contained):
      ...   implements(IMyUtility)
      >>> setup2 = UtilitySetUp(MyUtility2, IMyUtility, override=True)
      >>> setup2(site, None)
      >>> setSite(site)
      
    Now we expect there to be only MyUtility2::

      >>> from zope.component import getUtility
      >>> util = getUtility(IMyUtility)
      >>> isinstance(util, MyUtility2)
      True
    """

def sitePlacefulSetUp(*args):
    setup.placefulSetUp(site=True)

def sitePlacefulTearDown(*args):
    setup.placefulTearDown()
    
def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=sitePlacefulSetUp,
                             tearDown=sitePlacefulTearDown)])
