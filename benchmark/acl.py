#!/usr/bin/python
"""
Benchmark the ACL view.
"""

import random
import urllib

from benchmark import *

import transaction
from schooltool.person.person import Person
from schooltool.group.group import Group


def setup_benchmark():
    """Create an SB application and populate with users and groups."""
    setup = load_ftesting_zcml()
    r = http(r"""
         POST /@@contents.html HTTP/1.1
         Authorization: Basic mgr:mgrpw
         Content-Type: application/x-www-form-urlencoded

         type_name=BrowserAdd__schooltool.app.app.SchoolToolApplication&new_value=frogpond
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


def main():
    print "ZCML took %.3f seconds." % measure(load_ftesting_zcml)
    print "Setup took %.3f seconds." % measure(setup_benchmark)
    benchmark("ACL view render", do_benchmark_render)
    benchmark("ACL view update", do_benchmark_update)


if __name__ == '__main__':
    main()
