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
Unit tests for schooltool.rest.infofacets

$Id$
"""

import unittest
import datetime
from StringIO import StringIO
from logging import INFO
import PIL.Image
from zope.interface import directlyProvides
from zope.testing.doctestunit import DocTestSuite
from schooltool.interfaces import ILocation
from schooltool.rest.tests import RequestStub
from schooltool.rest.tests import setPath
from schooltool.tests.utils import XMLCompareMixin

__metaclass__ = type


class TestPersonInfoFacetView(unittest.TestCase, XMLCompareMixin):

    def createView(self, context=None):
        from schooltool.rest.infofacets import PersonInfoFacetView
        from schooltool.infofacets import PersonInfoFacet
        if context is None:
            context = PersonInfoFacet()
        view = PersonInfoFacetView(context)
        return view

    def test(self):
        view = self.createView()
        setPath(view.context, '/persons/007/facets/person_info')
        empty_xml = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name/>
              <last_name/>
              <date_of_birth/>
              <comment/>
              <photo xlink:type="simple" xlink:title="Photo"
                     xlink:href="/persons/007/facets/person_info/photo"/>
            </person_info>
            """
        request = RequestStub('/person/000001/facets/person_info')
        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          'text/xml; charset=UTF-8')
        self.assertEqualsXML(result, empty_xml)

    def test_put(self):
        from schooltool.infofacets import PersonInfoFacet
        from schooltool.model import Person
        body = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1">
              <first_name>John \xe2\x98\xbb</first_name>
              <last_name>Smith \xe2\x98\xbb</last_name>
              <date_of_birth>1970-04-21</date_of_birth>
              <comment>... \xe2\x98\xbb</comment>
            </person_info>
            """
        person = Person()
        setPath(person, '/persons/007')

        context = PersonInfoFacet()
        context.__parent__ = person
        context.__name__ = 'info'
        directlyProvides(context, ILocation)

        view = self.createView(context)
        view.authorization = lambda ct, rq: True
        request = RequestStub(method='PUT', body=body,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(result, "Updated")
        self.assertEquals(request.applog,
                          [(None,
                            u'Person info updated on John '
                            u'\u263b Smith \u263b (/persons/007)', INFO)])
        self.assertEquals(request.code, 200)
        self.assertEquals(context.first_name, u'John \u263B')
        self.assertEquals(context.last_name, u'Smith \u263B')
        self.assertEquals(person.title, u'John \u263B Smith \u263B')
        self.assertEquals(context.date_of_birth, datetime.date(1970, 4, 21))
        self.assertEquals(context.comment, u'... \u263B')

        body2 = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name/>
              <last_name/>
              <date_of_birth/>
              <comment/>
              <photo xlink:type="simple" xlink:title="Photo"
                     xlink:href="/persons/007/facets/person_info/photo"/>
            </person_info>
            """
        request = RequestStub(method='PUT', body=body2,
                              headers={'Content-Type': 'text/xml'})
        result = view.render(request)
        self.assertEquals(result, "Updated")
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog,
                          [(None, u'Person info updated on '
                            u'Smith \u263b (/persons/007)', INFO)])
        self.assertEquals(context.first_name, '')
        self.assertEquals(context.last_name, '')
        self.assert_(context.date_of_birth is None)
        self.assertEquals(context.comment, '')

    def test_traverse(self):
        from schooltool.infofacets import PersonInfoFacet
        from schooltool.rest.infofacets import PhotoView
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
        from schooltool.rest.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet
        context = PersonInfoFacet()
        context.photo = 'data\rdata\ndata\000and more data'
        view = PhotoView(context)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(result, context.photo)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'], 'image/jpeg')

    def test_get_no_photo(self):
        from schooltool.rest.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet
        context = PersonInfoFacet()
        view = PhotoView(context)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_put(self):
        from schooltool.rest.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet

        photo = 'P6\n1 1\n255\n\xff\xff\xff'
        ctype = "image/x-portable-pixmap"

        context = PersonInfoFacet()
        setPath(context, "/my/dog's/photo")
        context.__parent__.title = 'Fido'
        view = PhotoView(context)
        view.authorization = lambda ct, rq: True
        request = RequestStub(method='PUT', body=photo,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog,
                          [(None, 'Photo added on Fido (/)', INFO)])
        self.assert_(context.photo is not None)

    def test_put_errors(self):
        from schooltool.rest.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet

        photo = 'this is not a picture'
        ctype = "image/jpeg"

        context = PersonInfoFacet()
        setPath(context, "/my/dog's/photo")
        view = PhotoView(context)
        view.authorization = lambda ct, rq: True
        request = RequestStub(method='PUT', body=photo,
                              headers={'Content-Type': ctype})
        result = view.render(request)
        self.assertEquals(result, 'cannot identify image file')
        self.assertEquals(request.code, 400)
        self.assertEquals(request.applog, [])

    def test_delete(self):
        from schooltool.rest.infofacets import PhotoView
        from schooltool.infofacets import PersonInfoFacet
        context = PersonInfoFacet()

        context.photo = '8-)'
        setPath(context, "/my/dog's/photo")
        context.__parent__.title = 'Fido'
        view = PhotoView(context)
        view.authorization = lambda ct, rq: True
        request = RequestStub(method='DELETE')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog,
                          [(None, 'Photo removed from Fido (/)', INFO)])
        self.assert_(context.photo is None)


class TestPhotoResizing(unittest.TestCase):

    def test(self):
        from schooltool.rest.infofacets import resize_photo
        photo = 'P6\n1 1\n255\n\xff\xff\xff'
        resized = resize_photo(StringIO(photo), (2, 3))
        img = PIL.Image.open(StringIO(resized))
        self.assertEquals(img.size, (2, 2))
        self.assertEquals(img.getpixel((1, 1)), (0xff, 0xff, 0xff))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfoFacetView))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    suite.addTest(unittest.makeSuite(TestPhotoResizing))
    suite.addTest(DocTestSuite('schooltool.rest.infofacets'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
