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

from celery.task import task, periodic_task
from celery.task import Task, PeriodicTask

import transaction
from ZODB.POSException import ConflictError
from zope.component.hooks import getSite, setSite
from zope.app.publication.zopepublication import ZopePublication

from schooltool.task.celery import open_schooltool_db


class NoDatabaseException(Exception):
    pass


class DBTaskMixin(object):

    db_connection = None
    schooltool_app = None

    def __call__(self, *args, **kwargs):
        db = open_schooltool_db(self.app)
        if db is None:
            raise NoDatabaseException()
        self.db_connection = db.open()
        root = self.db_connection.root()
        self.schooltool_app = root[ZopePublication.root_name]
        transaction.begin()
        site = getSite()
        setSite(self.schooltool_app)
        fatal_exc = None
        recoverable_exc = None
        try:
            result = self.run(*args, **kwargs)
        except Exception, fatal_exc:
            transaction.abort()

        if fatal_exc is None:
            try:
                transaction.commit()
            except ConflictError, recoverable_exc:
                pass
        self.schooltool_app = None
        setSite(site)
        self.db_connection.close()
        self.db_connection = None
        if fatal_exc is not None:
            raise fatal_exc
        if recoverable_exc is not None:
            max_retries = getattr(self, 'max_db_conflict_retries',
                                  self.app.conf.SCHOOLTOOL_RETRY_DB_CONFLICTS)
            raise self.retry(exc=recoverable_exc, retries=max_retries)
        return result


class DBTask(DBTaskMixin, Task):
    abstract = True


def db_task(*args, **kw):
    return task(*args, **dict({'base': DBTask}, **kw))


class PeriodicDBTask(DBTaskMixin, PeriodicTask):
    abstract = True


def periodic_db_task(*args, **kw):
    return task(*args, **dict({'base': PeriodicDBTask}, **kw))
