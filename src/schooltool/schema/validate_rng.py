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
Check that a RelaxNG schema is valid, or validate an xml document against
a RelaxNG schema.

Usage: validate_rng schema [xmlfile]

This program requires libxml2 and the python bindings for libxml2.
libxml2 is available from http://www.xmlsoft.org/
Python bindings are available from http://www.xmlsoft.org/python.html

PoV are using libxml2 2.5.11-2 and libxml2-python2.3 2.5.11-2 from debian
unstable. However, any recent release should work.

$Id$
"""
import libxml2
import sys


def validate_against_schema(schema, xml):
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


def load_schema(schema):
    rngp = libxml2.relaxNGNewMemParserCtxt(schema, len(schema))
    try:
        rngs = rngp.relaxNGParse()
        ctxt = rngs.relaxNGNewValidCtxt()
    finally:
        # what does this do?
        libxml2.relaxNGCleanupTypes()


def on_error_callback(ctx, str):
    print "error: %s:%s" % (ctx, str)


def print_usage():
    print >> sys.stderr, 'usage: validate_rng schema [xmlfile]'


def main():
    if len(sys.argv) == 1:
        print_usage()
        return 1
    argiter = iter(sys.argv)
    pyfile = argiter.next()
    xmlfile = None
    try:
        schemafile = argiter.next()
        xmlfile = argiter.next()
        shouldstophere = argiter.next()
    except StopIteration:
        pass
    else:
        print_usage()
        return 1

    libxml2.registerErrorHandler(on_error_callback, "-->")
    schema = file(schemafile).read()

    try:
        if xmlfile:
            xml = file(xmlfile).read()
            validates_ok = validate_against_schema(schema, xml)
            if not validates_ok:
                print "Invalid"
                return 1
        else:
            load_schema(schema)
    except libxml2.parserError, e:
        print >> sys.stderr, e.msg
        return 1
    print "OK"
    return 0


if __name__ == '__main__':
    sys.exit(main())

