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
Unit tests for schooltool.views.infofacets

$Id$
"""

import unittest
from zope.testing.doctestunit import DocTestSuite
from schooltool.views.tests import RequestStub
from schooltool.tests.utils import XMLCompareMixin

__metaclass__ = type


class TestPersonInfoFacetView(unittest.TestCase, XMLCompareMixin):

    def createView(self, context=None):
        from schooltool.views.infofacets import PersonInfoFacetView
        from schooltool.infofacets import PersonInfoFacet
        if context is None:
            context = PersonInfoFacet()
        view = PersonInfoFacetView(context)
        return view

    def test(self):
        view = self.createView()
        empty_xml = """
            <facet active="active" owned="unowned">
              <class>PersonInfoFacet</class>
              <name></name>
            </facet>
            """
        request = RequestStub('/person/000001/facets/person_info')
        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'],
                          'text/xml; charset=UTF-8')
        self.assertEqualsXML(result, empty_xml)

    def test_traverse(self):
        from schooltool.infofacets import PersonInfoFacet
        from schooltool.views.infofacets import PhotoView
        context = PersonInfoFacet()
        context.photo = "[pretend that this is JPEG data]"
        view = self.createView(context)
        request = RequestStub()
        view2 = view._traverse('photo', request)
        self.assert_(isinstance(view2, PhotoView))
        result = view2.render(request)
        self.assertEquals(result, context.photo)


class TestPhotoView(unittest.TestCase):

    def test_get(self):
        from schooltool.views.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet
        context = PersonInfoFacet()
        context.photo = 'data\rdata\ndata\000and more data'
        view = PhotoView(context)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(result, context.photo)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], 'image/jpeg')

    def test_get_no_photo(self):
        from schooltool.views.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet
        context = PersonInfoFacet()
        view = PhotoView(context)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        from schooltool.views.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet

        photo = 'P6\n1 1\n255\n\xff\xff\xff'
        ctype = "image/jpeg"

        context = PersonInfoFacet()
        view = PhotoView(context)
        view.authorization = lambda ct, rq: True
        request = RequestStub(method='PUT', body=photo,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_(context.photo is not None)

    def test_delete(self):
        from schooltool.views.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet
        context = PersonInfoFacet()
        context.photo = '8-)'
        view = PhotoView(context)
        view.authorization = lambda ct, rq: True
        request = RequestStub(method='DELETE')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assert_(context.photo is None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfoFacetView))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    suite.addTest(DocTestSuite('schooltool.views.infofacets'))
    return suite

if __name__ == '__main__':
    unittest.main()
