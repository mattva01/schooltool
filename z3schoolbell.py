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

    logging.basicConfig()

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

    # Evil hack
    from zope.app.tests import ztapi
    from zope.app.appsetup.appsetup import IDatabaseOpenedEvent
    ztapi.handle([IDatabaseOpenedEvent], bootstrapSubscriber)

    # Another evil hack
    import transaction
    from schoolbell.app.interfaces import ISchoolBellApplication
    from zope.app.publisher.browser import BrowserView
    from zope.publisher.interfaces.browser import IBrowserPublisher
    from zope.publisher.interfaces import NotFound
    from zope.interface import implements
    class ResetDbView(BrowserView):
        implements(IBrowserPublisher)
        def browserDefault(self, request):
            return self, ()
        def publishTraverse(self, request, name):
            raise NotFound(self, name, request)
        def __call__(self):
            db = self.request.publication.db
            transaction.commit()
            conn = db.open()
            installAppInRoot(db, conn.root())
            transaction.commit()
            conn.close()
            return 'OK'
    from zope.security.checker import Checker
    from zope.security.checker import defineChecker
    defineChecker(ResetDbView, Checker(dict([(n, 'zope.ManageContent')
                    for n in ('browserDefault', '__call__', 'publishTraverse')])))
    ztapi.browserView(ISchoolBellApplication, 'resetdb.html', ResetDbView)


def bootstrapSubscriber(event):
    """Set up a SchoolBell application as the database root.

    This is an evil hack that rips out the Zope 3 RootFolder and replaces it
    with a SchoolBellApplication.
    """
    import transaction
    from zope.app.appsetup.bootstrap import getInformationFromEvent
    from schoolbell.app.interfaces import ISchoolBellApplication
    db, connection, root, root_folder = getInformationFromEvent(event)
    if not ISchoolBellApplication.providedBy(root_folder):
        if root_folder is None:
            print "Installing SchoolBellApplication as the root object"
        else:
            print "Root folder already exists.  Replacing it with a SchoolBellApplication."
        installAppInRoot(db, root)
        transaction.commit()
        connection.close()

def installAppInRoot(db, root):
    from schoolbell.app.app import SchoolBellApplication
    from zope.app.traversing.interfaces import IContainmentRoot
    from zope.interface import directlyProvides
    from zope.app.publication.zopepublication import ZopePublication
    from zope.app.appsetup.bootstrap import getServiceManager
    from zope.app.appsetup.bootstrap import ensureService
    from zope.app.servicenames import Utilities
    from zope.app.utility import LocalUtilityService

    app = SchoolBellApplication()
    directlyProvides(app, IContainmentRoot)
    root[ZopePublication.root_name] = app

    service_manager = getServiceManager(app)
    ensureService(service_manager, app, Utilities, LocalUtilityService)

    # Evil hack, continued:
    #    1. We open the db, DatabaseOpened event gets published
    #    2. zope.app.appsetup.bootstrap.bootStrapSubscriber adds a RootFolder
    #    3. various other subscribers register various local utilities
    #    4. our very own bootstrapSubscriber rips out the RootFolder and replaces
    #       it with a SchoolBellApplication
    # step (4) undoes the changes made in steps (2) and (3), but we need changes
    # made in step (3)!  So, publish the event again.  (2) and (4) will not do
    # anything this time because the root application object exists.
    from zope.event import notify
    from zope.app.appsetup.appsetup import DatabaseOpened
    notify(DatabaseOpened(db))


SITE_DEFINITION = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:browser="http://namespaces.zope.org/browser">

  <include package="zope.app" />
  <include package="zope.app.securitypolicy" file="meta.zcml" />

  <!-- XXX strange: testz3sb.py passes without zope.app.authentication.  Why? -->
<!--  <include package="zope.app.authentication" /> -->
  <include package="zope.app.session" />
  <include package="zope.app.server" />

  <!-- Workaround to shut down a DeprecationWarning that gets because we do not
       include zope.app.onlinehelp and the rotterdam skin tries to look for
       this menu -->
  <browser:menu id="help_actions" />

  <include package="schoolbell.app" />

  <include package="zope.app.securitypolicy" />

  <unauthenticatedPrincipal id="zope.anybody" title="Unauthenticated User" />
  <unauthenticatedGroup id="zope.Anybody" title="Unauthenticated Users" />
  <authenticatedGroup id="zope.Authenticated" title="Authenticated Users" />
  <everybodyGroup id="zope.Everybody" title="All Users" />

  <principal id="zope.sample_manager" title="Sample Manager"
             login="gandalf" password="123" />
  <grant role="zope.Manager" principal="zope.sample_manager" />

  <principal id="zope.testmgr" title="test Manager"
             login="mgr" password="mgrpw" />
  <grant role="zope.Manager" principal="zope.testmgr" />

</configure>
"""


if __name__ == '__main__':
    main()
