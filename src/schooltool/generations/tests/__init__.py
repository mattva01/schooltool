"""
Tests for generation scripts.
"""
from zope.interface import implements
from zope.keyreference.interfaces import IKeyReference
from zope.app.testing.setup import setUpAnnotations
from zope.app.publication.zopepublication import ZopePublication
from zope.site.folder import rootFolder
from zope.app.testing import setup


class ContextStub(object):
    """Stub for the context argument passed to evolve scripts.

        >>> from zope.app.generations.utility import getRootFolder
        >>> context = ContextStub()
        >>> getRootFolder(context) is context.root_folder
        True

    """

    class ConnectionStub(object):
        def __init__(self, root_folder):
            self.root_folder = root_folder
        def root(self):
            return {ZopePublication.root_name: self.root_folder}

    def __init__(self):
        self.root_folder = rootFolder()
        self.connection = self.ConnectionStub(self.root_folder)


_d = {}

class StupidKeyReference(object):
    implements(IKeyReference)
    key_type_id = 'StupidKeyReference'
    def __init__(self, ob):
        global _d
        self.id = id(ob)
        _d[self.id] = ob
    def __call__(self):
        return _d[self.id]
    def __hash__(self):
        return self.id
    def __cmp__(self, other):
        return cmp(hash(self), hash(other))


def catalogSetUp(test):
    """This code is deprecated, to be used only by old evolution tests."""
    setup.placefulSetUp()
    setup.setUpTraversal()
    setUpAnnotations()

    # this is code to set up the catalog for unit testing. it could
    # be extracted and put into general setup functionality

    # Make sure objects can be keyreferenced - necessary for int ids to
    # work:

    from zope.component import provideAdapter
    from persistent.interfaces import IPersistent
    provideAdapter(StupidKeyReference, [IPersistent], IKeyReference)

    # Provide the int id subscribers:

    from zope.component import provideHandler
    from zope.intid import addIntIdSubscriber, removeIntIdSubscriber
    from zope.location.interfaces import ILocation
    from zope.lifecycleevent.interfaces import IObjectAddedEvent
    from zope.lifecycleevent.interfaces import IObjectRemovedEvent
    provideHandler(addIntIdSubscriber,
                   [ILocation, IObjectAddedEvent])
    provideHandler(removeIntIdSubscriber,
                   [ILocation, IObjectRemovedEvent])

    # And the catalog subscribers:

    from zope.catalog import catalog
    from zope.catalog.interfaces import ICatalogIndex
    from zope.intid.interfaces import IIntIdAddedEvent,\
         IIntIdRemovedEvent
    from zope.lifecycleevent.interfaces import IObjectModifiedEvent
    provideHandler(catalog.indexAdded,
                   [ICatalogIndex, IObjectAddedEvent])
    provideHandler(catalog.indexDocSubscriber,
                   [IIntIdAddedEvent])
    provideHandler(catalog.reindexDocSubscriber,
                   [IObjectModifiedEvent])
    provideHandler(catalog.unindexDocSubscriber,
                   [IIntIdRemovedEvent])

def catalogTearDown(test):
    """This code is deprecated, to be used only by old evolution tests."""
    setup.placefulTearDown()
    _d.clear()
