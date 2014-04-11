#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Report Tests
"""
import unittest
from textwrap import dedent

from schooltool.skin.flourish.report import buildHTMLParagraphs
from schooltool.testing.util import NiceDiffsMixin


class TestBuildHTMLParagraphs(NiceDiffsMixin, unittest.TestCase):

    def test_p(self):
        snippet = 'Text'
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['Text'])
        snippet = '''<p>One paragraph</p>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One paragraph'])
        snippet = '''<p>One paragraph</p><p> </p>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One paragraph'])
        snippet = dedent('''
            <p>One paragraph</p>
            <p>Another paragraph</p>''')
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One paragraph',
                          'Another paragraph'])

    def test_br(self):
        snippet = dedent('''
            <p>One paragraph<br/>Another line</p>''')
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One paragraph',
                          'Another line'])
        snippet = '''<p>One paragraph<br>    <br></p>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One paragraph'])

    def test_entities(self):
        snippet = '''<p>One &amp; Two</p>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One &amp; Two'])
        snippet = '''<p>One&nbsp;&lt;&nbsp;Two</p>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One &lt; Two'])
        snippet = '''<p>One &lt; <strong>Two</strong></p>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['One &lt; <strong>Two</strong>'])

    def test_bold_italic(self):
        snippet = '''<b>Bold</b> or <i>Italic</i>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['<b>Bold</b> or <i>Italic</i>'])
        snippet = '''<strong>Bold</strong> or <em>Italic</em>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['<strong>Bold</strong> or <em>Italic</em>'])

    def test_other_tags(self):
        snippet = '''<ul><li>One</li><li>Two</li></ul>'''
        self.assertEqual(buildHTMLParagraphs(snippet),
                         ['&lt;ul&gt;&lt;li&gt;One&lt;/li&gt;&lt;li&gt;Two&lt;/li&gt;&lt;/ul&gt;'])


if __name__ == '__main__':
    unittest.main()
