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

from schooltool.browser.tests import RequestStub

__metaclass__ = type


class TestPersonInfo(unittest.TestCase):

    def test(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonInfoPage
        person = Person(title="John Doe")
        person.__name__ = 'johndoe'
        view = PersonInfoPage(person)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_('johndoe' in result)
        self.assert_('John Doe' in result)

    def test_container(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonContainerView
        container = {'person': Person()}
        view = PersonContainerView(container)
        personview = view._traverse('person', RequestStub())
        self.assertEquals(personview.__class__.__name__, 'PersonInfoPage')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfo))
    return suite


if __name__ == '__main__':
    unittest.main()
