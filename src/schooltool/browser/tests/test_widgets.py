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
Unit tests for schooltool.browser.timetable

$Id$
"""

import unittest
import datetime

from zope.testing.doctestunit import DocTestSuite
from zope.interface.verify import verifyObject
from schooltool.browser.tests import RequestStub
from schooltool.tests.utils import XMLCompareMixin


class TestWidget(unittest.TestCase):

    def test(self):
        from schooltool.browser.widgets import Widget
        from schooltool.browser.widgets import defaultParser
        from schooltool.browser.widgets import defaultFormatter
        from schooltool.browser.widgets import defaultValidator
        widget = Widget('field', 'Field Label')
        self.assertEquals(widget.name, 'field')
        self.assertEquals(widget.label, 'Field Label')
        self.assertEquals(widget.parser(None), None)
        self.assertEquals(widget.parser('foo'), 'foo')
        self.assertEquals(widget.formatter(None), None)
        self.assertEquals(widget.formatter('foo'), 'foo')
        self.assertEquals(widget.formatter(123), '123')
        widget.validator(None)
        widget.validator('foo')
        widget.validator(123)

    def test_getRawValue(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label')
        request = RequestStub()
        self.assertEquals(widget.getRawValue(request), None)
        request = RequestStub(args={'field': u'\u263B'.encode('UTF-8')})
        self.assertEquals(widget.getRawValue(request), u'\u263B')

    def test_update(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label')
        widget.update(RequestStub())
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, None)

        widget.update(RequestStub(args={'field': u'\u263B'.encode('UTF-8')}))
        self.assertEquals(widget.raw_value, u'\u263B')
        self.assertEquals(widget.value, u'\u263B')
        self.assertEquals(widget.error, None)

    def test_setRawValue(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label')
        widget.setRawValue(None)
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, None)

        widget.setRawValue(u'\u263B')
        self.assertEquals(widget.raw_value, u'\u263B')
        self.assertEquals(widget.value, u'\u263B')
        self.assertEquals(widget.error, None)

    def test_setValue(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label')
        widget.setValue(None)
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, None)

        widget.setValue(u'\u263B')
        self.assertEquals(widget.raw_value, u'\u263B')
        self.assertEquals(widget.value, u'\u263B')
        self.assertEquals(widget.error, None)

    def test_require(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label')
        widget.setRawValue('foo')
        widget.require()
        self.assert_(widget.error is None)

        widget.setRawValue(None)
        self.assert_(widget.error is None)
        widget.require()
        self.assertEquals(widget.error, 'This field is required.')


class TestWidgetWithConverters(unittest.TestCase):

    def parser(self, value):
        if value is None:
            return None
        return int(value, 16)

    def validator(self, value):
        if value is not None and value < 0:
            raise ValueError(u'negative value \u2639')

    def formatter(self, value):
        if value is None:
            return None
        return hex(value)

    def createWidget(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label',
                        self.parser, self.validator, self.formatter)
        return widget

    def test_setRawValue(self):
        widget = self.createWidget()
        widget.setRawValue(' 0x12AB ')
        self.assertEquals(widget.raw_value, '0x12ab')
        self.assertEquals(widget.value, 0x12AB)
        self.assertEquals(widget.error, None)

        widget.setRawValue(None)
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, None)

        widget.setRawValue(' xyz ')
        self.assertEquals(widget.raw_value, ' xyz ')
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, "invalid literal for int(): xyz ")

        widget.setRawValue(' -12 ')
        self.assertEquals(widget.raw_value, ' -12 ')
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, u"negative value \u2639")

    def test_setValue(self):
        widget = self.createWidget()
        widget.setValue(0x12AB)
        self.assertEquals(widget.raw_value, '0x12ab')
        self.assertEquals(widget.value, 0x12AB)
        self.assertEquals(widget.error, None)

        widget.setValue(None)
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, None)

        widget.setValue(-12)
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, -12)
        self.assertEquals(widget.error, u"negative value \u2639")


class TestTextWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self):
        from schooltool.browser.widgets import TextWidget
        widget = TextWidget('field', 'Label')
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        verifyObject(IWidget, self.createWidget())

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(u'some <text> \u263B')
        expected = u"""
            <div class="row">
              <label for="field">Label</label>
              <input class="text" type="text" name="field" id="field"
                     value="some &lt;text&gt; \u263B" />
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.browser.widgets'))
    suite.addTest(unittest.makeSuite(TestWidget))
    suite.addTest(unittest.makeSuite(TestWidgetWithConverters))
    suite.addTest(unittest.makeSuite(TestTextWidget))
    return suite


if __name__ == '__main__':
    unittest.main()
