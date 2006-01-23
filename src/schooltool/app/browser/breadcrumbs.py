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
"""Custom Breadcrumbs implementation

$Id$
"""
__docformat__ = 'reStructuredText'
import zope.component
import zope.interface
import zope.publisher.interfaces.http
from zope.app import zapi
from zope.app.publisher import browser
from zope.app.traversing.interfaces import IContainmentRoot

from schooltool import SchoolToolMessage as _
from schooltool.app.browser import interfaces


class Breadcrumbs(browser.BrowserView):
    """Special Breadcrumbs implementation."""
    zope.interface.implements(interfaces.IBreadcrumbs)

    @property
    def crumbs(self):
        objects = [self.context] + list(zapi.getParents(self.context))
        objects.reverse()
        for object in objects:
            info = zapi.getMultiAdapter((object, self.request),
                                        interfaces.IBreadcrumbInfo)
            yield {'name': info.name, 'url': info.url, 'active': info.active}


class GenericBreadcrumbInfo(object):
    """A generic breadcrumb info adapter."""
    zope.interface.implements(interfaces.IBreadcrumbInfo)
    zope.component.adapts(zope.interface.Interface,
                          zope.publisher.interfaces.http.IHTTPRequest)

    # See interfaces.IBreadcrumbInfo
    active = True

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def name(self):
        """See interfaces.IBreadcrumbInfo"""
        name = getattr(self.context, 'title', None)
        if name is None:
            name = getattr(self.context, '__name__', None)
        if name is None and IContainmentRoot.providedBy(self.context):
            name = _('top')
        return name

    @property
    def url(self):
        """See interfaces.IBreadcrumbInfo"""
        return zapi.absoluteURL(self.context, self.request)


def CustomNameBreadCrumbInfo(name):
    return type('CustomNameBreadCrumbInfo(%r)' %name,
                (GenericBreadcrumbInfo,), {'name': name})
