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
Browser views for notes.
"""

from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.app.form.browser.add import AddView

from schoolbell.app.interfaces import IHaveNotes, INotes, INote
from schoolbell.app.notes import Note

class NotesView(BrowserView):

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.notes = INotes(context)

    def notes(self):
        return self.notes


class NoteAddView(AddView):
    """A view for adding a note."""

    __used_for__ = IHaveNotes

    # Form error message for the page template
    error = None

    # Override some fields of AddView
    schema = INote
    _factory = Note
    _arguments = ['title', 'body']
    _keyword_arguments = []
    _set_before_add = []
    _set_after_add = []

    def create(self, title, body):
        note = self._factory(title=title, body=body)
        return note

    def add(self, note):
        """Add `note` to the object."""
        notes = INotes(self.context)
        notes.add(note)
        return note

    def update(self):
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

        return AddView.update(self)

    def nextURL(self):
        """See zope.app.container.interfaces.IAdding"""
        return zapi.absoluteURL(self.context, self.request)


