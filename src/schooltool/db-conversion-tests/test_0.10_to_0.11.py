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
Functional test for migrating from v. 0.10 to 0.11

$Id$
"""
import os
import sys
import shutil
import tempfile

tempdir = tempfile.mkdtemp()

mydir = os.path.dirname(sys.argv[0])
shutil.copy(os.path.join(mydir, 'Data.fs-0.10'),
            os.path.join(tempdir, 'Data.fs'))

script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
basedir = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))

sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

os.chdir(tempdir)
import schooltool.main
schooltool.main.StandaloneServer().main()
