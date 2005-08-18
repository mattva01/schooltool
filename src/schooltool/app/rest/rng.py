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
The schooltool.schema.rng module.

Relax NG validation facilities.
"""
import libxml2


def validate_against_schema(schema, xml):
    """Return True iff the xml document conforms to the given RelaxNG schema.

    Raises libxml2.parserError if the document is not well-formed.
    """

    rngp = libxml2.relaxNGNewMemParserCtxt(schema, len(schema))
    try:
        rngs = rngp.relaxNGParse()
        ctxt = rngs.relaxNGNewValidCtxt()
        doc = libxml2.parseDoc(xml)
        try:
            result = doc.relaxNGValidateDoc(ctxt)
        finally:
            doc.freeDoc()
        return result == 0
    finally:
        # what does this do?
        libxml2.relaxNGCleanupTypes()

