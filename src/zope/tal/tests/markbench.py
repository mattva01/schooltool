#! /usr/bin/env python
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
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
"""Run benchmarks of TAL vs. DTML

$Id$
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
os.environ['NO_SECURITY'] = 'true'

import getopt
import sys
import time

from cStringIO import StringIO

#from zope.documenttemplate.dt_html import HTMLFile

from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talinterpreter import TALInterpreter
from zope.tal.dummyengine import DummyEngine


def time_apply(f, args, kwargs, count):
    r = [None] * count
    for i in range(4):
        f(*args, **kwargs)
    t0 = time.clock()
    for i in r:
        pass
    t1 = time.clock()
    for i in r:
        f(*args, **kwargs)
    t = time.clock() - t1 - (t1 - t0)
    return t / count

def time_zpt(fn, count):
    from zope.pagetemplate.pagetemplate import PageTemplate
    pt = PageTemplate()
    pt.write(open(fn).read())
    return time_apply(pt.pt_render, (data,), {}, count)

def time_tal(fn, count):
    p = HTMLTALParser()
    p.parseFile(fn)
    program, macros = p.getCode()
    engine = DummyEngine(macros)
    engine.globals = data
    tal = TALInterpreter(program, macros, engine, StringIO(), wrap=0,
                         tal=1, strictinsert=0)
    return time_apply(tal, (), {}, count)

def time_dtml(fn, count):
    html = HTMLFile(fn)
    return time_apply(html, (), data, count)

def profile_zpt(fn, count, profiler):
    from zope.pagetemplate.pagetemplate import PageTemplate
    pt = PageTemplate()
    pt.write(open(fn).read())
    for i in range(4):
        pt.pt_render(extra_context=data)
    r = [None] * count
    for i in r:
        profiler.runcall(pt.pt_render, 0, data)

def profile_tal(fn, count, profiler):
    p = HTMLTALParser()
    p.parseFile(fn)
    program, macros = p.getCode()
    engine = DummyEngine(macros)
    engine.globals = data
    tal = TALInterpreter(program, macros, engine, StringIO(), wrap=0,
                         tal=1, strictinsert=0)
    for i in range(4):
        tal()
    r = [None] * count
    for i in r:
        profiler.runcall(tal)

# Figure out where the benchmark files are:
try:
    fname = __file__
except NameError:
    fname = sys.argv[0]
taldir = os.path.dirname(os.path.dirname(os.path.abspath(fname)))
benchdir = os.path.join(taldir, 'benchmark')

# Construct templates for the filenames:
tal_fn = os.path.join(benchdir, 'tal%.2d.html')
dtml_fn = os.path.join(benchdir, 'dtml%.2d.html')

def compare(n, count, profiler=None, verbose=1):
    if verbose:
        t1 = int(time_zpt(tal_fn % n, count) * 1000 + 0.5)
        t2 = int(time_tal(tal_fn % n, count) * 1000 + 0.5)
        t3 = 'n/a' # int(time_dtml(dtml_fn % n, count) * 1000 + 0.5)
        print '%.2d: %10s %10s %10s' % (n, t1, t2, t3)
    if profiler:
        profile_tal(tal_fn % n, count, profiler)

def main(count, profiler=None, verbose=1):
    n = 1
    if verbose:
        print '##: %10s %10s %10s' % ('ZPT', 'TAL', 'DTML')
    while os.path.isfile(tal_fn % n) and os.path.isfile(dtml_fn % n):
        compare(n, count, profiler, verbose)
        n = n + 1

def get_signal_name(sig):
    import signal
    for name in dir(signal):
        if getattr(signal, name) == sig:
            return name
    return None

data = {'x':'X', 'r2': range(2), 'r8': range(8), 'r64': range(64)}
for i in range(10):
    data['x%s' % i] = 'X%s' % i

if __name__ == "__main__":
    filename = "markbench.prof"
    profiler = None
    runtests = False
    verbose = True

    opts, args = getopt.getopt(sys.argv[1:], "pqt")
    for opt, arg in opts:
        if opt == "-p":
            import profile
            profiler = profile.Profile()
        elif opt == "-q":
            verbose = False
        elif opt == "-t":
            runtests = True

    if runtests:
        srcdir = os.path.dirname(os.path.dirname(taldir))
        topdir = os.path.dirname(srcdir)
        pwd = os.getcwd()
        os.chdir(topdir)
        rc = os.spawnl(os.P_WAIT, sys.executable,
                       sys.executable, "test.py", "zope.tal.tests")
        if rc > 0:
            # TODO: Failing tests don't cause test.py to report an
            # error; not sure why.  ;-(
            sys.exit(rc)
        elif rc < 0:
            sig = -rc
            print >>sys.stderr, (
                "Process exited, signal %d (%s)."
                % (sig, get_signal_name(sig) or "<unknown signal>"))
            sys.exit(1)
        os.chdir(pwd)

    if len(args) >= 1:
        for arg in args:
            compare(int(arg), 25, profiler, verbose)
    else:
        main(25, profiler, verbose)

    if profiler is not None:
        profiler.dump_stats(filename)
        import pstats
        p = pstats.Stats(filename)
        p.strip_dirs()
        p.sort_stats('time', 'calls')
        try:
            p.print_stats(20)
        except IOError, e:
            if e.errno != errno.EPIPE:
                raise
