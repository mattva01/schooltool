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
Run schooltool with given Data.fs

$Id$
"""
import os
import sys
import shutil
import tempfile

def runSchoolToolWith(datafs):
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    basedir = os.path.abspath(
        os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))

    tempdir = tempfile.mkdtemp()
    skeldir = os.path.join(tempdir, 'schooltool-skel')
    os.mkdir(skeldir)

    mydir = os.path.dirname(sys.argv[0])
    topskeldir = os.path.join(basedir, 'schooltool-skel')
    shutil.copytree(os.path.join(topskeldir, 'bin'),
                    os.path.join(skeldir, 'bin'))
    shutil.copytree(os.path.join(topskeldir, 'etc'),
                    os.path.join(skeldir, 'etc'))
    logdir = os.path.join(skeldir, 'log')
    os.mkdir(logdir)
    open(os.path.join(logdir, 'schooltool.log'), 'w')
    datafsdir = os.path.join(skeldir, 'var')
    os.mkdir(datafsdir)
    shutil.copy(os.path.join(mydir, datafs),
                os.path.join(datafsdir, 'Data.fs'))

    sys.path.insert(0, os.path.join(basedir, 'src'))
    z3dir = os.path.join(basedir, 'Zope3', 'src')
    sys.path.insert(0, z3dir)
    import site
    site.addsitedir(z3dir)

    os.chdir(tempdir)
    from schooltool.app.main import StandaloneServer
    StandaloneServer().main()
