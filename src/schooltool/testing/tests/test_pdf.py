#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Tests for pdf testing helpers.
"""

import unittest
import doctest

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import units
from reportlab import platypus


def buildTableFlowable():
    para_style = ParagraphStyle(name='Test', fontName='Times-Roman')

    data = [
        ['text',
         platypus.paragraph.Paragraph('Text', para_style)],
        [['several', 'items in a cell'],
         platypus.flowables.Image('table_img.png')],
    ]
    return platypus.tables.Table(data)


def buildNestedTables():
    data = [
        ['A table with another table inside!'],
        [buildTableFlowable()]]
    return platypus.tables.LongTable(data)


def buildTestStory():
    para_style = ParagraphStyle(name='Test', fontName='Times-Roman')

    flowables = []
    flowables.append('Some\ntext')

    flowables.append(
        platypus.flowables.KeepInFrame(
            units.inch*2, units.inch, content=[
                platypus.paragraph.Paragraph('Single line', para_style),
                u'unicode text']))
    flowables.append(
        platypus.xpreformatted.PythonPreformatted('print "foo"',
                                                  para_style, bulletText='*'))
    flowables.append(
        platypus.flowables.KeepTogether([
            platypus.paragraph.Paragraph(
                'Multi &amp;\n<b>Line</b>', para_style),
            platypus.xpreformatted.XPreformatted(
                'Text', para_style, bulletText='*'),
            ],
            maxHeight=units.inch))

    flowables.extend([
        platypus.flowables.HRFlowable(),
        platypus.flowables.Image('logo.png', height=units.inch),
        platypus.flowables.ParagraphAndImage(
            platypus.paragraph.Paragraph('Text', para_style),
            platypus.flowables.Image('file.png'),
            xpad=units.inch),
        ])

    flowables.extend([
        platypus.flowables.PageBreak(),
        platypus.flowables.SlowPageBreak(),
        platypus.flowables.CondPageBreak(height=units.inch*2),
        platypus.flowables.Spacer(units.inch*3, units.inch),
        ])

    flowables.append(platypus.flowables.AnchorFlowable('My anchor'))

    # also add some uninteresting flowables
    flowables.append(platypus.flowables.UseUpSpace())
    flowables.append(platypus.flowables.Macro('print "foo"'))

    flowables.append(buildNestedTables())
    return flowables


def doctest_StoryXML():
    r"""Tests for StoryXML document building and printing

        >>> story = buildTestStory()

    StoryXML builds an XML element tree with some some basic flowable
    parameters.

        >>> from schooltool.testing.pdf import StoryXML
        >>> parser = StoryXML(story)

    The XML document can be accessed directly:

        >>> parser.document
        <...ElementTree object ...>

    StoryXML.printXML prints the XML tree.

        >>> parser.printXML()
        <story>
          Some
          text
          <KeepInFrame>
            <Paragraph>Single line</Paragraph>
            unicode text
          </KeepInFrame>
          <PythonPreformatted bulletText="*">print "foo"</PythonPreformatted>
          <KeepTogether>
            <Paragraph>Multi &amp; Line</Paragraph>
            <XPreformatted bulletText="*">Text</XPreformatted>
          </KeepTogether>
          <HRFlowable width="80%" lineWidth="1"
                      spaceBefore="1" spaceAfter="1"
                      hAlign="CENTER" vAlign="BOTTOM"/>
          <Image filename="logo.png" width="None" height="72.0"/>
          <ParagraphAndImage xpad="72.0" ypad="3">
            <Image filename="file.png" width="None" height="None"/>
            <Paragraph>Text</Paragraph>
          </ParagraphAndImage>
          <PageBreak/>
          <SlowPageBreak/>
          <CondPageBreak height="144.0"/>
          <Spacer width="216.0" height="72.0"/>
          <AnchorFlowable name="My anchor"/>
          <LongTable>
          <tr>
            <td>A table with another table inside!</td>
          </tr>
          <tr>
            <td><Table>
              <tr>
                <td>text</td>
                <td><Paragraph>Text</Paragraph></td>
              </tr>
              <tr>
                <td>several
                    items in a cell</td>
                <td><Image filename="table_img.png" width="None" height="None"/></td>
              </tr>
            </Table></td>
            </tr>
          </LongTable>
        </story>

    We can pass an XPath query to printXML.

        >>> parser.printXML('//Image')
        <Image filename="logo.png" width="None" height="72.0"/>
        <Image filename="file.png" width="None" height="None"/>
        <Image filename="table_img.png" width="None" height="None"/>

    Or use SimpleXML.query to obtain a list of results.

        >>> parser.query('//Image')
        ['<Image filename="logo.png" width="None" height="72.0"/>',
         '<Image filename="file.png" width="None" height="None"/>',
         '<Image filename="table_img.png" width="None" height="None"/>']

    """


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite((
        doctest.DocTestSuite(optionflags=optionflags),
        ))

if __name__ == '__main__':
    unittest.main(default='test_suite')
