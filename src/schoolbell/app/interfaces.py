"""
SchoolBell application interfaces
"""

from zope.interface import Interface
from zope.schema import Object
from zope.app.container.interfaces import IReadContainer, IContainer
from zope.app.container.constraints import contains


class IPerson(Interface):
    """Person."""


class IPersonContainer(IContainer):
    """Container of persons."""

    contains(IPerson)


class ISchoolBellApplication(IReadContainer):
    """The main SchoolBell application object.

    The application is a read-only container with the following items:

        'persons' - IPersonContainer

    TODO: groups, resources

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """
