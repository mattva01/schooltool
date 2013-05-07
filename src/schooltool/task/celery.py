#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
from __future__ import absolute_import

import celery.app.abstract
import celery.app.defaults
import celery.loaders.default

from zope.app.publication.zopepublication import ZopePublication
from zope.component import provideUtility
from ZODB.interfaces import IDatabase
from ZODB.ActivityMonitor import ActivityMonitor

from schooltool.app.main import SchoolToolMachinery
from schooltool.app.interfaces import ISchoolToolApplication


SCHOOLTOOL_CONFIG_NAMESPACES = {
    "SCHOOLTOOL": {
        "CONFIG": celery.app.defaults.Option('schooltool.conf', type="string"),
        "RETRY_DB_CONFLICTS": celery.app.defaults.Option(3, type="int"),
        }
    }
celery.app.defaults.NAMESPACES.update(SCHOOLTOOL_CONFIG_NAMESPACES)
celery.app.defaults.DEFAULTS.update(
    dict((key, value.default)
         for key, value in celery.app.defaults.flatten(SCHOOLTOOL_CONFIG_NAMESPACES)))


SCHOOLTOOL_MACHINERY = None


class ZopeLoader(celery.loaders.default.Loader):

    def on_worker_init(self, *args, **kw):
        super(ZopeLoader, self).on_worker_init(*args, **kw)

    def on_worker_process_init(self,*args, **kw):
        super(ZopeLoader, self).on_worker_process_init(*args, **kw)
        open_schooltool_db(self.app)

    def on_task_init(self, *args, **kw):
        super(ZopeLoader, self).on_task_init(*args, **kw)
        #db = open_schooltool_db(self.app)

    def on_process_cleanup(self,*args, **kw):
        super(ZopeLoader, self).on_process_cleanup(*args, **kw)
        #close_schooltool_db(self.app)


class ConfiguratedSchoolToolMachinery(celery.app.abstract.configurated,
                                      SchoolToolMachinery):

    config = celery.app.abstract.from_config()
    celery_app = None
    db = None
    options = None

    def __init__(self, celery_app, **kwargs):
        self.app = celery_app
        self.setup_defaults(kwargs, namespace='schooltool')

    def loadOptions(self):
        options = self.Options()
        if self.config:
            options.config_file = self.config
        options.config, handler = self.readConfig(options.config_file)
        if options.config.database.config.storage is None:
            raise Exception('No ZODB storage configured')
        return options

    def openDB(self, options):
        if self.db is not None:
            return self.db
        db_configuration = options.config.database
        db = db_configuration.open()
        connection = db.open()
        root = connection.root()
        app = root.get(ZopePublication.root_name)
        if app is None or not ISchoolToolApplication.providedBy(app):
            connection.close()
            return None
        connection.close()
        provideUtility(db, IDatabase)
        db.setActivityMonitor(ActivityMonitor())
        self.db = db
        return self.db

    def start(self):
        # XXX: this goes to WARNING, should go to INFO
        print 'Configuring SchoolTool machinery.'
        self.options = self.loadOptions()
        self.configure(self.options)
        self.db = self.openDB(self.options)

    def stop(self):
        if self.db is not None:
            self.db.close()
            self.db = None


def open_schooltool_db(celery_app=None):
    global SCHOOLTOOL_MACHINERY
    if SCHOOLTOOL_MACHINERY is None:
        if celery_app is None:
            return None
        SCHOOLTOOL_MACHINERY = ConfiguratedSchoolToolMachinery(celery_app)
        SCHOOLTOOL_MACHINERY.start()
    db = SCHOOLTOOL_MACHINERY.openDB(SCHOOLTOOL_MACHINERY.options)
    return db


def close_schooltool_db(celery_app):
    global SCHOOLTOOL_MACHINERY
    if SCHOOLTOOL_MACHINERY is None:
        return
    SCHOOLTOOL_MACHINERY.stop()


#class SchoolToolWorkerComponent(celery.abstract.StartStopComponent):
#    name = "worker.schooltool"
#
#    def create(self, parent):
#        return StratableStoppableSchooltoolWorkControllerComponent(parent)


