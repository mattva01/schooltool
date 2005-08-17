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
course browser views.

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.app.publisher.browser import BrowserView
from schoolbell.app.browser.app import ContainerView

from schooltool import SchoolToolMessageID as _
from schooltool.course.interfaces import ICourse, ICourseContainer

class CourseContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ICourseContainer

    index_title = _("Course index")
    add_title = _("Add a new course")
    add_url = "+/addSchoolToolCourse.html"


class CourseView(BrowserView):
    """A view for courses."""

    __used_for__ = ICourse


class CourseAddView(AddView):
    """A view for adding Courses."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)

