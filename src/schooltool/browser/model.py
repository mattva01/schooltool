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
from schooltool.browser import absoluteURL
from schooltool.browser.auth import AuthenticatedAccess, ManagerAccess
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects
from schooltool.interfaces import IPerson
from schooltool.interfaces import IGroup
from schooltool.uris import URIMember, URIGroup


__metaclass__ = type


class GetParentsMixin:
    """A helper for Person and Group views."""

    def getParentGroups(self, request):
        """Return groups that context is a member of."""
        return [{'url': absoluteURL(request, g), 'title': g.title}
                for g in getRelatedObjects(self.context, URIGroup)]


class PersonView(View, GetParentsMixin):

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/person.pt")

    def _traverse(self, name, request):
        if name == 'photo.jpg':
            return PhotoView(self.context)
        elif name == 'edit.html':
            return PersonEditView(self.context)
        raise KeyError(name)

    def info(self):
        return FacetManager(self.context).facetByName('person_info')

    def photo(self):
        # TODO: change to return just the path and refactor into PersonBaseView
        if self.info().photo is None:
            return u'<i>N/A</i>' # XXX Should this be translated?
        else:
            path = absoluteURL(self.request, self.context)
            return '<img src="%s/photo.jpg" />' % cgi.escape(path)


class PersonEditView(View):

    __used_for__ = IPerson

    authorization = ManagerAccess

    template = Template('www/person_edit.pt')

    def info(self):
        return FacetManager(self.context).facetByName('person_info')

    def do_POST(self, request):
        first_name = request.args['first_name'][0]
        last_name = request.args['last_name'][0]
        comment = request.args['comment'][0]
        photo = request.args['photo'][0]

        infofacet = self.info()
        infofacet.first_name = first_name
        infofacet.last_name = last_name
        infofacet.comment = comment
        if photo:
            infofacet.photo = photo

        url = absoluteURL(request, self.context)
        return self.redirect(url, request)


class GroupView(View, GetParentsMixin):

    __used_for__ = IGroup

    authorization = AuthenticatedAccess

    template = Template("www/group.pt")

    def getOtherMembers(self, request):
        """Return members that are not groups."""
        return [{'url': absoluteURL(request, g), 'title': g.title}
                for g in getRelatedObjects(self.context, URIMember)
                if not IGroup.providedBy(g)]

    def getSubGroups(self, request):
        """Return members that are groups."""
        return [{'url': absoluteURL(request, g), 'title': g.title}
                for g in getRelatedObjects(self.context, URIMember)
                if IGroup.providedBy(g)]


class PhotoView(View):

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    def do_GET(self, request):
        facet = FacetManager(self.context).facetByName('person_info')
        if facet.photo is None:
            raise ValueError('Photo not available')
        request.setHeader('Content-Type', 'image/jpeg')
        return facet.photo
