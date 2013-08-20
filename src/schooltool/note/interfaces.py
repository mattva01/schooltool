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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Notes support interfaces
"""
import zope.interface
import zope.schema

from zope.annotation.interfaces import IAnnotatable
from schooltool.common import SchoolToolMessage as _


class IHaveNotes(IAnnotatable):
    """An object that can have Notes.

    See also INote and INotes.
    """


class INote(zope.interface.Interface):
    """A note."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the note."))

    body = zope.schema.Text(
        title=_("Body"),
        description=_("Body of the note."))

    privacy = zope.schema.Choice(
        title=_("Privacy"),
        values=('private', 'public'),
        description=u"""
        Determines who can view the note.

        Can be one of two values: 'private', 'public'

        'private'  the note can only be viewed by the creator of the note.

        'public'   anyone can view the note, including anonymous users.

        """)

    owner = zope.interface.Attribute("""Component that owns this note.""")

    unique_id = zope.schema.TextLine(
        title=u"UID",
        required=False,
        description=u"""A globally unique id for this note.""")


class INotes(zope.interface.Interface):
    """A set of notes.

    Objects that can have notes are those that have an adapter to INotes.

    See also `INote`.
    """

    def __iter__():
        """Iterate over all notes."""

    def add(note):
        """Add a new note."""

    def remove(note):
        """Remove a note.

        Raises ValueError if note is not in the set.
        """

    def clear():
        """Remove all notes."""
