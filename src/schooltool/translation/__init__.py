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
  gettext       alias for catalog.gettext
  ugettext      alias for catalog.ugettext

Example usage:

  from schooltool.translations import gettext as _
  print _("Translated message")

Note that SchoolTool server mostly deals with Unicode strings and thus should
use ugettext, while the clients use 8-bit strings in locale encoding and thus
should use gettext.


The following files were taken from Zope 3 CVS (src/zope/app/translation_files)
and have their own copyright notices:

  - extract.py
  - pygettext.py
  - interfaces.py
  - i18nextract.py

"""

import os
import gettext


localedir = os.path.dirname(__file__)
catalog = gettext.translation('schooltool', localedir, fallback=True)
gettext = catalog.gettext
ugettext = catalog.ugettext
