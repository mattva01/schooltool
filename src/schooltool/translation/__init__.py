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

  localedir     location of message catalogs
  catalog       catalog of translations for domain 'schooltool'
  ugettext      alias for catalog.ugettext
  gettext       wrapper around ugettext that performs charset conversion

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
import gettext as _gettext
from schooltool.common import to_locale


localedir = os.path.dirname(__file__)
catalog = _gettext.translation('schooltool', localedir, fallback=True)


def ugettext(str):
    """Translate a message.

    Returns a Unicode string.
    """
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
    """
    global catalog
    global ugettext
    catalog = _gettext.translation(domain, localedir, languages,
                                   fallback=True)
    ugettext = catalog.ugettext
