from zope.app import zapi
from zope.app.component.hooks import getSite, setSite
from zope.component import queryUtility

class UtilitySpecification(object):
    def __init__(self, factory, iface, name='', setUp=None,
                 override=False,
                 storage_name=None):
        if storage_name is None:
            storage_name = iface.__module__ + '.' + iface.__name__
        self.storage_name = storage_name
        self.factory = factory
        self.setUp = setUp
        self.iface = iface
        self.utility_name = name 
        self.override = override

def setUpUtilities(site, specs):
    setSite(site)
    try:
        manager = site.getSiteManager()
        default = zapi.traverse(site, '++etc++site/default')
        for spec in specs:
            local_utility = getLocalUtility(default, spec)    
            if local_utility is not None:
                if spec.override:
                    # override existing utility
                    name = local_utility.__name__
                    manager.unregisterUtility(name,
                                              spec.iface)
                    del default[name]
                else:
                    # do not register this utility; we already got it
                    continue
            utility = spec.factory()
            default[spec.storage_name] = utility
            if spec.setUp is not None:
                spec.setUp(utility)
            manager.registerUtility(utility, spec.iface, spec.utility_name)
    finally:
        # we clean up as other bootstrapping code might otherwise get
        # confused...
        setSite(None)

def getLocalUtility(default, spec):
    util = queryUtility(spec.iface, name=spec.utility_name, default=None)
    if util is None:
        return util
    if util.__parent__ is default:
        return util
    else:
        return None

class UtilitySetUp(UtilitySpecification):        
    """Set up a single utility.
    """
    def __call__(self, site, event):
        setUpUtilities(site, [self])
        
class MultiUtilitySetUp(object):
    """Set up multiple related utilities that need to be in order.

    (for instance intids needs to be set up before the catalog is).
    """
    def __init__(self, *specifications):
        self.specifications = specifications
        
    def __call__(self, site, event):
        setUpUtilities(site, self.specifications)
