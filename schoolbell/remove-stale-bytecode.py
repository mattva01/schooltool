#!/usr/bin/env python
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
Recursively removes .pyc and .pyo files without a corresponding .py file.

Usage: %(progname)s [options] [dirname ...]

Options:
    -h, --help      this message
    -v, --verbose   print names of files before they are removed (default)
    -q, --quiet     the opposite of --verbose
    -n, --dry-run   do not actually remove the files (implies --verbose)

If dirname is ommitted, %(progname)s starts looking for stale
bytecode files in the current directory.
"""

import os
import sys
import getopt


def main(argv=sys.argv):
    progname = os.path.basename(argv[0])
    helpmsg = __doc__.strip() % {'progname': progname}
    verbose = True
    dry_run = False
    try:
        opts, args = getopt.getopt(argv[1:], 'vqnh',
                                   ['verbose', 'quiet', 'dry-run', 'help'])
    except getopt.error, e:
        print >> sys.stderr, e
        print >> sys.stderr, 'try %s --help' % progname
        sys.exit(1)
    for k, v in opts:
        if k in ('-v', '--verbose'):
            verbose = True
        elif k in ('-q', '--quiet'):
            verbose = False
        elif k in ('-n', '--dry-run'):
            dry_run = True
            verbose = True
        elif k in ('-h', '--help'):
            print helpmsg
            sys.exit(0)
    if not args:
        args = ['.']
    for root in args:
        for dirpath, dirnames, filenames in os.walk(root):
            filenames = map(os.path.normcase, filenames)
            for filename in filenames:
                if filename.endswith('.pyc') or filename.endswith('pyo'):
                    sourcename = filename[:-1]
                    if sourcename not in filenames:
                        fullname = os.path.join(dirpath, filename)
                        if verbose:
                            print "Removing", fullname
                        if not dry_run:
                            try:
                                os.unlink(fullname)
                            except os.error, e:
                                print >> sys.stderr, ("%s: %s: %s" %
                                                      (progname, fullname, e))


if __name__ == '__main__':
    main()
