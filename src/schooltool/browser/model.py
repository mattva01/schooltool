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

import datetime
import PIL.Image
from StringIO import StringIO

from schooltool.browser import View, Template
from schooltool.browser import absoluteURL
from schooltool.browser import notFoundPage
from schooltool.browser.auth import AuthenticatedAccess, ManagerAccess
from schooltool.browser.auth import PrivateAccess
from schooltool.browser.auth import isManager
from schooltool.browser.timetable import TimetableTraverseView
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects, getPath, traverse
from schooltool.interfaces import IPerson
from schooltool.interfaces import IGroup
from schooltool.membership import Membership
from schooltool.rest.infofacets import maxspect
from schooltool.translation import ugettext as _
from schooltool.uris import URIMember, URIGroup

__metaclass__ = type


class GetParentsMixin:
    """A helper for Person and Group views."""

    def getParentGroups(self, request):
        """Return groups that context is a member of."""
        return [{'url': absoluteURL(request, g), 'title': g.title}
                for g in getRelatedObjects(self.context, URIGroup)]


class PersonInfoMixin:
    """A helper for Person views."""

    def info(self):
        return FacetManager(self.context).facetByName('person_info')

    def photoURL(self):
        if self.info().photo is None:
            return u''
        else:
            return absoluteURL(self.request, self.context) + '/photo.jpg'


class PersonView(View, GetParentsMixin, PersonInfoMixin):
    """Person information view (/persons/id)."""

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/person.pt")

    def _traverse(self, name, request):
        if name == 'photo.jpg':
            return PhotoView(self.context)
        elif name == 'edit.html':
            return PersonEditView(self.context)
        elif name == 'password.html':
            return PersonPasswordView(self.context)
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        raise KeyError(name)

    def canEdit(self):
        return isManager(self.request.authenticated_user)

    def editURL(self):
        return absoluteURL(self.request, self.context) + '/edit.html'

    def canChangePassword(self):
        user = self.request.authenticated_user
        return isManager(user) or user is self.context

    def passwordURL(self):
        return absoluteURL(self.request, self.context) + '/password.html'

    def timetables(self):
        path = absoluteURL(self.request, self.context)
        keys = list(self.context.listCompositeTimetables())
        keys.sort()
        return [{'title': '%s, %s' % (period, schema),
                 'url': '%s/timetables/%s/%s' % (path, period, schema)}
                for period, schema in keys]


class PersonPasswordView(View):
    """Page for changing a person's password (/persons/id/password.html)."""

    __used_for__ = IPerson

    authorization = PrivateAccess

    template = Template('www/password.pt')

    error = None

    message = None

    def do_POST(self, request):
        old_password = request.args['old_password'][0]
        user = request.authenticated_user
        if not user.checkPassword(old_password):
            self.error = _("Incorrect password for %s." % user.title)
        else:
            if 'DISABLE' in request.args:
                self.message = _('Account disabled.')
                self.context.setPassword(None)
                request.appLog(_("Account disabled for %s (%s)") %
                               (self.context.title, getPath(self.context)))
            elif 'CHANGE' in request.args:
                new_password = request.args['new_password'][0]
                verify_password = request.args['verify_password'][0]
                if new_password != verify_password:
                    self.error = _('Passwords do not match.')
                else:
                    self.message = _('Password changed.')
                    self.context.setPassword(new_password)
                    request.appLog(_("Password changed for %s (%s)") %
                                   (self.context.title, getPath(self.context)))
        return self.do_GET(request)

    def contextURL(self):
        return absoluteURL(self.request, self.context)


class PersonEditView(View, PersonInfoMixin):
    """Page for changing information about a person (/persons/id/edit.html)."""

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

        if not dob_string:
            dob = None
        else:
            try:
                date_elements = [int(el) for el in dob_string.split('-')]
                dob = datetime.date(*date_elements)
            except (TypeError, ValueError):
                self.error = _('Invalid date')
                return self.do_GET(request)

        if photo:
            try:
                photo = self.processPhoto(photo)
            except IOError:
                self.error = _('Invalid photo')
                return self.do_GET(request)
            else:
                request.appLog(_("Photo added on %s (%s)") %
                               (self.context.title, getPath(self.context)))

        infofacet = self.info()
        infofacet.first_name = first_name
        infofacet.last_name = last_name
        infofacet.date_of_birth = dob
        infofacet.comment = comment
        if photo:
            infofacet.photo = photo

        request.appLog(_("Person info updated on %s (%s)") %
                       (self.context.title, getPath(self.context)))

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
    """Group information view (/group/id)."""

    __used_for__ = IGroup

    authorization = AuthenticatedAccess

    template = Template("www/group.pt")

    def _traverse(self, name, request):
        if name == "edit.html":
            return GroupEditView(self.context)
        raise KeyError(name)

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

    def canEdit(self):
        return isManager(self.request.authenticated_user)

    def editURL(self):
        return absoluteURL(self.request, self.context) + '/edit.html'


class GroupEditView(View):
    """Page for "editing" a Group (/group/id/edit.html)."""

    __used_for__ = IGroup

    authorization = ManagerAccess

    template = Template('www/group_edit.pt')

    def list(self, request):
        """Return a list of member data as tuples

        (type, title, path, URL)
        """
        result = [(obj.__class__.__name__, obj.title, getPath(obj),
                   absoluteURL(request, obj))
                  for obj in getRelatedObjects(self.context, URIMember)]
        result.sort()
        return result

    def addList(self, request):
        """Return a list of member data as tuples

        (type, title, path, URL)
        """
        result = []

        searchstr = request.args['SEARCH'][0].lower()
        members = getRelatedObjects(self.context, URIMember)

        for path in ('/groups', '/persons', '/resources'):
            for obj in traverse(self.context, path).itervalues():
                if (searchstr in obj.title.lower() and
                    obj not in members):
                    result.append((obj.__class__.__name__, obj.title,
                                   getPath(obj), absoluteURL(request, obj)))
        result.sort()
        return result

    def update(self, request):
        if "DELETE" in request.args:
            paths = []
            if "CHECK" in request.args:
                paths += request.args["CHECK"]
            for link in self.context.listLinks(URIMember):
                if getPath(link.traverse()) in paths:
                    link.unlink()
        if "FINISH_ADD" in request.args:
            paths = []
            if "CHECK" in request.args:
                paths += request.args["CHECK"]
            for path in paths:
                obj = traverse(self.context, path)
                Membership(group=self.context, member=obj)


class PhotoView(View):
    """View for displaying a person's photo (/persons/id/photo.jpg)."""

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    def do_GET(self, request):
        facet = FacetManager(self.context).facetByName('person_info')
        if facet.photo is None:
            return notFoundPage(request)
        else:
            request.setHeader('Content-Type', 'image/jpeg')
            return facet.photo

