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

import libxml2
import PIL.Image
from cStringIO import StringIO
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IPersonInfoFacet
from schooltool.component import registerView
from schooltool.views import View, Template
from schooltool.views import notFoundPage, textErrorPage
from schooltool.views import absolutePath
from schooltool.views.facet import FacetView
from schooltool.views.auth import PublicAccess
from schooltool.common import parse_date, to_unicode
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


class PersonInfoFacetView(FacetView):

    template = Template("www/infofacets.pt", content_type="text/xml")
    authorization = PublicAccess

    schema = """<?xml version="1.0" encoding="UTF-8"?>
        <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 ns="http://schooltool.org/ns/model/0.1"
                 datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
          <start>
            <element name="person_info">
              <element name="first_name"><text/></element>
              <element name="last_name"><text/></element>
              <element name="date_of_birth"><text/></element>
              <element name="comment"><text/></element>
              <optional>
                <element name="photo">
                  <attribute name="xlink:type">
                    <value>simple</value>
                  </attribute>
                  <attribute name="xlink:href">
                    <data type="anyURI"/>
                  </attribute>
                  <optional>
                    <attribute name="xlink:title">
                      <text/>
                    </attribute>
                  </optional>
                </element>
              </optional>
            </element>
          </start>
        </grammar>
    """

    def photo_href(self):
        return absolutePath(self.request, self.context, 'photo')

    def _traverse(self, name, request):
        if name == 'photo':
            return PhotoView(self.context)
        else:
            return FacetView._traverse(self, name, request)

    def do_PUT(self, request):
        xml = request.content.read()
        try:
            if not validate_against_schema(self.schema, xml):
                return textErrorPage(request,
                            _("XML not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request, _("Invalid XML"))
        doc = libxml2.parseDoc(xml)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/model/0.1'
            xpathctx.xpathRegisterNs('st', ns)

            def extract(attr):
                node = xpathctx.xpathEval('/st:person_info/st:%s' % attr)[0]
                return to_unicode(node.content).strip()

            self.context.first_name = extract('first_name')
            self.context.last_name = extract('last_name')
            self.context.comment = extract('comment')
            date_of_birth = extract('date_of_birth')
            if date_of_birth:
                try:
                    self.context.date_of_birth = parse_date(date_of_birth)
                except ValueError, e:
                    return textErrorPage(request, str(e))
            else:
                self.context.date_of_birth = None
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()
        path = absolutePath(request, self.context)
        request.site.logAppEvent(request.authenticated_user,
                                 "Facet updated: %s" % path)
        request.setHeader('Content-Type', 'text/plain')
        return _("Updated")


class PhotoView(View):

    authorization = PublicAccess

    canonical_photo_size = (240, 240)

    def do_GET(self, request):
        if self.context.photo is None:
            return notFoundPage(request)
        else:
            request.setHeader('Content-Type', 'image/jpeg')
            return self.context.photo

    def do_PUT(self, request):
        try:
            img = PIL.Image.open(request.content)
        except IOError, e:
            return textErrorPage(request, str(e))
        size = maxspect(img.size, self.canonical_photo_size)
        img2 = img.resize(size, PIL.Image.ANTIALIAS)
        buf = StringIO()
        img2.save(buf, 'JPEG')
        self.context.photo = buf.getvalue()
        path = absolutePath(request, self.context)
        request.site.logAppEvent(request.authenticated_user,
                                 "Photo added: %s" % path)
        request.setHeader('Content-Type', 'text/plain')
        return _("Photo added")

    def do_DELETE(self, request):
        self.context.photo = None
        path = absolutePath(request, self.context)
        request.site.logAppEvent(request.authenticated_user,
                                 "Photo removed: %s" % path)
        request.setHeader('Content-Type', 'text/plain')
        return _("Photo removed")


def maxspect(size, limits):
    """Returns the maximized image size maintaining aspect.

    If size == (orig_w, orig_h) and limits == (limit_w, limit_h), then
    (w, h) = maxspect(size, limits) will have the following properties:

      w <= limit_w and h <= limit_h
      w == limit_w or h == limit_h
      w / h = orig_w / orig_h (or, more correctly, w * orig_h = h * orig_w)

    >>> maxspect((1, 2), (100, 100))
    (50, 100)
    >>> maxspect((2, 1), (100, 100))
    (100, 50)
    >>> maxspect((4, 3), (640, 480))
    (640, 480)
    >>> maxspect((1280, 1024), (640, 480))
    (600, 480)
    """
    orig_w, orig_h = size
    limit_w, limit_h = limits
    assert orig_w > 0
    assert orig_h > 0
    assert limit_w > 0
    assert limit_h > 0
    if limit_w * orig_h <= limit_h * orig_w:
        return (limit_w, limit_w * orig_h / orig_w)
    else:
        return (limit_h * orig_w / orig_h, limit_h)


def setUp():
    """See IModuleSetup."""
    registerView(IPersonInfoFacet, PersonInfoFacetView)

