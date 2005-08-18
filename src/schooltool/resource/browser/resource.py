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
group views.

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.app import zapi
from zope.app.publisher.browser import BrowserView

from schooltool import SchoolToolMessageID as _
from schooltool.batching import Batch
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.browser.app import ContainerView, BaseAddView, BaseEditView

from schooltool.resource.interfaces import IResourceContainer
from schooltool.resource.interfaces import IResourceContained


class ResourceContainerView(ContainerView):
    """A Resource Container view."""

    __used_for__ = IResourceContainer

    index_title = _("Resource index")
    add_title = _("Add a new resource")
    add_url = "+/addSchoolBellResource.html"


class ResourceView(BrowserView):
    """A Resource info view."""

    __used_for__ = IResourceContained


class ResourceAddView(BaseAddView):
    """A view for adding a resource."""


class ResourceEditView(BaseEditView):
    """A view for editing resource info."""

    __used_for__ = IResourceContained
