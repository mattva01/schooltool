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
Customization of Zope's message string extraction module

$Id$
"""
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
"Generated-By: setup.py\\n"

"""

class POTMaker(extract.POTMaker):

    def _getProductVersion(self):
        return "SchoolTool Version %s" % schooltool.VERSION


def build_pot():
    """Build the *.pot."""
    # where is eveything
    here = os.path.abspath(os.path.dirname(__file__))
    domain = 'schooltool'
    path = os.path.join(here, 'src')
    output_dir = os.path.join(here, 'src', 'schooltool', 'locales')
    base_dir = os.path.join(here, 'src', 'schooltool')

    # Setup
    (zcml, zcml_filename) = tempfile.mkstemp()
    file = open(zcml_filename, 'w')
    file.write("""<configure xmlns="http://namespaces.zope.org/zope">
                     <include package="zope.app" />
                     <include package="zope.app.wfmc" file="meta.zcml" />
                     <include package="schooltool" />
                  </configure>""")
    file.close()

    output_file = os.path.join(path, output_dir, domain + '.pot')

    # Create the POT
    maker = POTMaker(output_file, path)
    maker.add(extract.py_strings(path, domain), base_dir)
    maker.add(extract.zcml_strings(path, domain, site_zcml=zcml_filename), base_dir)
    maker.add(extract.tal_strings(path, domain), base_dir)
    maker.write()

    # Cleanup
    os.remove(zcml_filename)
