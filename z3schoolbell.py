#!/usr/bin/env python2.3
"""
Start the new Zope-3 based SchoolBell.
"""

import sys
import os
import time
import logging
from cStringIO import StringIO


def main(argv=sys.argv):
    # Set up PYTHONPATH
    here = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.join(here, 'Zope3', 'src'))
    sys.path.insert(0, os.path.join(here, 'src'))

    # Start the Zope 3 server
    from zope.app.server.main import run

    # Record start times (real time and CPU time)
    t0 = time.time()
    c0 = time.clock()

    setup()

    t1 = time.time()
    c1 = time.clock()
    print "Startup time: %.3f sec real, %.3f sec CPU" % (t1-t0, c1-c0)

    run()


def setup():
    from zope.event import notify
    from ZODB.FileStorage import FileStorage
    from ZODB.DB import DB
    from zope.server.taskthreads import ThreadedTaskDispatcher
    import zope.app.appsetup

    print "Parsing ZCML"
    config()

    print "Opening schoolbell-data.fs"
    db = zope.app.appsetup.database('schoolbell-data.fs') # XXX hardcoded

    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(4)  # XXX hardcoded

    from zope.app.server.http import http
    print "Starting HTTP server on *:8080"
    http.create('HTTP', task_dispatcher, db, 8080) # XXX hardcoded

    notify(zope.app.appsetup.ProcessStarting())

    return db


def config():
    """Configure site globals."""
    import zope.app.component.hooks
    from zope.configuration import xmlconfig

    # Hook up custom component architecture calls
    zope.app.component.hooks.setHooks()
    context = xmlconfig.string(SITE_DEFINITION)


SITE_DEFINITION = """
<configure xmlns="http://namespaces.zope.org/zope">

  <include package="zope.app" />
  <include package="zope.app.securitypolicy" file="meta.zcml" />

  <include package="zope.app.authentication" />
<!--  <include package="zope.app.presentation" />  need fssync -->
  <include package="zope.app.session" />
  <include package="zope.app.server" />

  <include package="schoolbell.app" />

  <include package="zope.app.securitypolicy" />

  <unauthenticatedPrincipal id="zope.anybody" title="Unauthenticated User" />
  <unauthenticatedGroup id="zope.Anybody" title="Unauthenticated Users" />
  <authenticatedGroup id="zope.Authenticated" title="Authenticated Users" />
  <everybodyGroup id="zope.Everybody" title="All Users" />

  <principal id="zope.sample_manager" title="Sample Manager"
             login="gandalf" password="123" />
  <grant role="zope.Manager" principal="zope.sample_manager" />

</configure>
"""


if __name__ == '__main__':
    main()
