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
import tokenize

from zope.i18nmessageid.message import MessageFactory
from zope.app.locales.pygettext import make_escapes
from zope.app.locales.extract import find_files

_import_chickens = {}, {}, ("*",) # dead chickens needed by __import__

here = os.path.abspath(os.path.dirname(__file__))

# Remove this directory from path:
# (prevents conflicts between python's test module and the test runner)
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != here]
# Lets add the Zope and schooltool paths to sys.path
zope3 = os.path.join(here, 'Zope3', 'src')
sys.path.insert(0, zope3)
st = os.path.join(here, 'src')
sys.path.insert(0, st)

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

def get_version():
    version_file = os.path.join('src', 'schooltool', 'version.txt')
    f = open(version_file, 'r')
    result = f.read()
    f.close()
    return result

class POTMaker(extract.POTMaker):

    def _getProductVersion(self):
        return "SchoolTool Version %s" % get_version()

def py_strings(dir, domain="zope", exclude=()):
    """Retrieve all Python messages from `dir` that are in the `domain`.
    """
    eater = extract.TokenEater()
    make_escapes(0)
    for filename in find_files(
            dir, '*.py', exclude=('extract.py', 'pygettext.py')+tuple(exclude)):

        common_path_lengths = [
            len(os.path.commonprefix([os.path.abspath(filename), path]))
            for path in sys.path]
        l = sorted(common_path_lengths)[-1]
        import_name = filename[l+1:-3].replace("/", ".").replace(".__init__", "")

        try:
            module = __import__(import_name, *_import_chickens)
        except ImportError, e:
            # XXX if we can't import it - we assume that the domain is
            # the right one
            print "Could not import %s" % import_name
        else:
            mf = getattr(module, '_', None)
            # XXX if _ is not a MessageFactory, we assume that the
            # domain is the right one, thus strings in
            # schooltool.app.main will be in all the pot files
            if isinstance(mf, MessageFactory):
                if mf._domain != domain:
                    # domain mismatch - skip
                    continue

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
    return eater.getCatalog()

def write_pot(output_dir, path, domain, base_dir, site_zcml):
    # Create the POT
    output_file = os.path.join(path, output_dir, domain + '.pot')
    maker = POTMaker(output_file, path)
    maker.add(py_strings(path, domain), base_dir)
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
