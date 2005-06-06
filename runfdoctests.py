#!/usr/bin/env python
"""Hacky script for a fast feedback loop with SchoolTool's functional tests.

The problem with functional doctests is that the initial setup (ZCML parsing
etc.) takes ages, and then your brand new and shiny functional doctest fails
because of a silly typo.  You fix the typo and wait 30 seconds to find another
one.  The feedback loop is just too slow for efficient development.

Hence this script.  Run it in the root of your SchoolTool source tree, and
enter a pathname of a functional doctest file at the prompt.  When you get
that proverbial silly typo on line 17, just fix it and use readline's history
to rerun the same test file.  You'll get feedback in seconds.
"""

import os
import sys
import time
import glob
import unittest
import readline


def main():
    args = sys.argv[1:]

    # Hack hack hack!
    sys.path.insert(0, os.path.abspath('src')) # breaks horribly without os.path.abspath
    sys.path.insert(0, os.path.abspath('Zope3/src'))
    # Load and set up Zope 3.
    start = time.time()
    print "Bringing up Zope 3 (wait 20 seconds or so)"
    from zope.app.testing.functional import FunctionalTestSetup
    from zope.app.testing.functional import FunctionalDocFileSuite
    FunctionalTestSetup('ftesting.zcml')
    elapsed = time.time() - start
    print "Setup ate %.3f seconds" % elapsed

    from zope.testing import doctest
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)

    try:
        testdir = 'src/schooltool/browser/ftests'
        print "Try test scripts in %s:" % testdir
        fns = glob.glob('%s/*.txt' % testdir)
        fns.sort()
        print "\n".join(fns)
        print
        while True:
            if args:
                # Process command line arguments first, then go into
                # interactive mode
                filename = args.pop(0)
                readline.add_history(filename)
                print "fdoctest file name>", filename
            else:
                filename = raw_input("fdoctest file name> ")
            if not filename:
                print "^D to exit"
            elif filename == 'pdb':
                import pdb; pdb.set_trace()
            else:
                try:
                    suite = FunctionalDocFileSuite(filename,
                                                   optionflags=optionflags)
                    run(suite)
                except Exception, e:
                    import traceback
                    traceback.print_exc()
    except (KeyboardInterrupt, EOFError):
        print "Bye!"


def run(suite):
    try:
        from test import CustomTestRunner, Options, Colorizer, light_colormap
    except ImportError:
        runner = unittest.TextTestRunner()
    else:
        cfg = Options()
        cfg.colorizer = Colorizer(light_colormap)
        runner = CustomTestRunner(cfg, [])
    runner.run(suite)

if __name__ == '__main__':
    main()
