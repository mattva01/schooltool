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
HTML Analyzation Tools
"""
from lxml import etree


def to_string(node):
    if isinstance(node, basestring):
        return node
    else:
        return etree.tostring(node, pretty_print=True)


def queryHTML(xpath, response):
    """Helper function to perform an xpath query on an html response"""
    # Emulate the (annoying) behaviour of libxml2 < 2.9.0
    # https://bugzilla.gnome.org/show_bug.cgi?id=681822
    parser = etree.HTMLParser(remove_blank_text=True)
    doc = etree.HTML(response, parser)
    result = [to_string(node) for node in doc.xpath(xpath)]
    return result


def printQuery(xpath, response):
    """Helper function to print xpath query results on an html response"""
    for result in queryHTML(xpath, response):
        if result.strip():
            print result

