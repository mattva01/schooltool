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
Unit tests for the schooltool.views package.
"""

from StringIO import StringIO
from zope.interface import implements, directlyProvides
from twisted.protocols import http
from schooltool.interfaces import ITraversable, IContainmentRoot, IUtility
from schooltool.interfaces import ILocation

__metaclass__ = type


class RequestStub:

    code = 200
    reason = 'OK'

    def __init__(self, uri='', method='GET', body='', headers=None,
                 authenticated_user=None):
        self.uri = uri
        self.method = method
        self.path = ''
        self.virtualpath = ''
        self.content = StringIO(body)
        self.authenticated_user = authenticated_user
        self.headers = {}
        self.args = {}
        if body:
            self.request_headers = {'content-length': len(body)}
        else:
            self.request_headers = {'content-length': 0}
        if headers:
            for k, v in headers.items():
                self.request_headers[k.lower()] = v
        self.accept = []
        self.path = uri
        self._transport = 'INET'
        self._hostname = 'localhost'
        self._port = 7001
        if '://' in uri:
            start = uri.find('/', uri.find('://')+3)
            if start < 0:
                start = len(uri)
            self.path = uri[start:]
            if uri.startswith('https://'):
                self._transport = 'SSL'
            host_and_port = uri[uri.index('://')+3:start]
            if ':' not in host_and_port:
                host_and_port += ':7001'
            self._hostname, port = host_and_port.split(':')
            self._port = int(port)

    def getRequestHostname(self):
        return self.getHost()[1]

    def getHost(self):
        return (self._transport, self._hostname, self._port)

    def getHeader(self, header):
        # Twisted's getHeader returns None when the header does not exist
        return self.request_headers.get(header.lower())

    def setHeader(self, header, value):
        self.headers[header.lower()] = value

    def setResponseCode(self, code, reason=None):
        self.code = code
        if reason is None:
            self.reason = http.RESPONSES.get(code, 'Unknown Status')
        else:
            self.reason = reason

    def chooseMediaType(self, supported_types):
        from schooltool.main import chooseMediaType
        return chooseMediaType(supported_types, self.accept)


class TraversableStub:

    implements(ITraversable)

    def __init__(self, **kw):
        self.children = kw

    def traverse(self, name):
        return self.children[name]


class TraversableRoot(TraversableStub):

    implements(IContainmentRoot)


class LocatableStub:
    pass


def setPath(obj, path, root=None):
    """Trick getPath(obj) into returning path."""
    assert path.startswith('/')
    obj.__name__ = path[1:]
    if root is None:
        directlyProvides(obj, ILocation)
        obj.__parent__ = TraversableRoot()
    else:
        assert IContainmentRoot.providedBy(root)
        obj.__parent__ = root


class Libxml2ErrorLogger:

    def __init__(self):
        self.log = []

    def __call__(self, ctx, error):
        self.log.append(error)


class XPathTestContext:
    """XPath context for use in tests that check rendered xml.

    You must call the free() method at the end of the test.

    XXX add option for validating result against a schema
    """

    namespaces = {'xlink': 'http://www.w3.org/1999/xlink'}

    def __init__(self, test, result):
        """Create an XPath test context.

        test is the unit test TestCase, used for assertions.
        result is a string containing XML>
        """
        import libxml2  # import here so we only import if we need it
        self.errorlogger = Libxml2ErrorLogger()
        libxml2.registerErrorHandler(self.errorlogger, None)
        self.test = test
        self.doc = libxml2.parseDoc(result)
        self.context = self.doc.xpathNewContext()
        for nsname, ns in self.namespaces.iteritems():
            self.context.xpathRegisterNs(nsname, ns)

    def free(self):
        """Free C level objects.

        Call this at the end of a test to prevent memory leaks.
        """
        self.doc.freeDoc()
        self.context.xpathFreeContext()

    def query(self, expression):
        """Perform an XPath query.

        Returns a sequence of DOM nodes.
        """
        return self.context.xpathEval(expression)

    def oneNode(self, expression):
        """Perform an XPath query.

        Asserts that the query matches exactly one DOM node.  Returns it.
        """
        nodes = self.context.xpathEval(expression)
        self.test.assertEquals(len(nodes), 1,
                               "%s matched %d nodes"
                               % (expression, len(nodes)))
        return nodes[0]

    def assertNumNodes(self, num, expression):
        """Assert that an XPath expression matches exactly num nodes."""
        nodes = self.context.xpathEval(expression)
        self.test.assertEquals(num, len(nodes),
                               "%s matched %d nodes instead of %d"
                               % (expression, len(nodes), num))

    def assertAttrEquals(self, node, name, value):
        """Assert that an attribute of an element node has a given value.

        Attribute name may contain a namespace (e.g. 'xlink:href').  The
        dict of recongized namespaces is kept in the namespaces attribute.
        """
        name_parts = name.split(':')
        if len(name_parts) > 2:
            raise ValueError('max one colon in attribute name', name)
        elif len(name_parts) == 1:
            localname = name_parts[0]
            ns = None
        else:
            nsname, localname = name_parts
            ns = self.namespaces[nsname]
        self.test.assertEquals(node.nsProp(localname, ns), value)

    def assertNoErrors(self):
        """Assert that no errors were found while parsing the document."""
        self.test.assertEquals(self.errorlogger.log, [])


class UtilityStub:

    implements(IUtility)

    __parent__ = None
    __name__ = None

    def __init__(self, title):
        self.title = title


def viewClass(iface):
    """Return the view class registered for an interface."""
    from schooltool.component import getView
    cls = type(iface.getName(), (), {})
    obj = cls()
    directlyProvides(obj, iface)
    return getView(obj).__class__
