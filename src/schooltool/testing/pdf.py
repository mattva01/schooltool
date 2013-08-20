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
SchoolTool Reporlab PDF testing helpers.

"""

import cgi
from cStringIO import StringIO
from lxml import etree

from reportlab import platypus


class StoryXML(object):

    document = None # XML document representing the story

    def __init__(self, story):
        parser = Parser(formatters=_xml_formatters,
                        default=format_classname_xml)
        xml_text = u'<story>\n%s\n</story>' % parser(story)
        self.document = etree.parse(StringIO(xml_text.encode('UTF-8')))
        self._text = etree.tostring(self.document, pretty_print=True)

    def query(self, xpath):
        result = []
        for node in self.document.xpath(xpath):
            if isinstance(node, basestring):
                result.append(node)
            else:
                result.append(etree.tostring(node, pretty_print=True))
        return [s.strip() for s in result]

    def printXML(self, xpath=''):
        if not xpath:
            print self._text
            return
        for entry in self.query(xpath):
            print entry


null_formatter = lambda parser, flowable: u''


class Parser(object):
    def __init__(self, formatters={}, default=null_formatter):
        self.formatters = formatters.copy()
        self.default = default

    def __call__(self, flowable):
        formatter = self.formatters.get(flowable.__class__, self.default)
        return formatter(self, flowable)


def format_flowable_list(parser, flowables):
    parsed = [parser(flowable)
              for flowable in flowables]
    return '\n'.join([text for text in parsed if text])


def format_str_text(parser, flowable):
    return unicode(flowable)


def format_classname_text(parser, flowable):
    return unicode(flowable.__class__.__name__)


def format_str_xml(parser, flowable):
    return cgi.escape(unicode(flowable))


def format_classname_xml(parser, flowable):
    return u'<%s />' % format_classname_text(parser, flowable)


def format_container_xml(parser, flowable):
    tag_name = format_classname_text(parser, flowable)
    content = parser(flowable._content)
    return u'<%s>\n%s\n</%s>' % (tag_name, content, tag_name)


def format_preformatted_xml(parser, flowable):
    tag_name = format_classname_text(parser, flowable)
    return u'<%s bulletText="%s">%s</%s>' % (
        tag_name,
        cgi.escape(flowable.bulletText),
        cgi.escape(u'\n'.join(flowable.lines)),
        tag_name)


def format_table_xml(parser, flowable):
    tag_name = format_classname_text(parser, flowable)
    text = u'<%s>\n' % tag_name
    for row in flowable._cellvalues:
        text += '<tr>\n'
        for cell in row:
            text += '<td>%s</td>\n' % parser(cell)
        text += '</tr>\n'
    text += u'</%s>' % tag_name
    return text


class Format_Attributes_XML(object):
    def __init__(self, attributes=[], content=''):
        self.attribute_names = attributes
        self.content_attribute = content

    def formatAttr(self, parser, flowable, attr_name):
        words = [word for word in attr_name.split('_') if word]
        if words:
            # first word starts with lower case
            words[0] = words[0][:1].lower() + words[0][1:]
        # other words start with upper case
        words[1:] = [word[:1].upper() + word[1:] for word in words[1:]]
        pretty_name = ''.join(words)

        return u'%s="%s"' % (
            pretty_name,
            cgi.escape(str(getattr(flowable, attr_name, None))))

    def formatContents(self, parser, flowable):
        contents = u''
        if self.content_attribute:
            contents = getattr(
                flowable, self.content_attribute, '')
        return unicode(cgi.escape(contents))

    def __call__(self, parser, flowable):
        tag_name = format_classname_text(parser, flowable)
        text = u'<%s' % tag_name
        for attr_name in self.attribute_names:
            text += u' %s' % self.formatAttr(parser, flowable, attr_name)

        contents = self.formatContents(parser, flowable)
        if contents:
            text += u'>%s</%s>' % (contents, tag_name)
        else:
            text += u' />'

        return text


class Format_Paragraph_XML(Format_Attributes_XML):
    def __init__(self, attributes=[]):
        Format_Attributes_XML.__init__(self, attributes=attributes)

    def formatContents(self, parser, flowable):
        return unicode(cgi.escape(flowable.getPlainText()))


class Format_ParaAndImage_XML(Format_Attributes_XML):

    def __init__(self):
        Format_Attributes_XML.__init__(self, ['xpad', 'ypad'])

    def formatContents(self, parser, flowable):
        text = parser([flowable.I, flowable.P])
        return text and '\n%s\n' % text or ''


_xml_formatters = {
    # system
    type(None): null_formatter,
    list: format_flowable_list,

    # plain text
    str: format_str_xml,
    unicode: format_str_xml,

    # paragraph text
    platypus.paragraph.Paragraph: Format_Paragraph_XML(),
    platypus.xpreformatted.XPreformatted: Format_Paragraph_XML(
        attributes=['bulletText']),
    platypus.xpreformatted.PythonPreformatted: Format_Paragraph_XML(
        attributes=['bulletText']),
    platypus.flowables.Preformatted: format_preformatted_xml,

    # graphics
    platypus.flowables.Image:
        Format_Attributes_XML(['filename', '_width', '_height']),
    platypus.flowables.HRFlowable:
        Format_Attributes_XML(
            ['width', 'lineWidth', 'spaceBefore', 'spaceAfter',
             'hAlign', 'vAlign']),

    # containers
    platypus.tables.Table: format_table_xml,
    platypus.tables.LongTable: format_table_xml,
    platypus.flowables.ParagraphAndImage: Format_ParaAndImage_XML(),
    #platypus.flowables.ImageAndFlowables
    #platypus.flowables.PTOContainer, # (Please Turn Over The Page behaviour)

    # spacing
    platypus.flowables.KeepInFrame: format_container_xml,
    platypus.flowables.KeepTogether: format_container_xml,
    platypus.flowables.PageBreak: format_classname_xml,
    platypus.flowables.SlowPageBreak: format_classname_xml,
    platypus.flowables.CondPageBreak: Format_Attributes_XML(['height']),
    platypus.flowables.Spacer: Format_Attributes_XML(
        ['width', 'height']),

    # other
    platypus.flowables.AnchorFlowable: Format_Attributes_XML(['_name']),
    #platypus.tableofcontents.TableOfContents,
    #platypus.tableofcontents.SimpleIndex,

    # omit from output
    platypus.flowables.UseUpSpace: null_formatter,
    platypus.flowables.Flowable: null_formatter,
    platypus.flowables.TraceInfo: null_formatter,
    platypus.flowables.Macro: null_formatter,
    platypus.flowables.CallerMacro: null_formatter,
    platypus.flowables.FailOnWrap: null_formatter,
    platypus.flowables.FailOnDraw: null_formatter,
}

