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
SchoolTool translations.

The following names are available in this module:

  ugettext      translate a message
  gettext       wrapper around ugettext that performs charset conversion
  setCatalog    choose a translation domain and translation language

  TranslatableString
                a class that pretends (imperfectly) to be a unicode string
                and performs translations on the fly.

Example usage:

  import sys
  from schooltool.common import StreamWrapper
  from schooltool.translations import ugettext as _
  sys.stdout = StreamWrapper(sys.stdout)
  print _("Translated message")

You should prefer ugettext to gettext unless you're really sure you will need
the string in locale encoding.  Output to the console does not use locale
encoding on Windows.  wxPython does not use locale encoding on Windows, nor on
Gtk2.  Output to a text file uses locale encoding everywhere.




The following files were taken from Zope 3 CVS (src/zope/app/translation_files)
and have their own copyright notices:

  - extract.py
  - pygettext.py
  - interfaces.py
  - i18nextract.py

"""

import os
import sys
import sets
import gettext as _gettext
from schooltool.common import to_locale
from schooltool import translation_prefix


localedir = translation_prefix
if localedir is None:
    localedir = os.path.dirname(__file__)
catalog = _gettext.translation('schooltool', localedir, fallback=True)

debug_overeager_translations = False
    # If set to True, ugettext will remember which places in the source code
    # called ugettext before setCatalog was called, and setCatalog will print
    # a list of those places to stderr.  Calling setCatalog turns this switch
    # off.

_overeager_translations = sets.Set()


def ugettext(str):
    """Translate a message.

    Returns a Unicode string.

    Warning: if you call ugettext in global scope or inside class definition,
    the string will be translated immediatelly.  Any further calls to
    setCatalog will *not* change that translation.  If you want setCatalog to
    take effect on strings defined in these scopes, use TranslatableString
    instead.
    """
    if debug_overeager_translations:
        import sys
        frame = sys._getframe(1)
        filename = frame.f_globals['__file__']
        if filename.endswith('.pyc') or filename.endswith('.pyo'):
            filename = filename[:-1]
        lineno = frame.f_lineno
        _overeager_translations.add((filename, lineno))
    global catalog
    # Uncomment the following line to decorate all translatable strings -- then
    # all untranslated strings will stand out:
    #   return u'\u00AB%s\u00BB' % catalog.ugettext(str)
    return catalog.ugettext(str)


def gettext(msgid):
    """Translate a message and convert it to locale encoding."""
    return to_locale(ugettext(msgid))


def setCatalog(domain, languages=None):
    """Set the domain and languages used for message lookup.

    Domain is usually the name of the application ('schooltool' or
    'schoolbell').

    Languages, if specified, override the default gettext language selection
    (e.g., the environment variables LANGUAGES, LC_ALL, LC_MESSAGES, LANG on
    POSIX systems).

    Warning: if you call ugettext in global scope or inside class definition,
    the string will be translated immediatelly.  Any further calls to
    setCatalog will *not* change that translation.  If you want setCatalog to
    take effect on strings defined in these scopes, use TranslatableString
    instead.
    """
    global catalog
    catalog = _gettext.translation(domain, localedir, languages,
                                   fallback=True)
    global debug_overeager_translations
    if debug_overeager_translations:
        debug_overeager_translations = False
        offenders = list(_overeager_translations)
        if offenders:
            print >> sys.stderr, "DEBUG: ugettext called too early in"
            offenders.sort()
            for filename, lineno in offenders:
                print >> sys.stderr, "  %s:%d" % (filename, lineno)
            _overeager_translations.clear()


class TranslatableString(object):
    """Delayed translation.

    TranslatableString tries to pretent do be a unicode string and performs
    translation when you use it.  Due to limitations in Python, the following
    opetations will not work on translatable strings:

        "".join([TranslatableString(...)])
        TranslatableString(...) in "a string"
        "a string: %s" % TranslatableString(...)
        print TranslatableString(...)

    You must explicitly convert TranslatableStrings to unicode:

        "".join(map(unicode, [TranslatableString(...)]))
        unicode(TranslatableString(...)) in "a string"
        "a string: %s" % unicode(TranslatableString(...))
        print unicode(TranslatableString(...))

    """

    def __init__(self, msgid):
        self.msgid = msgid

    def __repr__(self):
        return "_(%r)" % self.msgid

    def __unicode__(self):
        return ugettext(self.msgid)

    def __str__(self):
        return unicode(self)

    # Simple wrappers

    def __int__(self): return int(unicode(self))
    def __long__(self): return long(unicode(self))
    def __float__(self): return float(unicode(self))
    def __getitem__(self, idx): return unicode(self)[idx]
    def __eq__(self, other): return unicode(self) == other
    def __ne__(self, other): return unicode(self) != other
    def __lt__(self, other): return unicode(self) < other
    def __gt__(self, other): return unicode(self) > other
    def __le__(self, other): return unicode(self) <= other
    def __ge__(self, other): return unicode(self) >= other
    def __hash__(self): return hash(unicode(self))
    def __len__(self): return len(unicode(self))
    def __contains__(self, substring): return substring in unicode(self)
    def __add__(self, other): return unicode(self) + other
    def __radd__(self, other): return other + unicode(self)
    def __mul__(self, other): return unicode(self) * other
    def __mod__(self, args): return unicode(self) % args

    def __getattr__(self, attr):
        if attr == 'msgid':
            return object.__getattr__(self, attr)
        else:
            return getattr(unicode(self), attr)

