"""
Tests for generation scripts.

$Id$
"""


from zope.app.publication.zopepublication import ZopePublication
from zope.app.folder.folder import rootFolder


class ContextStub(object):
    """Stub for the context argument passed to evolve scripts.

        >>> from zope.app.zopeappgenerations import getRootFolder
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
