"""
SchoolBell application object
"""

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app.container.btree import BTreeContainer
from zope.app.container.sample import SampleContainer

from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import IPersonContainer


class SchoolBellApplication(Persistent, SampleContainer):
    """The main application object.

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """

    implements(ISchoolBellApplication)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = PersonContainer()

    def _newContainerData(self):
        return PersistentDict()


class PersonContainer(BTreeContainer):
    """Container of persons."""

    implements(IPersonContainer)
