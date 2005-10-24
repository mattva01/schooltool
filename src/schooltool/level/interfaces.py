#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
School Level and Related Interfaces

$Id$
"""
import zope.interface
import zope.interface.common.mapping
import zope.schema
import zope.app.container.constraints
from zope.app import container
from zope.app import zapi

from schooltool import SchoolToolMessageID as _


class ILevelValidationError(zope.interface.Interface):
    """An error that can be created during level validation."""

class LevelValidationError(Exception):
    zope.interface.implements(ILevelValidationError)


class ILevelLoopError(ILevelValidationError):
    """A loop was detected in the level graph."""

    level = zope.interface.Attribute("This is the level that points back "
                                     "to a level that was found in the graph "
                                     "before.")

class LevelLoopError(LevelValidationError):
    zope.interface.implements(ILevelLoopError)

    def __init__(self, level):
        LevelValidationError.__init__(
            self, 'Loop-Closing Level: ' + zapi.getName(level))
        self.level = level

class IDisconnectedLevelsError(ILevelValidationError):
    """A loop was detected in the level graph."""

    levels = zope.interface.Attribute(
        "A list of levels not properly connected.")

class DisconnectedLevelsError(LevelValidationError):
    zope.interface.implements(IDisconnectedLevelsError)

    def __init__(self, levels):
        LevelValidationError.__init__(
            self, ', '.join([zapi.getName(level) for level in levels]))
        self.levels = levels


class ILevel(zope.interface.Interface):
    """A grade level in a school."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the level."),
        required=True)

    isInitial = zope.schema.Bool(
        title=_("Is Initial Level"),
        description=_("Is this level an initial level for the school."),
        required=True,
        default=False)

    nextLevel = zope.schema.Choice(
        title=_("Next Level"),
        description=_("The next level in the school. If None, then there is "
                      "no following level."),
        vocabulary="Levels",
        required=False,
        default=None)


class ILevelContainer(container.interfaces.IContainer):
    """Container of Levels."""

    container.constraints.contains(ILevel)

    def validate(self):
        """Validate the level graphs.

        This method checks for two different types of errors:

        (1) Make sure that there is not a loop in in any of the level graphs,
            since it would prohibit students from graduating. If a loop is
            found, an ``ILevelLoopError`` is raised.

        (2) Ensure that all levels are connected in a graph. If a level is not
            connected, then it is not used at all, which is doubtly the intend
            of the manager. If disconnected levels are found, an
            ``DiscoonectedLevelsError`` will be raised.

        Both of those errors extend ``LevelValidationError`` so that other
        code can safely catch them.
        """


class ILevelContained(container.interfaces.IContained):
    """Cou contained in an ICourseContainer."""

    container.constraints.containers(ILevelContainer)


class IHistoricalRecord(zope.interface.Interface):
    """A histroical record in the academic record history.

    This is a generic interfaces that must be fulfilled for an object to be in
    the history. However, particular record obejcts might implement an
    extended version of this interface or other interface."""

    timestamp = zope.schema.Datetime(
        title=_("Time Stamp"),
        description=_("The date and time the record was created."),
        required=True)

    user = zope.schema.Id(
        title=_("User"),
        description=_("The principal id of the user making the record."),
        required=True)

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the record."),
        required=True)

    description = zope.schema.Text(
        title=_("Description"),
        description=_("A detailed description of the record."),
        required=False)


class IAcademicRecord(zope.interface.Interface):
    """An academic record of a student.

    This interface will commonly be implemented as an adapter from
    ``IPerson``.
    """

    history = zope.schema.List(
        title=_("Academic History"),
        description=_("The academic history of a student."),
        value_type=zope.schema.Object(schema=IHistoricalRecord),
        required=True)

    status = zope.schema.Choice(
        title=_("Status"),
        description=_("The current standing of the student in the school."),
        # TODO: This should become a managed vocabulary later.
        values=[_('Enrolled'), _('Graduated'), _('Withdrawn')],
        required=True,
        default=_('Enrolled'))

    levelProcess = zope.schema.Field(
        title=_("Level Process"),
        description=_("The workflow process of the level the student is "
                      "currently completing."),
        required=False)


class IManagerWorkItems(zope.interface.common.mapping.IFullMapping):
    """Provides access to the manager group's work items."""

    def addWorkItem(item):
        """Add a work item to the manager group."""

    def removeWorkItem(item):
        """Delete a work item from the manager group."""
