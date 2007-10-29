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
"""Activity Views.

$Id$
"""
from zope.app import zapi
from zope.app.form.browser.editview import EditView
from zope.security.checker import canWrite

from schooltool.app.browser import app
from schooltool.gradebook import interfaces
from schooltool.person.interfaces import IPerson
from schooltool.requirement import requirement

class ActivitiesView(object):
    """A Group Container view."""

    __used_for__ = interfaces.IActivities

    @property
    def worksheets(self):
        """Get  a list of all worksheets."""
        return sorted(self.context.values(), key=lambda x: x.title)

    @property
    def currentWorksheet(self):
        return self.context.getCurrentWorksheet(self.person)
    
    def activities(self):
        pos = 0
        for activity in self.context.getCurrentActivities(self.person):
            pos += 1
            inherited = False
            if zapi.isinstance(activity, requirement.InheritedRequirement):
                inherited = True
                activity = requirement.unwrapRequirement(activity)
            yield {'name': zapi.name(activity),
                   'title': activity.title,
                   'inherited': inherited,
                   'disabled': inherited and 'disabled' or '',
                   'url': zapi.absoluteURL(activity, self.request),
                   'pos': pos}

    def positions(self):
        return range(1, len(self.currentWorksheet)+1)

    def canModify(self):
        return canWrite(self.context, 'title')

    def update(self):
        self.person = IPerson(self.request.principal)

        if 'DELETE' in self.request:
            for name in self.request.get('delete', []):
                del self.currentWorksheet[name]

        elif 'form-submitted' in self.request:
            old_pos = 0
            for activity in self.context.getCurrentActivities(self.person):
                old_pos += 1
                name = zapi.name(activity)
                if 'pos.'+name not in self.request:
                    continue
                new_pos = int(self.request['pos.'+name])
                if new_pos != old_pos:
                    self.currentWorksheet.changePosition(name, new_pos-1)
        
            """Handle change of current worksheet."""
            if 'currentWorksheet' in self.request:
                for worksheet in self.worksheets:
                    if worksheet.title == self.request['currentWorksheet']:
                        self.context.setCurrentWorksheet(self.person, worksheet)
                        break


class WorksheetAddView(app.BaseAddView):
    """A view for adding a worksheet."""


class ActivityAddView(app.BaseAddView):
    """A view for adding an activity."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context.__parent__, self.request)


class BaseEditView(EditView):
    """A base class for edit views that need special redirect."""

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            status = EditView.update(self)
            if 'UPDATE_SUBMIT' in self.request and not self.errors:
                self.request.response.redirect(self.nextURL())
            return status
            
            
class WorksheetEditView(BaseEditView):
    """A view for editing worksheet info."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.__parent__, self.request)


class ActivityEditView(BaseEditView):
    """A view for editing activity info."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.__parent__.__parent__, self.request)

