"""
SchoolBell application object
"""

from persistent import Persistent
from zope.interface import implements

from schoolbell.app.interfaces import ISchoolBellApplication

class SchoolBellApplication(Persistent):
    """The main application object.

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """

    implements(ISchoolBellApplication)
