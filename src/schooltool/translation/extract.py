##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Extract message strings from python modules, page template files
and ZCML files.

$Id: extract.py,v 1.17 2004/04/02 14:03:29 mgedmin Exp $
"""

import os, sys, fnmatch
import time
import tokenize
import traceback
from pygettext import safe_eval, normalize, make_escapes

from interfaces import IPOTEntry, IPOTMaker, ITokenEater
from zope.interface import implements

__metaclass__ = type

DEFAULT_CHARSET = 'UTF-8'
DEFAULT_ENCODING = '8bit'

pot_header = '''\
##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
msgid ""
msgstr ""
"Project-Id-Version: %(version)s\\n"
"POT-Creation-Date: %(time)s\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: Zope 3 Developers <zope3-dev@zope.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=%(charset)s\\n"
"Content-Transfer-Encoding: %(encoding)s\\n"
"Generated-By: zope/app/translation_files/extract.py\\n"

'''

class POTEntry:
    """This class represents a single message entry in the POT file.
    """
    implements(IPOTEntry)

    def __init__(self, msgid, comments=None):
        self.msgid = msgid
        self.comments = comments or ''

    def addComment(self, comment):
        self.comments += comment + '\n'

    def addLocationComment(self, filename, line):
        self.comments += '#: %s:%s\n' %(filename, line)

    def write(self, file):
        file.write(self.comments)
        from zope.i18n.messageid import MessageID
        if isinstance(self.msgid, MessageID) and \
               self.msgid != self.msgid.default:
            default = self.msgid.default.strip()
            file.write('# Default: %s\n' % normalize(default))
        file.write('msgid %s\n' % normalize(self.msgid))
        file.write('msgstr ""\n')
        file.write('\n')

    def __cmp__(self, other):
        return cmp((self.comments, self.msgid), (other.comments, other.msgid))

class POTMaker:
    """This class inserts sets of strings into a POT file.
    """
    implements(IPOTMaker)
    
    def __init__ (self, output_fn, path):
        self._output_filename = output_fn
        self.path = path
        self.catalog = {}

    def add(self, strings, base_dir=None):
        for msgid, locations in strings.items():
            if msgid == '':
                continue
            if msgid not in self.catalog:
                self.catalog[msgid] = POTEntry(msgid)

            for filename, lineno in locations:
                if base_dir is not None:
                    filename = filename.replace(base_dir, '')
                self.catalog[msgid].addLocationComment(filename, lineno)

    def _getProductVersion(self):
        # First, try to get the product version
        fn = os.path.join(self.path, 'version.txt')
        if os.path.exists(fn):
            return open(fn, 'r').read().strip()
        # Second, try to find a Zope version
        import zope
        fn = os.path.join(os.path.dirname(zope.__file__), 'version.txt')
        if os.path.exists(fn):
            return open(fn, 'r').read().strip()
        else:
            return 'Zope 3 (unknown version)'

    def write(self):
        file = open(self._output_filename, 'w')
        file.write(pot_header % {'time':     time.ctime(),
                                 'version':  self._getProductVersion(),
                                 'charset':  DEFAULT_CHARSET,
                                 'encoding': DEFAULT_ENCODING})

        # Sort the catalog entries by filename
        catalog = self.catalog.values()
        catalog.sort()

        # Write each entry to the file
        for entry in catalog:
            entry.write(file)
            
        file.close()

class TokenEater:
    """This is almost 100% taken from pygettext.py, except that I
    removed all option handling and output a dictionary.

    >>> eater = TokenEater()
    >>> make_escapes(0)

    TokenEater eats tokens generated by the standard python module
    tokenize.

    >>> import tokenize
    >>> from StringIO import StringIO

    We feed it a (fake) file:

    >>> file = StringIO("_('hello', 'buenos dias')")
    >>> tokenize.tokenize(file.readline, eater)

    The catalog of collected message ids contains our example

    >>> catalog = eater.getCatalog()
    >>> catalog
    {u'hello': [(None, 1)]}

    The key in the catalog is not a unicode string, it's a real
    message id with a default value:

    >>> msgid = catalog.keys()[0]
    >>> msgid
    u'hello'
    >>> msgid.default
    u'buenos dias'

    Note that everything gets converted to unicode.
    """
    implements(ITokenEater)
    
    def __init__(self):
        self.__messages = {}
        self.__state = self.__waiting
        self.__data = []
        self.__lineno = -1
        self.__freshmodule = 1
        self.__curfile = None

    def __call__(self, ttype, tstring, stup, etup, line):
        self.__state(ttype, tstring, stup[0])

    def __waiting(self, ttype, tstring, lineno):
        if ttype == tokenize.NAME and tstring in ['_']:
            self.__state = self.__keywordseen

    def __suiteseen(self, ttype, tstring, lineno):
        # ignore anything until we see the colon
        if ttype == tokenize.OP and tstring == ':':
            self.__state = self.__suitedocstring

    def __suitedocstring(self, ttype, tstring, lineno):

        # ignore any intervening noise
        if ttype == tokenize.STRING:
            self.__addentry(safe_eval(tstring), lineno, isdocstring=1)
            self.__state = self.__waiting
        elif ttype not in (tokenize.NEWLINE, tokenize.INDENT,
                           tokenize.COMMENT):
            # there was no class docstring
            self.__state = self.__waiting

    def __keywordseen(self, ttype, tstring, lineno):
        if ttype == tokenize.OP and tstring == '(':
            self.__data = []
            self.__msgid = ''
            self.__lineno = lineno
            self.__state = self.__openseen
        else:
            self.__state = self.__waiting

    def __openseen(self, ttype, tstring, lineno):
        if ttype == tokenize.OP and tstring == ')':
            # We've seen the last of the translatable strings.  Record the
            # line number of the first line of the strings and update the list 
            # of messages seen.  Reset state for the next batch.  If there
            # were no strings inside _(), then just ignore this entry.
            if self.__data or self.__msgid:
                if self.__msgid:
                    msgid = self.__msgid
                    default = ''.join(self.__data)
                else:
                    msgid = ''.join(self.__data)
                    default = None
                self.__addentry(msgid, default)
            self.__state = self.__waiting
        elif ttype == tokenize.OP and tstring == ',':
            self.__msgid = ''.join(self.__data)
            self.__data = []
        elif ttype == tokenize.STRING:
            self.__data.append(safe_eval(tstring))

    def __addentry(self, msg, default=None, lineno=None, isdocstring=0):
        if lineno is None:
            lineno = self.__lineno

        if default is not None:
            from zope.i18n.messageid import MessageID
            msg = MessageID(msg, default=default)
        entry = (self.__curfile, lineno)
        self.__messages.setdefault(msg, {})[entry] = isdocstring

    def set_filename(self, filename):
        self.__curfile = filename
        self.__freshmodule = 1

    def getCatalog(self):
        catalog = {}
        # Sort the entries.  First sort each particular entry's keys, then
        # sort all the entries by their first item.
        reverse = {}
        for k, v in self.__messages.items():
            keys = v.keys()
            keys.sort()
            reverse.setdefault(tuple(keys), []).append((k, v))
        rkeys = reverse.keys()
        rkeys.sort()
        for rkey in rkeys:
            rentries = reverse[rkey]
            rentries.sort()
            for msgid, locations in rentries:
                catalog[msgid] = []
                
                locations = locations.keys()
                locations.sort()

                for filename, lineno in locations:
                    catalog[msgid].append((filename, lineno))

        return catalog

def find_files(dir, pattern, exclude=()):
    files = []

    def visit(files, dirname, names):
        files += [os.path.join(dirname, name)
                  for name in fnmatch.filter(names, pattern)
                  if name not in exclude]
        
    os.path.walk(dir, visit, files)
    return files

def py_strings(dir, domain="zope"):
    """Retrieve all Python messages from dir that are in the domain.
    """
    eater = TokenEater()
    make_escapes(0)
    for filename in find_files(dir, '*.py', 
                               exclude=('extract.py', 'pygettext.py')):
        fp = open(filename)
        try:
            eater.set_filename(filename)
            try:
                tokenize.tokenize(fp.readline, eater)
            except tokenize.TokenError, e:
                print >> sys.stderr, '%s: %s, line %d, column %d' % (
                    e[0], filename, e[1][0], e[1][1])
        finally:
            fp.close()            
    # XXX: No support for domains yet :(
    return eater.getCatalog()

def zcml_strings(dir, domain="zope"):
    """Retrieve all ZCML messages from dir that are in the domain.
    """
    from zope.app._app import config
    import zope
    dirname = os.path.dirname
    site_zcml = os.path.join(dirname(dirname(dirname(zope.__file__))),
                             "site.zcml")
    context = config(site_zcml, execute=False)
    return context.i18n_strings.get(domain, {})

def tal_strings(dir, domain="zope", include_default_domain=False):
    """Retrieve all TAL messages from dir that are in the domain.
    """
    # We import zope.tal.talgettext here because we can't rely on the
    # right sys path until app_dir has run
    from zope.tal.talgettext import POEngine, POTALInterpreter
    from zope.tal.htmltalparser import HTMLTALParser
    engine = POEngine()

    class Devnull:
        def write(self, s):
            pass

    for filename in find_files(dir, '*.pt'):
        try:
            engine.file = filename
            p = HTMLTALParser()
            p.parseFile(filename)
            program, macros = p.getCode()
            POTALInterpreter(program, macros, engine, stream=Devnull(),
                             metal=False)()
        except: # Hee hee, I love bare excepts!
            print 'There was an error processing', filename
            traceback.print_exc()

    # See whether anything in the domain was found
    if not engine.catalog.has_key(domain):
        return {}
    # We do not want column numbers.
    catalog = engine.catalog[domain].copy()
    # When the Domain is 'default', then this means that none was found;
    # Include these strings; yes or no?
    if include_default_domain:
        catalog.update(engine.catalog['default'])
    for msgid, locations in catalog.items():
        catalog[msgid] = map(lambda l: (l[0], l[1][0]), locations)
    return catalog
