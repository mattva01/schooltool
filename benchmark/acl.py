#!/usr/bin/python
"""
Benchmark the ACL view.
"""

import sys
import os
import time
import random
import timeit
import urllib
import textwrap

basedir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

import transaction
from zope.app.testing.functional import FunctionalTestSetup
from zope.app.testing.functional import HTTPCaller

from schoolbell.app.browser.ftests.test_all import find_ftesting_zcml
from schoolbell.app.app import Person, Group


def http(indented_request_string, http_caller=HTTPCaller()):
    """Dedent the request string and perform the HTTP request."""
    rq = textwrap.dedent(indented_request_string).strip()
    return http_caller(rq, handle_errors=False)


def load_ftesting_zcml():
    """Load ZCML.

    First call is expensive, subsequent calls are virtually free.
    """
    return FunctionalTestSetup(find_ftesting_zcml())


def setup_benchmark():
    """Create an SB application and populate with users and groups."""
    setup = load_ftesting_zcml()
    r = http(r"""
         POST /@@contents.html HTTP/1.1
         Authorization: Basic mgr:mgrpw
         Content-Type: application/x-www-form-urlencoded

         type_name=BrowserAdd__schoolbell.app.app.SchoolBellApplication&new_value=frogpond
    """)
    assert r.getStatus() == 303

    app = setup.getRootFolder()['frogpond']
    create_random_users_and_groups(app)
    transaction.commit()

    r = http(r"""
        GET /frogpond/persons HTTP/1.1
        Authorization: Basic mgr:mgrpw
    """)
    assert r.getStatus() == 200


def create_random_users_and_groups(app, count=100, seed=42):
    """Create some randomly named users and groups."""
    rng = random.Random(seed)
    groups = []
    for i in range(count):
        group = Group('title%s' % i)
        groups.append(group)
        app['groups']['title%s' % i] = group
    for i in range(count):
        person = Person('username%s' % i, 'title%s' % i)
        name = person.username
        app['persons'][name] = person
        for j in range(10):
            try:
                person.groups.add(rng.choice(groups))
            except:
                pass


def do_benchmark_render():
    """Benchmark the ACL view."""
    r = http(r"""
         GET /frogpond/acl.html HTTP/1.1
         Authorization: Basic mgr:mgrpw
    """)
    assert r.getStatus() == 200


def do_benchmark_update(n_users_in_form=10):
    """Benchmark the ACL view."""
    form = {'UPDATE_SUBMIT': 'Set'}
    for n in range(n_users_in_form):
        form['marker-sb.person.username%d' % n] = '1'
        form['sb.person.username%d' % n] = ['schoolbell.view',
                                            'schoolbell.edit']
    formdata = urllib.urlencode(form)
    r = http(r"""
         POST /frogpond/acl.html HTTP/1.1
         Authorization: Basic mgr:mgrpw
         Content-Type: application/x-www-form-urlencoded

         %s
    """ % formdata)
    assert r.getStatus() == 303


def measure(fn):
    """Measure the running time of `fn` in seconds (very crudely)."""
    t0 = time.time()
    fn()
    return time.time() - t0


def benchmark(title, fn, count=5):
    print title
    for n in range(count):
        time = measure(fn)
        print "  %.3f seconds" % time


def main():
    print "ZCML took %.3f seconds." % measure(load_ftesting_zcml)
    print "Setup took %.3f seconds." % measure(setup_benchmark)
    benchmark("ACL view render", do_benchmark_render)
    benchmark("ACL view update", do_benchmark_update)

if __name__ == '__main__':
    main()
