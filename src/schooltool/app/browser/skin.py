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
SchoolBell skin.

$Id: skin.py 3335 2005-03-25 18:53:11Z ignas $
"""
import os
import sys

from zope.interface import Interface
from zope.publisher.interfaces.browser import ILayer, IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.app.publisher.browser import applySkin
from zope.app.traversing import api
from zope.app.viewlet import viewlet

from schooltool.app.interfaces import ISchoolToolApplication


class ResourceViewletBase(object):

    _path = None

    def getFileURL(self):
        resource = api.traverse(self.context, '++resource++' + self._path,
                                request=self.request)
        return resource()

    def __call__(self, *args, **kw):
        return self.index(*args, **kw)


def JavaScriptViewlet(path):
    """Create a viewlet that can simply insert a javascript link."""
    src = os.path.join(os.path.dirname(__file__), 'templates',
                       'javascript_viewlet.pt')

    klass = type('JavaScriptViewlet',
                 (ResourceViewletBase, viewlet.SimpleViewlet),
                  {'index': viewlet.ViewletPageTemplateFile(src),
                   '_path': path})

    return klass


def CSSViewlet(path):
    """Create a viewlet that can simply insert a javascript link."""
    src = os.path.join(os.path.dirname(__file__), 'templates',
                       'css_viewlet.pt')

    klass = type('JavaScriptViewlet',
                 (ResourceViewletBase, viewlet.SimpleViewlet),
                  {'index': viewlet.ViewletPageTemplateFile(src),
                   '_path': path})

    return klass


class JavaScriptRegion(Interface):
    """Provides a viewlet hook for the javascript link entries."""


class CSSRegion(Interface):
    """Provides a viewlet hook for the CSS link entries."""


class HeaderRegion(Interface):
    """Provides a viewlet hook for the header of a page."""


class ISchoolToolLayer(ILayer, IBrowserRequest):
    """SchoolTool layer."""


class ISchoolToolSkin(ISchoolToolLayer, IDefaultBrowserLayer):
    """The SchoolTool skin"""


def schoolToolTraverseSubscriber(event):
    """A subscriber to BeforeTraverseEvent.

    Sets the SchoolBell skin if the object traversed is a SchoolBell
    application instance.
    """
    if (ISchoolToolApplication.providedBy(event.object) and
        IBrowserRequest.providedBy(event.request)):
        applySkin(event.request, ISchoolToolSkin)
