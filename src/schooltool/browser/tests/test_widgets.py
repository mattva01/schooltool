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

from zope.testing.doctest import DocTestSuite
from zope.interface.verify import verifyObject
from schooltool.browser.tests import RequestStub
from schooltool.tests.utils import XMLCompareMixin


class TestWidget(unittest.TestCase):

    def test(self):
        from schooltool.browser.widgets import Widget
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

    def test_with_value(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label', value=123)
        self.assertEquals(widget.value, 123)
        self.assertEquals(widget.raw_value, '123')

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

        widget.update(RequestStub())
        self.assertEquals(widget.raw_value, u'\u263B')
        self.assertEquals(widget.value, u'\u263B')
        self.assertEquals(widget.error, None)

        widget.update(RequestStub(args={'field': '\xff'}))
        self.assertEquals(widget.raw_value, u'\u263B')
        self.assertEquals(widget.value, u'\u263B')
        self.assertEquals(widget.error, "Invalid UTF-8 data.")

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
        widget.require()
        self.assertEquals(widget.error, 'This field is required.')

        widget.setRawValue('foo')
        widget.require()
        self.assert_(widget.error is None)

        widget.setRawValue(None)
        self.assert_(widget.error is None)
        widget.require()
        self.assertEquals(widget.error, 'This field is required.')

        widget = Widget('field', 'Field Label')
        self.assert_(widget.error is None)
        widget.setRawValue('')
        widget.require()
        self.assertEquals(widget.error, 'This field is required.')

        widget.setRawValue('')
        widget.error = 'Other error'
        widget.require()
        self.assertEquals(widget.error, 'Other error')

    def test_row_class(self):
        from schooltool.browser.widgets import Widget
        widget = Widget('field', 'Field Label')
        widget.error = None
        self.assertEquals(widget.row_class(), 'row')
        widget.error = 'Error!'
        self.assertEquals(widget.row_class(), 'row row_error')


class TestSequenceWidget(unittest.TestCase):

    def test_getRawValue(self):
        from schooltool.browser.widgets import SequenceWidget
        widget = SequenceWidget('field', 'Field Label')
        request = RequestStub()
        self.assertEquals(widget.getRawValue(request), None)
        request = RequestStub(args={'field': ["foo", "bar",
                                              u'\u263B'.encode('UTF-8')]})
        self.assertEquals(widget.getRawValue(request),
                          ["foo", "bar", u'\u263B'])

    def test_setRawValue(self):
        from schooltool.browser.widgets import SequenceWidget
        widget = SequenceWidget('field', 'Field Label')
        widget.setRawValue(None)
        self.assertEquals(widget.raw_value, None)
        self.assertEquals(widget.value, None)
        self.assertEquals(widget.error, None)

        widget.setRawValue(('foo', u'\u263B'))
        self.assertEquals(widget.raw_value, ['foo', u'\u263B'])
        self.assertEquals(widget.value, ['foo', u'\u263B'])
        self.assertEquals(widget.error, None)


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

    def createWidget(self, field="field", label="Label", **kw):
        from schooltool.browser.widgets import TextWidget
        widget = TextWidget(field, label, **kw)
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

    def test_call_with_formatter(self):
        widget = self.createWidget(formatter=hex)
        widget.setValue(42)
        expected = u"""
            <div class="row">
              <label for="field">Label</label>
              <input class="text" type="text" name="field" id="field"
                     value="0x2a" />
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))

    def test_call_with_error(self):
        widget = self.createWidget()
        widget.error = u"An error! \u2639"
        expected = u"""
            <div class="row row_error">
              <label for="field">Label</label>
              <input class="text" type="text" name="field" id="field" />
              <div class="error">An error! \u2639</div>
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))

    def test_call_with_everything(self):
        widget = self.createWidget(label="Length", unit="mm, > 0")
        widget.error = "Error"
        widget.css_class = "extra"
        widget.label_class = "big"
        widget.tabindex = 16
        expected = u"""
            <div class="row row_error">
              <label class="big" for="field">Length</label>
              <input class="extra" type="text" name="field" id="field"
                     tabindex="16" />
              <span class="unit">mm, &gt; 0</span>
              <div class="error">Error</div>
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))

    def test_call_with_tabindex(self):
        widget = self.createWidget()
        widget.tabindex = 16
        expected = u"""
            <div class="row">
              <label for="field">Label</label>
              <input class="text" type="text" name="field" id="field"
                     tabindex="42" />
            </div>
            """
        self.assertEqualsXML(widget(tabindex=42).encode('UTF-8'),
                             expected.encode('UTF-8'))


class TestPasswordWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self, field="field", label="Label", **kw):
        from schooltool.browser.widgets import PasswordWidget
        widget = PasswordWidget(field, label, **kw)
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        from schooltool.browser.widgets import passwordValidator
        widget = self.createWidget()
        verifyObject(IWidget, widget)
        assert widget.validator is passwordValidator

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(u'some <text>')
        expected = u"""
            <div class="row">
              <label for="field">Label</label>
              <input class="text" type="password" name="field" id="field"
                     value="some &lt;text&gt;" />
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))


class TestTextAreaWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self, field="field", label="Label"):
        from schooltool.browser.widgets import TextAreaWidget
        widget = TextAreaWidget(field, label)
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        verifyObject(IWidget, self.createWidget())

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(u'some\n<text>\n\u263B')
        expected = u"""
            <div class="row">
              <label for="field">Label</label>
              <textarea class="text" name="field" id="field">some
            &lt;text&gt;
            \u263B</textarea>
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))

    def test_call_with_everything(self):
        widget = self.createWidget()
        widget.error = u"An error! \u2639"
        widget.css_class = "extra"
        widget.tabindex = 12
        expected = u"""
            <div class="row row_error">
              <label for="field">Label</label>
              <textarea class="extra" name="field" id="field" tabindex="12">
              </textarea>
              <div class="error">An error! \u2639</div>
            </div>
            """
        self.assertEqualsXML(widget().encode('UTF-8'),
                             expected.encode('UTF-8'))


class TestSelectionWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self):
        from schooltool.browser.widgets import SelectionWidget
        widget = SelectionWidget('field', 'Label', [('a', 'Aa'), ('b', 'Bb')])
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        verifyObject(IWidget, self.createWidget())

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(u'a')
        expected = """
            <div class="row">
              <label for="field">Label</label>
              <select name="field" id="field">
                <option value="a" selected="selected">Aa</option>
                <option value="b">Bb</option>
              </select>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_call_with_everything(self):
        widget = self.createWidget()
        widget.error = u"An error!"
        widget.unit = u"(blah blah blah)"
        widget.css_class = u"extra"
        widget.tabindex = 11
        expected = """
            <div class="row row_error">
              <label for="field">Label</label>
              <select class="extra" name="field" id="field" tabindex="11">
                <option value="a">Aa</option>
                <option value="b">Bb</option>
              </select>
              <span class="unit">(blah blah blah)</span>
              <div class="error">An error!</div>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_update_nodata(self):
        widget = self.createWidget()
        request = RequestStub(args={})
        widget.update(request)
        self.assertEquals(widget.value, None)

    def test_update_data(self):
        widget = self.createWidget()
        request = RequestStub(args={'field': 'a'})
        widget.update(request)
        self.assertEquals(widget.value, 'a')


class TestMultiselectionWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self):
        from schooltool.browser.widgets import MultiselectionWidget
        widget = MultiselectionWidget('field', 'Label',
                                      [('a', 'Aa'), ('b', 'Bb'), ('c', 'Cc')])
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        verifyObject(IWidget, self.createWidget())

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(['a', 'c'])
        # FIXME: having to set this value is a bug
        widget.size = 5
        expected = """
            <div class="row">
              <label for="field">Label</label>
              <select name="field" size="5" id="field" multiple="multiple">
                <option value="a" selected="selected">Aa</option>
                <option value="b">Bb</option>
                <option value="c" selected="selected">Cc</option>
              </select>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_call_with_everything(self):
        widget = self.createWidget()
        widget.error = u"An error!"
        widget.unit = u"(blah blah blah)"
        widget.css_class = u"extra"
        widget.tabindex = 11
        widget.size = 5
        expected = """
            <div class="row row_error">
              <label for="field">Label</label>
              <select class="extra" name="field" size="5" id="field"
                      tabindex="11" multiple="multiple">
                <option value="a">Aa</option>
                <option value="b">Bb</option>
                <option value="c">Cc</option>
              </select>
              <span class="unit">(blah blah blah)</span>
              <div class="error">An error!</div>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_update_nodata(self):
        widget = self.createWidget()
        request = RequestStub(args={})
        widget.update(request)
        self.assertEquals(widget.value, None)

    def test_update_data(self):
        widget = self.createWidget()
        request = RequestStub(args={'field': 'a'})
        widget.update(request)
        self.assertEquals(widget.value, ['a'])

    def test_update_more_data(self):
        widget = self.createWidget()
        request = RequestStub(args={'field': ['a', 'b']})
        widget.update(request)
        self.assertEquals(widget.value, ['a', 'b'])


class TestMultiCheckboxWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self):
        from schooltool.browser.widgets import MultiCheckboxWidget
        widget = MultiCheckboxWidget('field', 'Label',
                                     [('a', 'Aa'), ('b', 'Bb'), ('c', 'Cc')])
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        verifyObject(IWidget, self.createWidget())

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(['a', 'c'])
        expected = """
            <div class="row">
              <label for="field">Label</label>
              <div>
                <input checked="checked" id="field_1" name="field"
                       type="checkbox" value="a"/>
                <label class="plain" for="field_1">
                  Aa
                </label>
                <input id="field_2" name="field" type="checkbox" value="b"/>
                <label class="plain" for="field_2">
                  Bb
                </label>
                <input checked="checked" id="field_3" name="field"
                       type="checkbox" value="c"/>
                <label class="plain" for="field_3">
                  Cc
                </label>
              </div>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_call_with_everything(self):
        widget = self.createWidget()
        widget.error = u"An error!"
        widget.unit = u"(blah blah blah)"
        widget.css_class = u"extra"
        widget.tabindex = 11
        expected = """
            <div class="row row_error">
              <label for="field">Label</label>
                 <div>
                   <input class="extra" id="field_1" name="field" tabindex="11"
                          type="checkbox" value="a"/>
                   <label class="plain" for="field_1">
                     Aa
                   </label>
                   <input class="extra" id="field_2" name="field" tabindex="12"
                          type="checkbox" value="b"/>
                   <label class="plain" for="field_2">
                     Bb
                   </label>
                   <input class="extra" id="field_3" name="field" tabindex="13"
                          type="checkbox" value="c"/>
                   <label class="plain" for="field_3">
                     Cc
                   </label>
                 </div>
                 <span class="unit">(blah blah blah)</span>
              <div class="error">An error!</div>
            </div>
            """
        self.assertEqualsXML(widget(), expected)


class TestCheckboxWidget(XMLCompareMixin, unittest.TestCase):

    def createWidget(self):
        from schooltool.browser.widgets import CheckboxWidget
        widget = CheckboxWidget('field', 'Label')
        return widget

    def test(self):
        from schooltool.browser.widgets import IWidget
        verifyObject(IWidget, self.createWidget())

    def test_call(self):
        widget = self.createWidget()
        widget.setValue(False)
        expected = """
            <div class="row">
              <input type="checkbox" name="field" id="field"/>
              <label class="plain" for="field">Label</label>
              <input name="field_shown" type="hidden" value="yes"/>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_call_with_everything(self):
        widget = self.createWidget()
        widget.unit = u"(blah blah blah)"
        widget.css_class = u"extra"
        widget.tabindex = 11
        widget.setValue(True)
        widget.error = u"An error!"
        expected = """
            <div class="row row_error">
              <input type="checkbox" class="extra"
                     id="field" name="field" tabindex="11" checked="checked" />
              <label class="plain" for="field">Label</label>
              <input name="field_shown" type="hidden" value="yes"/>
              <span class="unit">(blah blah blah)</span>
              <div class="error">An error!</div>
            </div>
            """
        self.assertEqualsXML(widget(), expected)

    def test_update(self):
        widget = self.createWidget()
        widget.setValue(True)
        request = RequestStub(args={'field_shown': 'yes'})
        widget.update(request)
        self.assertEquals(widget.value, False)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.browser.widgets'))
    suite.addTest(unittest.makeSuite(TestWidget))
    suite.addTest(unittest.makeSuite(TestSequenceWidget))
    suite.addTest(unittest.makeSuite(TestWidgetWithConverters))
    suite.addTest(unittest.makeSuite(TestTextWidget))
    suite.addTest(unittest.makeSuite(TestPasswordWidget))
    suite.addTest(unittest.makeSuite(TestTextAreaWidget))
    suite.addTest(unittest.makeSuite(TestSelectionWidget))
    suite.addTest(unittest.makeSuite(TestMultiselectionWidget))
    suite.addTest(unittest.makeSuite(TestMultiCheckboxWidget))
    suite.addTest(unittest.makeSuite(TestCheckboxWidget))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
