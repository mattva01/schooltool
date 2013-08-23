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
Browser views for notes.
"""

from zope.publisher.browser import BrowserView
from zope.app.form.browser.add import AddView
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.note.interfaces import IHaveNotes, INotes, INote
from schooltool.note.note import Note


class NotesView(BrowserView):

    # __used_for__ = ?

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        notes = INotes(context)
        self.notes = [note for note in notes
                      if note.privacy == 'public'
                         or note.owner == request.principal.id]

        if 'DELETE_NOTE' in request:
            notes.remove(request['uid'])


class NoteAddView(AddView):
    """A view for adding a note."""

    __used_for__ = IHaveNotes

    # Form error message for the page template
    error = None

    # Override some fields of AddView
    schema = INote
    _factory = Note
    _arguments = ['title', 'body', 'privacy']
    _keyword_arguments = []
    _set_before_add = []
    _set_after_add = []

    def create(self, title, body, privacy):
        owner = self.request.principal.id
        note = self._factory(title=title, body=body, privacy=privacy,
                             owner=owner)
        return note

    def add(self, note):
        """Add `note` to the object."""
        notes = INotes(self.context)
        notes.add(note)
        return note

    def update(self):
        if 'CANCEL' in self.request:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        return AddView.update(self)

    def nextURL(self):
        """See zope.browser.interfaces.IAdding"""
        return absoluteURL(self.context, self.request)
