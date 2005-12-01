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
RESTive views for errors in SchoolToolApplication

$Id$
"""

from zope.interface import classImplements, implements
from zope.interface.common.interfaces import IException
from zope.app.exception.interfaces import ISystemErrorView

from schooltool.app.rest import View
from schooltool.calendar.icalendar import ICalParseError


class TextErrorView(View):
    """A base class for error views

    Sets the response status to 400 by default, that is signals a "Bad
    request" user error.
    """

    def __init__(self, context, request):
        View.__init__(self, context, request)
        request.response.setStatus(400)
        request.response.setHeader('Content-Type', 'text/plain; charset=utf-8')

    def __call__(self):
        return str(self.context)


class XMLErrorView(TextErrorView):
    """A view for IXMLErrors"""


class ICalParseErrorView(TextErrorView):

    def __call__(self):
        return 'Error parsing iCalendar data: ' + str(self.context)


class IICalParseError(IException): pass

classImplements(ICalParseError, IICalParseError)


class SystemErrorView(TextErrorView):
    """A catch-all view for programmer errors"""

    implements(ISystemErrorView)

    def isSystemError(self):
        return True

    def __call__(self):
        self.request.response.setStatus(500)
        return "A system error has occured."


class RestError(Exception):
    """A catch-all error for ReST views that should produce a 400 response."""
