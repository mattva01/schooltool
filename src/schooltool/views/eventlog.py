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
Views for schooltool.eventlog.

$Id$
"""

from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.component import registerView
from schooltool.views import View, Template, textErrorPage
from schooltool.views.facet import FacetView
from schooltool.views.auth import SystemAccess
from schooltool.eventlog import IEventLog, IEventLogUtility, IEventLogFacet
from schooltool.translation import _

__metaclass__ = type


moduleProvides(IModuleSetup)


class EventLogView(View):
    """View for EventLogFacet."""

    template = Template("www/eventlog.pt", content_type="text/xml")
    authorization = SystemAccess

    def items(self):
        return [{'timestamp': ts.isoformat(' '), 'event': event}
                for ts, event in self.context.getReceived()]

    def do_PUT(self, request):
        # XXX RFC 2616, section 9.6:
        #   The recipient of the entity MUST NOT ignore any Content-* (e.g.
        #   Content-Range) headers that it does not understand or implement
        #   and MUST return a 501 (Not Implemented) response in such cases.
        if request.content.read(1):
            return textErrorPage(request, _("Only PUT with an empty body"
                                            " is defined for event logs"))
        n = len(self.context.getReceived())
        self.context.clear()
        request.setHeader('Content-Type', 'text/plain')
        if n == 1:
            return _("1 event cleared")
        else:
            return _("%d events cleared") % n


class EventLogFacetView(EventLogView, FacetView):
    """A view for IEventLogFacet."""


def setUp():
    """See IModuleSetup."""
    registerView(IEventLog, EventLogView)
    registerView(IEventLogUtility, EventLogView)
    registerView(IEventLogFacet, EventLogFacetView)

