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

The following files were taken from Zope 3 CVS (src/zope/app/translation_files)
and have their own copyright notices:

  - extract.py
  - pygettext.py
  - interfaces.py
  - i18nextract.py

"""

from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup


def setUp():
    """Initialize SchoolTool translations.

    Note that this function installs _ into the built-in namespace.
    """
    import os
    import gettext
    localedir = os.path.dirname(__file__)
    gettext.install('schooltool', localedir)


moduleProvides(IModuleSetup)
