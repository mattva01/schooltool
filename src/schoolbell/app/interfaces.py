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


class IGroup(Interface):
    """Group."""


class IGroupContainer(IContainer):
    """Container of groups."""

    contains(IGroup)


class IResource(Interface):
    """Resource."""


class IResourceContainer(IContainer):
    """Container of resources."""

    contains(IResource)


class ISchoolBellApplication(IReadContainer):
    """The main SchoolBell application object.

    The application is a read-only container with the following items:

        'persons' - IPersonContainer
        'groups' - IGroupContainer
        'resources' - IResourceContainer

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """
