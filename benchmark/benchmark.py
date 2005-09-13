"""
Utilities for SchoolTool's benchmarks.

Use with care (plays with sys.path).
"""

import sys
import os
import time
import textwrap

basedir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

from zope.app.testing.functional import FunctionalTestSetup
from zope.app.testing.functional import HTTPCaller
from schoolbell.app.browser.ftests.test_all import find_ftesting_zcml


def measure(fn):
    """Measure the running time of `fn` in seconds (very crudely)."""
    t0 = time.time()
    fn()
    return time.time() - t0


def benchmark(title, fn, count=5):
    """Benchmark a function."""
    print title
    times = []
    for n in range(count):
        time = measure(fn)
        print "  %.3f seconds" % time
        times.append(time)


def http(indented_request_string, http_caller=HTTPCaller()):
    """Dedent the request string and perform the HTTP request."""
    rq = textwrap.dedent(indented_request_string).strip()
    return http_caller(rq, handle_errors=False)


def load_ftesting_zcml():
    """Load ZCML.

    First call is expensive, subsequent calls are virtually free.
    """
    return FunctionalTestSetup(find_ftesting_zcml())

