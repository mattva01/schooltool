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
Views for facets.

$Id$
"""

from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IPersonInfoFacet
from schooltool.component import registerView
from schooltool.views import Template
from schooltool.views.facet import FacetView
from schooltool.views.auth import PublicAccess

__metaclass__ = type


moduleProvides(IModuleSetup)


class PersonInfoFacetView(FacetView):

    template = Template("www/infofacets.pt", content_type="text/xml")
    authorization = PublicAccess


def setUp():
    """See IModuleSetup."""
    registerView(IPersonInfoFacet, PersonInfoFacetView)

