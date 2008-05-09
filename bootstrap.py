##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

"""
import os, shutil, sys, tempfile, urllib2

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

def mkdir(path):
    if not os.path.exists(path):
        print 'Creating %s' % path
        os.makedirs(path)

def symlink(src, dest):
    if not os.path.exists(dest):
        os.symlink(src, dest)
    else:
        print 'Symlink %s already exists' % dest


def rmtree(dir):
    if os.path.exists(dir):
        print 'Deleting tree %s' % dir
        shutil.rmtree(dir)

def make_exe(fn):
    if os.name == 'posix':
        oldmode = os.stat(fn).st_mode & 07777
        newmode = (oldmode | 0555) & 07777
        os.chmod(fn, newmode)

def make_virtual_python():
    if os.name != 'posix':
        print "This script only works on Unix-like platforms, sorry."
        return

    lib_dir = join('python', 'lib', py_version)
    inc_dir = join('python', 'include', py_version)
    bin_dir = join('python', 'bin')

    if sys.executable.startswith(bin_dir):
        print 'Please use the *system* python to run this script'
        return

    mkdir('python')
    prefix = sys.prefix
    mkdir(lib_dir)
    stdlib_dir = join(prefix, 'lib', py_version)
    for fn in os.listdir(stdlib_dir):
        if fn != 'site-packages':
            symlink(join(stdlib_dir, fn), join(lib_dir, fn))

    mkdir(join(lib_dir, 'site-packages'))

    mkdir(inc_dir)
    stdinc_dir = join(prefix, 'include', py_version)
    for fn in os.listdir(stdinc_dir):
        symlink(join(stdinc_dir, fn), join(inc_dir, fn))

    if sys.exec_prefix != sys.prefix:
        exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            symlink(join(exec_dir, fn), join(lib_dir, fn))

    mkdir(bin_dir)
    print 'Copying %s to %s' % (sys.executable, bin_dir)
    py_executable = join(bin_dir, 'python')
    if sys.executable != py_executable:
        shutil.copyfile(sys.executable, py_executable)
        make_exe(py_executable)


if __name__ == "__main__":
    if sys.executable != os.path.abspath('python/bin/python'):
        make_virtual_python()
        sys.exit(os.spawnve(
                os.P_WAIT, 'python/bin/python',
                ['python/bin/python'] + sys.argv, os.environ))

    tmpeggs = tempfile.mkdtemp()

    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

    cmd = 'from setuptools.command.easy_install import main; main()'
    if sys.platform == 'win32':
        cmd = '"%s"' % cmd # work around spawn lamosity on windows

    ws = pkg_resources.working_set
    assert os.spawnle(
        os.P_WAIT, sys.executable, sys.executable,
        '-c', cmd, '-mqNxd', tmpeggs, 'zc.buildout',
        dict(os.environ,
             PYTHONPATH=
             ws.find(pkg_resources.Requirement.parse('setuptools')).location
             ),
        ) == 0

    ws.add_entry(tmpeggs)
    ws.require('zc.buildout')
    import zc.buildout.buildout
    zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
    shutil.rmtree(tmpeggs)
