"""
Wrappers around libxml2 for easier XML parsing.

$Id$
"""

import libxml2

from schooltool.common import UnicodeAwareException
from schooltool.common import to_unicode
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _


class XMLDocument(object):
    r"""XML document.

    The document is parsed when you create an XMLDocument instance.

        >>> body = '''
        ...   <?xml version="1.0" encoding="ISO-8859-13"?>
        ...   <hello id="123">
        ...     <world>Earth</world>
        ...     <message language="en">Hi, people!</message>
        ...     <message language="lt">Sveiki, \xFEmon\xEBs!</message>
        ...   </hello>
        ... '''.lstrip()
        >>> doc = XMLDocument(body)

    You can perform XPath queries on it.

        >>> len(doc.query('/hello/world'))
        1
        >>> len(doc.query('/hello/earthlings'))
        0

    A query returns a list of XMLNode objects.

        >>> message = doc.query('//message')[0]
        >>> message.content
        u'Hi, people!'
        >>> message['language']
        u'en'

    You can access the root element directly

        >>> doc.root['id']
        u'123'

    You do not need to worry about charset conversions.

        >>> message = doc.query('//message')[1]
        >>> message.content
        u'Sveiki, \u017emon\u0117s!'
        >>> message['language']
        u'lt'

    When you're done you should free the memory allocated by libxml2

        >>> doc.free()

    If you do not free the memory manually, it will be freed during garbage
    collection.
    """

    root = property(lambda self: XMLNode(self._doc.getRootElement(), self))

    def __init__(self, body, schema=None, namespaces=None):
        """Parse the document (and validate with a RelaxNG schema if given).

        Ill-formed documents cause XMLParseError to be raised.

            >>> XMLDocument("<ill></formed>")
            Traceback (most recent call last):
              ...
            XMLParseError: Ill-formed document.

        Documents can be validated according to a RelaxNG schema.

            >>> schema = '''
            ...   <grammar xmlns="http://relaxng.org/ns/structure/1.0">
            ...     <start>
            ...       <element name="sample">
            ...         <text/>
            ...       </element>
            ...     </start>
            ...   </grammar>
            ... '''

            >>> XMLDocument("<bad_example>I'm invalid!</bad_example>", schema)
            Traceback (most recent call last):
              ...
            XMLValidationError: Document not valid according to schema.

            >>> XMLDocument("<sample>Hi!</sample>", schema).free()

        You can pass a dictionary with namespaces directly to the constructor
        instead of calling registerNs:

            >>> doc = XMLDocument("<sample/>",
            ...                   namespaces={'n1': 'http://example.com/n1',
            ...                               'n2': 'http://example.com/n2'})
            >>> doc.namespaces['n1']
            'http://example.com/n1'
            >>> doc.query('n2:nosuchelement')
            []

        """
        self._doc = self._xpathctx = None # __del__ wants them
        if schema is not None:
            try:
                if not validate_against_schema(schema, body):
                    raise XMLValidationError(
                                _("Document not valid according to schema."))
            except libxml2.parserError, e:
                if 'xmlRelaxNGParse' in str(e):
                    raise XMLSchemaError(_("Invalid RelaxNG schema."))
                else:
                    raise XMLParseError(_("Ill-formed document."))
        try:
            self._doc = libxml2.parseDoc(body)
        except libxml2.parserError:
            raise XMLParseError(_("Ill-formed document."))
        self._xpathctx = self._doc.xpathNewContext()
        self.namespaces = {}
        if namespaces:
            for ns, url in namespaces.items():
                self.registerNs(ns, url)

    def registerNs(self, ns, url):
        """Register an XML namespace.

        You need to call registerNs for all namespaces that you want to use in
        XPath queries and attribute lookups.  You do not have to use the same
        prefix as is used in the document itself.

            >>> doc = XMLDocument('''
            ...   <sample xmlns="http://example.com/ns/samplens"
            ...           xmlns:xlink="http://www.w3.org/1999/xlink">
            ...      <a xlink:type="simple" xlink:href="http://example.com" />
            ...   </sample>
            ... '''.lstrip())
            >>> doc.registerNs('sample', 'http://example.com/ns/samplens')
            >>> doc.registerNs('xlnk', 'http://www.w3.org/1999/xlink')

            >>> nodes = doc.query('//sample:a')
            >>> len(nodes)
            1

            >>> nodes[0]['xlnk:href']
            u'http://example.com'

        As usual, it is a good idea to free the resources explicitly.

            >>> doc.free()

        """
        self._xpathctx.xpathRegisterNs(ns, url)
        self.namespaces[ns] = url

    def query(self, xpath_query):
        """Perform an XPath query relative to the document node.

        Returns a list of XMLNode objects.

            >>> doc = XMLDocument('<a><b><c>d</c></b></a>')
            >>> nodes = doc.query('/a//c')
            >>> len(nodes)
            1
            >>> nodes[0].content
            u'd'

        Raises an exception if the querry is ill-formed

            >>> doc.query('@!#%!@%!@#%')
            Traceback (most recent call last):
              ...
            XMLXPathError: Ill-formed XPath query ('@!#%!@%!@#%').

        As usual, it is a good idea to free the resources explicitly.

            >>> doc.free()

        """
        self._xpathctx.setContextNode(self._doc)
        try:
            return [XMLNode(node, self)
                    for node in self._xpathctx.xpathEval(xpath_query)]
        except libxml2.xpathError:
            raise XMLXPathError(_('Ill-formed XPath query (%r).')
                                % xpath_query)

    def free(self):
        """Free libxml2 data structures.

            >>> doc = XMLDocument('<simple/>')
            >>> doc.free()

        Free can be safely called more than once.

            >>> doc.free()

        """
        if self._doc is not None:
            self._doc.freeDoc()
            self._xpathctx.xpathFreeContext()
            self._doc = self._xpathctx = None

    def __del__(self):
        """Free libxml2 data structures during garbage collection.

            >>> doc = XMLDocument('<simple/>')
            >>> doc = None
            >>> import gc
            >>> ignore = gc.collect()

        """
        self.free()


class XMLNode(object):
    r"""XML element node.

    Lists of XMLNodes are returned by XMLDocument.query and XMLNode.query
    methods.  See the documentation of XMLDocument for usage examples.

    The content of an element is accessible as its `content` attribute.
    It is a Unicode string.

        >>> doc = XMLDocument('''
        ...    <sample>
        ...       <one>One</one>
        ...       <two count="42">
        ...         Two
        ...         lines
        ...       </two>
        ...       <empty />
        ...     </sample>
        ... ''')
        >>> doc.query('//one')[0].content
        u'One'
        >>> doc.query('//two')[0].content
        u'\n        Two\n        lines\n      '
        >>> doc.query('//empty')[0].content
        u''

    You can get attributes via XPath queries or by accessing the node directly.

        >>> doc.query('//two/@count')[0].content
        u'42'

        >>> node = doc.query('//two')[0]
        >>> node.query('@count')[0].content
        u'42'
        >>> node['count']
        u'42'

    As usual, it is a good idea to free the resources explicitly.

        >>> doc.free()
    """

    content = property(lambda self: to_unicode(self._node.content))

    def __init__(self, libxml_node, document):
        self._node = libxml_node
        self._doc = document

    def get(self, name, default=None):
        """Get an attribute of this node.

            >>> doc = XMLDocument('''
            ...    <sample
            ...       xmlns:xlink="http://www.w3.org/1999/xlink"
            ...       xmlns:sample="http://example.com/ns/samplens"
            ...       xlink:type="simple"
            ...       sample:attr="sample value"
            ...       just_attr="another value"
            ...       />
            ... ''')
            >>> doc.registerNs('sample', 'http://example.com/ns/samplens')
            >>> doc.registerNs('xlnk', 'http://www.w3.org/1999/xlink')

            >>> node = doc.query('/sample')[0]
            >>> node.get('xlnk:type')
            u'simple'
            >>> node.get('sample:attr')
            u'sample value'
            >>> node.get('just_attr')
            u'another value'
            >>> node.get('nonexistent') is None
            True
            >>> node.get('nonexistent', u'default value')
            u'default value'

        Accessing unregistered namespaces results in an XMLError.

            >>> node.get('unregistered_ns:anything')
            Traceback (most recent call last):
              ...
            XMLNamespaceError: Unregistered namespace prefix (unregistered_ns:anything).

            >>> node.get('too:many:colons')
            Traceback (most recent call last):
              ...
            XMLAttributeError: Ill-formed attribute name (too:many:colons).

        As usual, it is a good idea to free the resources explicitly.

            >>> doc.free()

        """
        if ':' in name:
            try:
                ns, attr = name.split(':')
            except (KeyError, ValueError):
                raise XMLAttributeError(_("Ill-formed attribute name (%s).")
                                        % name)
            try:
                uri = self._doc.namespaces[ns]
            except (KeyError, ValueError):
                raise XMLNamespaceError(
                            _("Unregistered namespace prefix (%s).") % name)
        else:
            attr = name
            uri = None
        value = to_unicode(self._node.nsProp(attr, uri))
        if value is None:
            value = default
        return value

    def __getitem__(self, name):
        """Get an attribute of this node.

            >>> doc = XMLDocument('''
            ...    <sample
            ...       xmlns:xlink="http://www.w3.org/1999/xlink"
            ...       xmlns:sample="http://example.com/ns/samplens"
            ...       xlink:type="simple"
            ...       sample:attr="sample value"
            ...       just_attr="another value"
            ...       />
            ... ''')
            >>> doc.registerNs('sample', 'http://example.com/ns/samplens')
            >>> doc.registerNs('xlnk', 'http://www.w3.org/1999/xlink')

            >>> node = doc.query('/sample')[0]
            >>> node['xlnk:type']
            u'simple'
            >>> node['sample:attr']
            u'sample value'
            >>> node['just_attr']
            u'another value'

        Accessing nonexistent attribues results in an AttributeError.

            >>> node['nonexistent']
            Traceback (most recent call last):
              ...
            AttributeError: nonexistent

            >>> node['attr']
            Traceback (most recent call last):
              ...
            AttributeError: attr

            >>> node['sample:nonexistent']
            Traceback (most recent call last):
              ...
            AttributeError: sample:nonexistent

        Accessing unregistered namespaces results in an XMLError.

            >>> node['unregistered_ns:anything']
            Traceback (most recent call last):
              ...
            XMLNamespaceError: Unregistered namespace prefix (unregistered_ns:anything).

            >>> node['too:many:colons']
            Traceback (most recent call last):
              ...
            XMLAttributeError: Ill-formed attribute name (too:many:colons).

        As usual, it is a good idea to free the resources explicitly.

            >>> doc.free()

        """
        value = self.get(name)
        if value is None:
            raise AttributeError(name)
        return value

    def query(self, xpath_query):
        """Perform an XPath query relative to this node node.

        Returns a list of XMLNode objects.

            >>> doc = XMLDocument('<a><b><c>d</c></b></a>')
            >>> node = doc.query('/a/b')[0]
            >>> len(node.query('c'))
            1
            >>> len(node.query('b'))
            0

        Raises an exception if the querry is ill-formed

            >>> node.query('@!#%!@%!@#%')
            Traceback (most recent call last):
              ...
            XMLXPathError: Ill-formed XPath query ('@!#%!@%!@#%').

        As usual, it is a good idea to free the resources explicitly.

            >>> doc.free()

        """
        xpathctx = self._doc._xpathctx
        xpathctx.setContextNode(self._node)
        try:
            return [XMLNode(node, self._doc)
                    for node in xpathctx.xpathEval(xpath_query)]
        except libxml2.xpathError:
            raise XMLXPathError(_('Ill-formed XPath query (%r).')
                                % xpath_query)


class XMLError(UnicodeAwareException):
    """Base class for XML errors."""

class XMLParseError(XMLError):
    """Ill-formed XML document."""

class XMLSchemaError(XMLError):
    """Invalid RelaxNG schema."""

class XMLValidationError(XMLError):
    """Invalid XML document."""

class XMLXPathError(XMLError):
    """Ill-formed XPath query."""

class XMLNamespaceError(XMLError):
    """Unregistered XML namespace."""

class XMLAttributeError(XMLError):
    """Ill-formed XML attribute name."""

