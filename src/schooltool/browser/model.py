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
Web-application views for the schooltool.model objects.

$Id$
"""

import cgi

from schooltool.browser import View, Template
from schooltool.component import FacetManager
from schooltool.interfaces import IPerson
from schooltool.views import absolutePath

__metaclass__ = type


class PersonView(View):

    __used_for__ = IPerson

    template = Template("www/person.pt")

    def _traverse(self, name, request):
        if name == 'photo.jpg':
            return PhotoView(self.context)
        raise KeyError(name)

    def photo(self):
        try:
            facet = FacetManager(self.context).facetByName('person_info')
            if facet.photo is None:
                raise KeyError
            else:
                path = absolutePath(self.request, self.context)
                return '<img src="%s/photo.jpg" />' % cgi.escape(path)
        except KeyError:
            return u'<i>N/A</i>' # XXX Should this be translated?


class PhotoView(View):

    __used_for__ = IPerson

    def do_GET(self, request):
        facet = FacetManager(self.context).facetByName('person_info')
        if facet.photo is None:
            raise ValueError('Photo not available')
        request.setHeader('Content-Type', 'image/jpeg')
        return facet.photo
