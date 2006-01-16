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
from schooltool.app.browser import app
from schooltool.gradebook import interfaces
from schooltool import SchoolToolMessage as _

class ActivitiesView(app.ContainerView):
    """A Group Container view."""

    __used_for__ = interfaces.IActivities

    index_title = _("Activities")
    add_title = _("Add Activity")
    add_url = "+/addActivity.html"


class ActivityAddView(app.BaseAddView):
    """A view for adding an activity."""


class ActivityEditView(app.BaseEditView):
    """A view for editing activity info."""
