"""
SchoolBell application interfaces
"""

from zope.interface import Interface


class ISchoolBellApplication(Interface):
    """The main SchoolBell application object.

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """

