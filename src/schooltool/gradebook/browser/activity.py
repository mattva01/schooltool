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
from schooltool.app.browser import app
from schooltool.gradebook import interfaces
from schooltool.requirement import requirement
from schooltool import SchoolToolMessage as _

class ActivitiesView(object):
    """A Group Container view."""

    __used_for__ = interfaces.IActivities

    def activities(self):
        pos = 0
        for activity in self.context.values():
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
        return range(1, len(self.context)+1)

    def update(self):
        if 'DELETE' in self.request:
            for name in self.request.get('delete', []):
                del self.context[name]
        elif 'form-submitted' in self.request:
            old_pos = 0
            for activity in self.context.values():
                old_pos += 1
                name = zapi.name(activity)
                new_pos = int(self.request['pos.'+name])
                if new_pos != old_pos:
                    self.context.changePosition(name, new_pos-1)

class ActivityAddView(app.BaseAddView):
    """A view for adding an activity."""


class ActivityEditView(app.BaseEditView):
    """A view for editing activity info."""
