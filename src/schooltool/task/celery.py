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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import absolute_import

import sys

import celery.app.defaults
import celery.loaders.default
try:
    # Celery 2
    from celery.app.abstract import configurated as StartStopStep
    logger = None
except:
    # Celery 3
    from celery.bootsteps import StartStopStep
    from celery.utils.log import worker_logger as logger

import zope.configuration.config
import zope.configuration.xmlconfig
from zope.app.publication.zopepublication import ZopePublication
from zope.component import provideUtility
from ZODB.interfaces import IDatabase
from ZODB.ActivityMonitor import ActivityMonitor

from schooltool.app.main import SchoolToolMachinery, setLanguage
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


ACTIVE_MACHINERY = None


class ConfiguratedSchoolToolMachinery(StartStopStep,
                                      SchoolToolMachinery):

    _configured = False
    app = None
    db = None
    options = None

    def __init__(self, celery_app, **kwargs):
        self.app = celery_app
        self.logger = logger or self.app.log.get_default_logger()

    def loadOptions(self):
        options = self.Options()
        options.config_file = self.app.conf.SCHOOLTOOL_CONFIG
        if not options.config_file:
            self.logger.error('No configuration file given')
            sys.exit(1)
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
        if self.db is not None:
            return # already running
        if not self._configured:
            self.logger.info('SchoolTool: Loading configuration')
            self.options = self.loadOptions()
            self.configure(self.options)
            self._configured = True
        self.db = self.openDB(self.options)

    def stop(self):
        if self.db is not None:
            self.db.close()
            self.db = None


class SchoolToolReportMachinery(ConfiguratedSchoolToolMachinery):

    def configure(self, options):
        self.options = options
        self.configureComponents(
            options,
            site_zcml=options.config.report_server_definition)
        setLanguage(options.config.lang)
        self.configureReportlab(options.config.reportlab_fontdir)


class GlobalMachinery(object):

    def init_machinery(self):
        global ACTIVE_MACHINERY
        if ACTIVE_MACHINERY:
            ACTIVE_MACHINERY.stop()
        ACTIVE_MACHINERY = self.machinery_factory(self.app)

    @property
    def machinery(self):
        global ACTIVE_MACHINERY
        if not ACTIVE_MACHINERY:
            self.init_machinery()
        return ACTIVE_MACHINERY


class ZopeLoader(celery.loaders.default.Loader,
                 GlobalMachinery):

    machinery_factory = ConfiguratedSchoolToolMachinery

    def on_worker_init(self, *args, **kw):
        super(ZopeLoader, self).on_worker_init(*args, **kw)

    def on_worker_process_init(self, *args, **kw):
        super(ZopeLoader, self).on_worker_process_init(*args, **kw)
        self.init_machinery()
        self.machinery.start()

    def on_task_init(self, *args, **kw):
        super(ZopeLoader, self).on_task_init(*args, **kw)

    def on_process_cleanup(self, *args, **kw):
        super(ZopeLoader, self).on_process_cleanup(*args, **kw)

    def on_worker_shutdown(self):
        super(ZopeLoader, self).on_worker_shutdown()
        self.machinery.stop()


class ReportLoader(ZopeLoader):
    machinery_factory = SchoolToolReportMachinery


def open_schooltool_db():
    global ACTIVE_MACHINERY
    if ACTIVE_MACHINERY is None:
        return None
    ACTIVE_MACHINERY.start()
    return ACTIVE_MACHINERY.db


def close_schooltool_db():
    global ACTIVE_MACHINERY
    if ACTIVE_MACHINERY is None:
        return
    ACTIVE_MACHINERY.stop()
