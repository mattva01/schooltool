##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Parse XML and compile to TALInterpreter intermediate code.

$Id$
"""
from zope.tal.taldefs import XML_NS, ZOPE_I18N_NS, ZOPE_METAL_NS, ZOPE_TAL_NS
from zope.tal.talgenerator import TALGenerator
from zope.tal.xmlparser import XMLParser


class TALParser(XMLParser):

    ordered_attributes = 1

    def __init__(self, gen=None, encoding=None): # Override
        XMLParser.__init__(self, encoding)
        if gen is None:
            gen = TALGenerator()
        self.gen = gen
        self.nsStack = []
        self.nsDict = {XML_NS: 'xml'}
        self.nsNew = []

    def getCode(self):
        return self.gen.getCode()

    def getWarnings(self):
        return ()

    def StartNamespaceDeclHandler(self, prefix, uri):
        self.nsStack.append(self.nsDict.copy())
        self.nsDict[uri] = prefix
        self.nsNew.append((prefix, uri))

    def EndNamespaceDeclHandler(self, prefix):
        self.nsDict = self.nsStack.pop()

    def StartElementHandler(self, name, attrs):
        if self.ordered_attributes:
            # attrs is a list of alternating names and values
            attrlist = []
            for i in range(0, len(attrs), 2):
                key = attrs[i]
                value = attrs[i+1]
                attrlist.append((key, value))
        else:
            # attrs is a dict of {name: value}
            attrlist = attrs.items()
            attrlist.sort() # For definiteness
        name, attrlist, taldict, metaldict, i18ndict \
              = self.process_ns(name, attrlist)
        attrlist = self.xmlnsattrs() + attrlist
        self.gen.emitStartElement(name, attrlist, taldict, metaldict, i18ndict)

    def process_ns(self, name, attrlist):
        taldict = {}
        metaldict = {}
        i18ndict = {}
        fixedattrlist = []
        name, namebase, namens = self.fixname(name)
        for key, value in attrlist:
            key, keybase, keyns = self.fixname(key)
            # Default to tag namespace, even though this really only
            # makes sense for elements in the TAL or METAL namespaces.
            # This allows <tal:block replace="..."> to be mostly
            # equivalent to <div tal:replace="...">; removal of the
            # actual element start and end tags is handled elsewhere
            # for elements in these namespaces.
            ns = keyns or namens
            item = key, value
            if ns == 'metal':
                metaldict[keybase] = value
                item = item + ("metal",)
            elif ns == 'tal':
                taldict[keybase] = value
                item = item + ("tal",)
            elif ns == 'i18n':
                i18ndict[keybase] = value
                item = item + ('i18n',)
            fixedattrlist.append(item)
        if namens in ('metal', 'tal', 'i18n'):
            taldict['tal tag'] = namens
        return name, fixedattrlist, taldict, metaldict, i18ndict

    def xmlnsattrs(self):
        # return [(qname, nsURI), ...] for the namespaces declared on
        # this element; must be called during the start element handler
        newlist = []
        for prefix, uri in self.nsNew:
            if prefix:
                key = "xmlns:" + prefix
            else:
                key = "xmlns"
            if uri in (ZOPE_METAL_NS, ZOPE_TAL_NS, ZOPE_I18N_NS):
                item = (key, uri, "xmlns")
            else:
                item = (key, uri)
            newlist.append(item)
        self.nsNew = []
        return newlist

    def fixname(self, name):
        # return (qname, localname, ns-indicator) for the attribute name `name`
        if ' ' in name:
            uri, name = name.split(' ')
            prefix = self.nsDict[uri]
            prefixed = name
            if prefix:
                prefixed = "%s:%s" % (prefix, name)
            ns = 'x'
            if uri == ZOPE_TAL_NS:
                ns = 'tal'
            elif uri == ZOPE_METAL_NS:
                ns = 'metal'
            elif uri == ZOPE_I18N_NS:
                ns = 'i18n'
            return (prefixed, name, ns)
        return (name, name, None)

    def EndElementHandler(self, name):
        name = self.fixname(name)[0]
        self.gen.emitEndElement(name)

    def DefaultHandler(self, text):
        self.gen.emitRawText(text)

def test():
    import sys
    p = TALParser()
    file = "tests/input/test01.xml"
    if sys.argv[1:]:
        file = sys.argv[1]
    p.parseFile(file)
    program, macros = p.getCode()
    from zope.tal.talinterpreter import TALInterpreter
    from zope.tal.dummyengine import DummyEngine
    engine = DummyEngine(macros)
    TALInterpreter(program, macros, engine, sys.stdout, wrap=0)()

if __name__ == "__main__":
    test()
