#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
The views for the schooltool.model objects.

$Id$
"""

from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IGroup, IPerson, IResource
from schooltool.uris import URIMember, URIGroup
from schooltool.component import registerView
from schooltool.component import getRelatedObjects
from schooltool.component import FacetManager
from schooltool.component import getPath
from schooltool.views import View, Template
from schooltool.views import notFoundPage
from schooltool.views import absolutePath
from schooltool.views.relationship import RelationshipsView
from schooltool.views.facet import FacetManagementView
from schooltool.views.timetable import TimetableTraverseView
from schooltool.views.timetable import CompositeTimetableTraverseView
from schooltool.views.cal import CalendarView, CalendarReadView, BookingView
from schooltool.views.absence import RollCallView, AbsenceManagementView
from schooltool.views.auth import PublicAccess, PrivateAccess
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


class ApplicationObjectTraverserView(View):
    """A view that supports traversing to facets and relationships etc."""

    def href(self):
        return absolutePath(self.request, self.context)

    def _traverse(self, name, request):
        if name == 'facets':
            return FacetManagementView(FacetManager(self.context))
        elif name == 'relationships':
            return RelationshipsView(self.context)
        elif name == 'calendar':
            return CalendarView(self.context.calendar)
        elif name == 'timetable-calendar':
            return CalendarReadView(self.context.makeCalendar())
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        elif name == 'composite-timetables':
            return CompositeTimetableTraverseView(self.context)
        raise KeyError(name)


class GroupView(ApplicationObjectTraverserView):
    """The view for a group"""

    template = Template("www/group.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        if name == 'rollcall':
            return RollCallView(self.context)
        elif name == 'tree':
            return TreeView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)

    def listItems(self):
        for item in getRelatedObjects(self.context, URIMember):
            yield {'title': item.title,
                   'href': absolutePath(self.request, item)}


class TreeView(View):

    template = Template('www/tree.pt', content_type='text/xml')
    node_template = Template('www/tree_node.pt',
                             content_type=None, charset=None)
    authorization = PublicAccess

    def generate(self, node):
        children = [child for child in getRelatedObjects(node, URIMember)
                    if IGroup.providedBy(child)]
        res = self.node_template(self.request, title=node.title,
                             href=absolutePath(self.request, node),
                             children=children, generate=self.generate)
        return res.strip().replace('\n', '\n  ')


class PersonView(ApplicationObjectTraverserView):
    """The view for a person object"""

    template = Template("www/person.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        if name == 'absences':
            return AbsenceManagementView(self.context)
        if name == 'password':
            return PersonPasswordView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)

    def getGroups(self):
        return [{'title': group.title,
                 'href': absolutePath(self.request, group)}
                for group in getRelatedObjects(self.context, URIGroup)]


class PersonPasswordView(View):

    do_GET = staticmethod(notFoundPage)
    authorization = PrivateAccess

    def do_PUT(self, request):
        password = request.content.read()
        password = password.strip()
        self.context.setPassword(password)
        path = getPath(self.context)
        request.site.logAppEvent(request.authenticated_user,
                "Password changed for %s (%s)" % (path, self.context.title))
        request.setHeader('Content-Type', 'text/plain')
        return _("Password changed")

    def do_DELETE(self, request):
        self.context.setPassword(None)
        path = getPath(self.context)
        request.site.logAppEvent(request.authenticated_user,
                "Account disabled for %s (%s)" % (path, self.context.title))
        request.setHeader('Content-Type', 'text/plain')
        return _("Account disabled")


class ResourceView(ApplicationObjectTraverserView):
    """A view on a resource"""

    template = Template("www/resource.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        if name == 'timetables':
            return TimetableTraverseView(self.context, readonly=True)
        if name == 'booking':
            return BookingView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(IPerson, PersonView)
    registerView(IGroup, GroupView)
    registerView(IResource, ResourceView)
