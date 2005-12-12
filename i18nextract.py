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
Customization of Zope's message string extraction module for schooltool and
schoolbell.

This is just a very simple script to be run from within an un-packed and built
schooltool checkout.

$Id$
"""
import os
import sys

here = os.path.abspath(os.path.dirname(__file__))

# Lets add the Zope and schooltool paths to sys.path
zope3 = os.path.join(here, 'Zope3', 'src')
sys.path.insert(0, zope3)
st = os.path.join(here, 'src')
sys.path.insert(0, st)

import schooltool
from zope.app.locales import extract

# Monkey patch the Zope3 translation extraction machinery
extract.pot_header = """\
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005    Shuttleworth Foundation
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
msgid ""
msgstr ""
"Project-Id-Version: %(version)s\\n"
"POT-Creation-Date: %(time)s\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: Schooltool Development Team <schooltool-dev@schooltool.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=%(charset)s\\n"
"Content-Transfer-Encoding: %(encoding)s\\n"
"Generated-By: i18nextract.py\\n"

"""

class POTMaker(extract.POTMaker):

    def _getProductVersion(self):
        return "SchoolTool Version %s" % schooltool.VERSION

def write_pot(output_dir, path, domain, base_dir, site_zcml):
    # Create the POT
    output_file = os.path.join(path, output_dir, domain + '.pot')
    maker = POTMaker(output_file, path)
    maker.add(extract.py_strings(path, domain), base_dir)
    maker.add(extract.zcml_strings(path, domain, site_zcml=site_zcml), base_dir)
    maker.add(extract.tal_strings(path, domain), base_dir)
    maker.write()

if __name__ == '__main__':
    here = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(here, 'src')
    base_dir = here # Comments are relative to the source checkouts so we are
                    # sure we don't have any absolute paths in there.
    output_dir = os.path.join(here, 'src', 'schooltool', 'locales')
    # SchoolTool
    domain = 'schooltool'
    site_zcml = os.path.join(here, 'schooltool-skel', 'etc', 'site.zcml')
    write_pot(output_dir, path, domain, base_dir, site_zcml)
    print 'Extracted %s.pot to %s' % (domain, output_dir)
    # SchoolBell
    domain = 'schoolbell'
    site_zcml = os.path.join(here, 'schoolbell-site.zcml')
    write_pot(output_dir, path, domain, base_dir, site_zcml)
    print 'Extracted %s.pot to %s' % (domain, output_dir)
