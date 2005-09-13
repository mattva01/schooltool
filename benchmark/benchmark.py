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
    # Yes, I know that we're supposed to use the timeit module here, but its
    # API is inconvenient, and we do not need a lot of precision here.
    t0 = time.time()
    fn()
    return time.time() - t0


def mean(seq):
    """Compute the mean of a sequence."""
    return sum(seq) / len(seq)


def stddev(seq):
    """Compute the standard deviation of a sequence."""
    avg = mean(seq)
    variance = sum((x - avg) ** 2 for x in seq) / len(seq)
    return variance ** 0.5


def benchmark(title, fn, count=5):
    """Benchmark a function."""
    print title
    times = []
    for n in range(count):
        time = measure(fn)
        print "  %.3f seconds" % time
        times.append(time)
    # Note: do not pay much attention to the statistical significance of these
    # values -- see the timeit module documentation.
    print ("    min = %.3f, max = %.3f, mean = %.3f, stddev = %.3f"
           % (min(times), max(times), mean(times), stddev(times)))


def http(indented_request_string, http_caller=HTTPCaller()):
    """Dedent the request string and perform the HTTP request."""
    rq = textwrap.dedent(indented_request_string).strip()
    return http_caller(rq, handle_errors=False)


def load_ftesting_zcml():
    """Load ZCML.

    First call is expensive, subsequent calls are virtually free.
    """
    return FunctionalTestSetup(find_ftesting_zcml())

