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
Unit tests for schooltool.browser.model

$Id$
"""

import unittest

from schooltool.browser.tests import RequestStub, setPath

__metaclass__ = type


class TestPersonInfo(unittest.TestCase):

    def test(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonView
        person = Person(title="John Doe")
        person.__name__ = 'johndoe'
        view = PersonView(person)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('johndoe' in result)
        self.assert_('John Doe' in result)

    def test_traverse(self):
        from schooltool.model import Person
        from schooltool.browser.model import PersonView, PhotoView
        person = Person(title="John Doe")
        view = PersonView(person)
        photoview = view._traverse('photo.jpg', RequestStub())
        self.assert_(photoview.context is person)
        self.assert_(isinstance(photoview, PhotoView))
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())

    def test_photo(self):
        from schooltool.model import Person
        from schooltool.browser.model import PersonView
        from schooltool.component import FacetManager
        person = Person()
        setPath(person, '/persons/>me')
        facet = FacetManager(person).facetByName('person_info')
        facet.photo = ';-)'
        view = PersonView(person)
        markup = view.photo()
        self.assertEquals(markup, '<img src="/persons/&gt;me/photo.jpg" />')

        facet.photo = None
        markup = view.photo()
        self.assertEquals(markup, '<i>N/A</i>')


class TestPhotoView(unittest.TestCase):

    def createView(self, photo):
        from schooltool.model import Person
        from schooltool.browser.model import PhotoView
        from schooltool.component import FacetManager
        person = Person()
        facet = FacetManager(person).facetByName('person_info')
        facet.photo = photo
        return PhotoView(person)

    def test(self):
        view = self.createView(';-)')
        request = RequestStub()
        photo = view.render(request)
        self.assertEquals(request.headers['content-type'], 'image/jpeg')
        self.assertEquals(photo, ';-)')

    def test_nophoto(self):
        view = self.createView(None)
        request = RequestStub()
        self.assertRaises(ValueError, view.render, request)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfo))
    suite.addTest(unittest.makeSuite(TestPhotoView))
    return suite


if __name__ == '__main__':
    unittest.main()
