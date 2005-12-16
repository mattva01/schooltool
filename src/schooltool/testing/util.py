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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Testing Utilities

$Id$
"""
__metaclass__ = type

import cgi
import sets
import difflib
import libxml2
import unittest
from pprint import pformat
from StringIO import StringIO

from zope.interface import implements
from zope.app.traversing.interfaces import IContainmentRoot


def unidiff(old, new, oldlabel="expected output", newlabel="actual output"):
    """Display a compact unified diff between old text and new text.

    Bugs: does not work when old or new is an empty string (this seems to
    be a bug/limitation of the Python 2.3 difflib module).
    """
    return "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                          oldlabel, newlabel, lineterm=''))


def diff(old, new, oldlabel="expected output", newlabel="actual output"):
    """Display a unified diff between old text and new text."""
    old = old.splitlines()
    new = new.splitlines()

    diff = ['--- %s' % oldlabel, '+++ %s' % newlabel]

    def dump(tag, x, lo, hi):
        for i in xrange(lo, hi):
            diff.append(tag + x[i])

    differ = difflib.SequenceMatcher(a=old, b=new)
    for tag, alo, ahi, blo, bhi in differ.get_opcodes():
        if tag == 'replace':
            dump('-', old, alo, ahi)
            dump('+', new, blo, bhi)
        elif tag == 'delete':
            dump('-', old, alo, ahi)
        elif tag == 'insert':
            dump('+', new, blo, bhi)
        elif tag == 'equal':
            dump(' ', old, alo, ahi)
        else:
            raise AssertionError('unknown tag %r' % tag)
    return "\n".join(diff)


def pformat_set(s):
    """Pretty-print a Set."""
    items = list(s)
    items.sort()
    return 'sets.Set(%s)' % pformat(items)



def normalize_xml(xml, recursively_sort=()):
    """Normalizes an XML document.

    The idea is that two semantically equivalent XML documents should be
    normalized into the same canonical representation.  Therefore if two
    documents compare equal after normalization, they are semantically
    equivalent.

    The canonical representation used here has nothing to do with W3C Canonical
    XML.

    This function normalizes indentation, whitespace and newlines (except
    inside text nodes), element attribute order, expands character references,
    expands shorthand notation of empty XML elements ("<br/>" becomes
    "<br></br>").

    If an element has an attribute test:sort="children", the attribute is
    removed and its immediate child nodes are sorted textually.  If the
    attribute value is test:sort="recursively", the sorting happens at
    all levels (unless specifically prohibited with test:sort="not").

    If recursively_sort is given, it is a sequence of tags that will have
    test:sort="recursively" automatically appended to their attribute lists in
    the text.  Use it when you cannot or do not want to modify the XML document
    itself.

    Caveats:
     - normalize_xml does not deal well with text nodes
     - normalize_xml does not help when different prefixes are used for the
       same namespace
     - normalize_xml does not handle all XML features (CDATA sections, inline
       DTDs, processing instructions, comments)
    """

    class Document:

        def __init__(self):
            self.children = []
            self.sort_recursively = False

        def render(self, level=0):
            result = []
            for child in self.children:
                result.append(child.render(level))
            return ''.join(result)

    class Element:

        def __init__(self, parent, tag, attrlist, sort=False,
                     sort_recursively=False):
            self.parent = parent
            self.tag = tag
            self.attrlist = attrlist
            self.children = []
            self.sort = sort
            self.sort_recursively = sort_recursively

        def render(self, level):
            result = []
            indent = '  ' * level
            line = '%s<%s' % (indent, self.tag)
            for attr in self.attrlist:
                if len(line + attr) < 78:
                    line += attr
                else:
                    result.append(line)
                    result.append('\n')
                    line = '%s %s%s' % (indent, ' ' * len(self.tag), attr)
            if self.children:
                s = ''.join([child.render(level+1) for child in self.children])
            else:
                s = ''
            if s:
                result.append('%s>\n' % line)
                result.append(s)
                result.append('%s</%s>\n' % (indent, self.tag))
            else:
                result.append('%s/>\n' % line)
            return ''.join(result)

        def finalize(self):
            if self.sort:
                self.children.sort(lambda x, y: cmp(x.key, y.key))
            self.key = self.render(0)

    class Text:

        def __init__(self, data):
            self.data = data
            self.key = None

        def render(self, level):
            data = cgi.escape(self.data.strip())
            if data:
                indent = '  ' * level
                return ''.join(['%s%s\n' % (indent, line.strip())
                                for line in data.splitlines()])
            else:
                return ''

    class Handler:

        def __init__(self):
            self.level = 0
            self.result = []
            self.root = self.cur = Document()
            self.last_text = None

        def startElement(self, tag, attrs):
            sort = sort_recursively = self.cur.sort_recursively
            if attrs:
                if 'test:sort' in attrs:
                    value = attrs['test:sort']
                    del attrs['test:sort']
                    if value == 'children':
                        sort = True
                    elif value == 'recursively':
                        sort = sort_recursively = True
                    elif value == 'not':
                        sort = sort_recursively = False
                attrlist = attrs.items()
                attrlist.sort()
                attrlist = [' %s="%s"' % (k, cgi.escape(v, True))
                            for k, v in attrlist]
            else:
                attrlist = []
            child = Element(self.cur, tag, attrlist, sort=sort,
                            sort_recursively=sort_recursively)
            self.cur.children.append(child)
            self.cur = child
            self.last_text = None

        def endElement(self, tag):
            self.cur.finalize()
            self.cur = self.cur.parent
            self.last_text = None

        def characters(self, data):
            if self.last_text is not None:
                self.last_text.data += data
            else:
                self.last_text = Text(data)
                self.cur.children.append(self.last_text)

        def render(self):
            return self.root.render()

    for tag in recursively_sort:
        xml = xml.replace('<%s' % tag,
                          '<%s test:sort="recursively"' % tag)
    try:
        handler = Handler()
        ctx = libxml2.createPushParser(handler, "", 0, "")
        ret = ctx.parseChunk(xml, len(xml), True)
        if ret:
            return "PARSE ERROR: %r\n%s" % (ret, xml)
        return ''.join(handler.render())
    except libxml2.parserError, e:
        return "ERROR: %s" % e


def run_unit_tests(testcase):
    r"""Hack to call into unittest from doctests.

        >>> class SampleTestCase(unittest.TestCase):
        ...     def test1(self):
        ...         self.assertEquals(2 + 2, 4)
        >>> run_unit_tests(SampleTestCase)

        >>> class BadTestCase(SampleTestCase):
        ...     def test2(self):
        ...         self.assertEquals(2 * 2, 5)
        >>> run_unit_tests(BadTestCase) # doctest: +REPORT_NDIFF
        .F
        ======================================================================
        FAIL: test2 (schooltool.app.tests.test_app.BadTestCase)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
        ...
        AssertionError: 4 != 5
        <BLANKLINE>
        ----------------------------------------------------------------------
        Ran 2 tests in ...s
        <BLANKLINE>
        FAILED (failures=1)

    """
    testsuite = unittest.makeSuite(testcase)
    output = StringIO()
    result = unittest.TextTestRunner(output).run(testsuite)
    if not result.wasSuccessful():
        print output.getvalue(),



class _Anything:
    """An object that is equal to any other object."""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return 'Anything'

Anything = _Anything()


class EqualsSortedMixin:
    """Mixin that adds a helper method for comparing lists ignoring order."""

    def assertEqualsSorted(self, a, b):
        x = list(a)
        y = list(b)
        x.sort()
        y.sort()
        self.assertEquals(x, y)

    assertEqualSorted = assertEqualsSorted


class NiceDiffsMixin:
    """Mixin that changes assertEquals to show a unified diff of pretty-printed
    values.
    """

    def assertEquals(self, results, expected, msg=None):
        if msg is None:
            if (isinstance(expected, basestring)
                and isinstance(results, basestring)):
                msg = "\n" + diff(expected, results)
            elif (isinstance(expected, sets.Set)
                and isinstance(results, sets.Set)):
                msg = "\n" + diff(pformat_set(expected), pformat_set(results))
            else:
                msg = "\n" + diff(pformat(expected), pformat(results))
        unittest.TestCase.assertEquals(self, results, expected, msg)

    assertEqual = assertEquals



class XMLCompareMixin:

    def assertEqualsXML(self, result, expected, recursively_sort=()):
        """Assert that two XML documents are equivalent.

        If recursively_sort is given, it is a sequence of tags that
        will have test:sort="recursively" appended to their attribute lists
        in 'result' text.  See the docstring for normalize_xml for more
        information about this attribute.
        """
        result = normalize_xml(result, recursively_sort=recursively_sort)
        expected = normalize_xml(expected, recursively_sort=recursively_sort)
        self.assertEquals(result, expected, "\n" + diff(expected, result))

    assertEqualXML = assertEqualsXML


def compareXML(result, expected, recursively_sort=()):
    """Compare 2 XML snippets for equality.

    This is a doctest version of XMLCompareMixin.assertEqualsXML.

    If recursively_sort is given, it is a sequence of tags that will have
    test:sort="recursively" appended to their attribute lists in 'result' text.
    See the docstring for normalize_xml for more information about this
    attribute.
    """
    result = normalize_xml(result, recursively_sort=recursively_sort)
    expected = normalize_xml(expected, recursively_sort=recursively_sort)
    if result == expected:
        return True
    else:
        print diff(expected, result)
        return False


class QuietLibxml2Mixin:
    """Text mixin that disables libxml2 error reporting.

    Sadly the API of libxml2 does not allow us to restore the error reporting
    function in tearDown.  <Insert derogatory comments here>
    """

    def setUpLibxml2(self):
        import libxml2
        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def tearDownLibxml2(self):
        import libxml2
        # It's not possible to restore the error handler that was installed
        # before (libxml2 API limitation), so we set up a generic one that
        # prints everything to stdout.
        def on_error_callback(ctx, msg):
            sys.stderr.write(msg)
        libxml2.registerErrorHandler(on_error_callback, None)



class FakeRoot(object):
    implements(IContainmentRoot)


class FakeFolder(object):
    def __init__(self, parent, name):
        self.__parent__ = parent
        self.__name__ = name


def fakePath(obj, path):
    """Make zapi.absoluteURL(obj) return url.

        >>> from zope.app import zapi
        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpTraversal()

        >>> class Stub: pass
        >>> obj = Stub()
        >>> fakePath(obj, '/dir/subdir/name')
        >>> zapi.absoluteURL(obj, TestRequest())
        'http://127.0.0.1/dir/subdir/name'

        >>> setup.placelessTearDown()

    """
    folder = FakeRoot()
    bits = [name for name in path.split('/') if name]
    for name in bits[:-1]:
        folder = FakeFolder(folder, name)
    name = bits and bits[-1] or ''
    obj.__parent__ = folder
    obj.__name__ = name


