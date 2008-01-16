"""
Wrappers around lxml for easier XML parsing.

$Id$
"""

from lxml import etree

from zope.interface import implements
from zope.interface.common.interfaces import IException

from schooltool.common import UnicodeAwareException


def validate_against_schema(schema, xml):
    """Return True iff the XML document conforms to the given RelaxNG schema.

    Raises lxml.etree.XMLSyntaxError if the document is not well-formed.
    """
    try:
        relaxng_doc = etree.XML(schema)
    except etree.XMLSyntaxError:
        raise XMLSchemaError("Invalid RelaxNG schema.")

    relaxng = etree.RelaxNG(relaxng_doc)

    try:
        doc = etree.XML(xml)
    except etree.XMLSyntaxError:
        raise XMLParseError("Ill-formed document.")

    return relaxng.validate(doc)


def LxmlDocument(body, schema=None):
    if (schema is not None and
        not validate_against_schema(schema, body)):
        raise XMLValidationError(
            "Document not valid according to schema.")
    return etree.XML(body)


class IXMLError(IException): pass
class IXMLParseError(IXMLError): pass
class IXMLSchemaError(IXMLError): pass
class IXMLValidationError(IXMLError): pass
class IXMLXPathError(IXMLError): pass
class IXMLNamespaceError(IXMLError): pass
class IXMLAttributeError(IXMLError): pass


class XMLError(UnicodeAwareException):
    """Base class for XML errors."""
    implements(IXMLError)


class XMLParseError(XMLError):
    """Ill-formed XML document."""
    implements(IXMLParseError)


class XMLSchemaError(XMLError):
    """Invalid RelaxNG schema."""
    implements(IXMLSchemaError)


class XMLValidationError(XMLError):
    """Invalid XML document."""
    implements(IXMLValidationError)


class XMLXPathError(XMLError):
    """Ill-formed XPath query."""
    implements(IXMLXPathError)


class XMLNamespaceError(XMLError):
    """Unregistered XML namespace."""
    implements(IXMLNamespaceError)


class XMLAttributeError(XMLError):
    """Ill-formed XML attribute name."""
    implements(IXMLAttributeError)

