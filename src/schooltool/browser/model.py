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
import datetime
import PIL.Image
from StringIO import StringIO

from schooltool.browser import View, Template
from schooltool.browser import absoluteURL
from schooltool.browser.auth import AuthenticatedAccess, ManagerAccess
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects
from schooltool.interfaces import IPerson
from schooltool.interfaces import IGroup
from schooltool.rest.infofacets import maxspect
from schooltool.uris import URIMember, URIGroup

__metaclass__ = type


class GetParentsMixin:
    """A helper for Person and Group views."""

    def getParentGroups(self, request):
        """Return groups that context is a member of."""
        return [{'url': absoluteURL(request, g), 'title': g.title}
                for g in getRelatedObjects(self.context, URIGroup)]


class PersonInfoMixin:

    def info(self):
        return FacetManager(self.context).facetByName('person_info')

    def photoURL(self):
        if self.info().photo is None:
            return u''
        else:
            path = absoluteURL(self.request, self.context) + '/photo.jpg'
            return cgi.escape(path)


class PersonView(View, GetParentsMixin, PersonInfoMixin):

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/person.pt")

    def _traverse(self, name, request):
        if name == 'photo.jpg':
            return PhotoView(self.context)
        elif name == 'edit.html':
            return PersonEditView(self.context)
        raise KeyError(name)



class PersonEditView(View, PersonInfoMixin):

    __used_for__ = IPerson

    authorization = ManagerAccess

    template = Template('www/person_edit.pt')

    error = None

    canonical_photo_size = (240, 240)

    def do_POST(self, request):
        first_name = unicode(request.args['first_name'][0], 'utf-8')
        last_name = unicode(request.args['last_name'][0], 'utf-8')
        dob_string = request.args['date_of_birth'][0]
        comment = unicode(request.args['comment'][0], 'utf-8')
        photo = request.args['photo'][0]

        try:
            date_elements = [int(el) for el in dob_string.split('-')]
            dob = datetime.date(*date_elements)
        except (TypeError, ValueError):
            self.error = 'Invalid date'
            return self.do_GET(request)

        if photo:
            try:
                photo = self.processPhoto(photo)
            except IOError:
                self.error = 'Invalid photo'
                return self.do_GET(request)

        infofacet = self.info()
        infofacet.first_name = first_name
        infofacet.last_name = last_name
        infofacet.date_of_birth = dob
        infofacet.comment = comment
        if photo:
            infofacet.photo = photo

        url = absoluteURL(request, self.context)
        return self.redirect(url, request)

    def processPhoto(self, photo):
        # XXX The code has been copy&pasted from
        #     schooltool.rest.infofacets.PhotoView.do_PUT().
        #     It does not have tests.
        photo_file = StringIO(photo)
        img = PIL.Image.open(photo_file)
        size = maxspect(img.size, self.canonical_photo_size)
        img2 = img.resize(size, PIL.Image.ANTIALIAS)
        buf = StringIO()
        img2.save(buf, 'JPEG')
        return buf.getvalue()


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
