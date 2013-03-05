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

import sys
import datetime
import pkg_resources
import pytz

import celery.task
import celery.result
import celery.utils
import celery.states
import transaction
import transaction.interfaces
from celery.task import task, periodic_task
from persistent import Persistent
from zope.interface import implements, implementer
from zope.intid.interfaces import IIntIds
from zope.catalog.text import TextIndex
from zope.component import adapter, getUtility, getAdapters
from zope.container.btree import BTreeContainer
from zope.container.contained import Contained
from zope.interface import implements
from ZODB.POSException import ConflictError
from zope.app.publication.zopepublication import ZopePublication
from zope.component.hooks import getSite, setSite
from zope.container.interfaces import INameChooser
from zc.catalog.catalogindex import SetIndex

from schooltool.app.app import StartUpBase
from schooltool.app.catalog import AttributeCatalog
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPerson
from schooltool.task.celery import open_schooltool_db
from schooltool.task.interfaces import IRemoteTask, ITaskContainer
from schooltool.task.interfaces import IMessage, IMessageContainer
from schooltool.task.interfaces import ITaskCompletedMessage
from schooltool.task.interfaces import ITaskFailedMessage


IN_PROGRESS = 'IN_PROGRESS'
COMMITTING = 'COMMITTING_ZODB'


class NoDatabaseException(Exception):
    """SchoolTool database is not available."""


class TPCNotReady(Exception):
    """
    Task is either being committed or was aborted on SchoolTool side.
    """


TPC_RETRY_SECONDS = (1, 10, 1*60, 5*60, 20*60)


class DBTaskMixin(object):

    max_tpc_retries = len(TPC_RETRY_SECONDS)

    db_connection = None
    schooltool_app = None
    track_started = True

    @property
    def remote_task(self):
        app = self.schooltool_app
        if app is None:
            raise AttributeError(
                'remote_task: SchoolTool app only available within ZODB transaction')
        tasks = ITaskContainer(app)
        return tasks.get(self.request.id)

    def beginTransaction(self):
        db = open_schooltool_db()
        if db is None:
            raise NoDatabaseException()
        self.db_connection = db.open()
        root = self.db_connection.root()
        self.schooltool_app = root[ZopePublication.root_name]
        transaction.begin()
        if self.remote_task is None:
            raise TPCNotReady()

    def abortTransaction(self):
        transaction.abort()

    def commitTransaction(self):
        transaction.commit()

    def closeTransaction(self):
        try:
            self.schooltool_app = None
            if self.db_connection is not None:
                self.db_connection.close()
                self.db_connection = None
        finally:
            setSite(None)

    @property
    def max_db_retries(self):
        max_db_retries = getattr(self.app.conf, 'SCHOOLTOOL_RETRY_DB_CONFLICTS', 3)
        max_db_retries = getattr(self, 'max_db_conflict_retries', max_db_retries)
        return max_db_retries

    def runTransaction(self, attr, set_committing, *args, **kw):
        self.beginTransaction()
        max_db_retries = self.max_db_retries
        result = None
        conflict_exception = None
        for n_try in range(min(1, max_db_retries+1)):
            try:
                old_site = getSite()
                setSite(self.schooltool_app)
                callable = getattr(self.remote_task, attr)
                result = callable(*args, **kw)
                setSite(old_site)
                if set_committing:
                    try:
                        status = TaskWriteStatus(self.request.id)
                        status.set_committing()
                    except Exception:
                        pass # don't care really
            except ConflictError, conflict_exception:
                # Transaction conflict, let's repeat
                pass
            except Exception, other:
                self.abortTransaction()
                raise other
        if conflict_exception is not None:
            self.abortTransaction()
            raise conflict_exception
        self.commitTransaction()
        return result

    def __call__(self, *args, **kwargs):
        result = None
        try:
            result = self.runTransaction('execute', True, self, *args, **kwargs)
            self.runTransaction('complete', False, self, result)
        except (NoDatabaseException, TPCNotReady), exc:
            n_retry = getattr(self.request, 'retries', 0)
            countdown = TPC_RETRY_SECONDS[min(n_retry, len(TPC_RETRY_SECONDS)-1)]
            raise self.retry(exc=exc, countdown=countdown,
                             max_retries=self.max_tpc_retries)
        except Exception, exception:
            try:
                self.runTransaction('fail', False, self, result, exception)
            except Exception:
                pass
            raise exception
        finally:
            self.closeTransaction()
        return result


class DBTask(DBTaskMixin, celery.task.Task):
    pass


def db_task(*args, **kw):
    return celery.task.task(*args, **dict({'base': DBTask}, **kw))


class PeriodicDBTask(DBTaskMixin, celery.task.PeriodicTask):
    abstract = True


def periodic_db_task(*args, **kw):
    return celery.task.task(*args, **dict({'base': PeriodicDBTask}, **kw))


class TaskTransactionManager(object):
    implements(transaction.interfaces.IDataManager)

    tpc_result = None
    task = None
    options = None

    tracker = None

    def __init__(self, tracker, task, args, kwargs, **options):
        self.task = celery.task.subtask(task, args=args, kwargs=kwargs)
        self.options = options
        self.tracker = tracker

    @property
    def transaction_manager(self):
        return transaction.manager

    def abort(self, transaction):
        self.task = None
        self.optons = None
        self.tracker = None
        if self.tpc_result is not None:
            self.tpc_result.revoke()

    # TPC protocol: tpc_begin commit tpc_vote (tpc_finish | tpc_abort)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # Actual commit should happen in tpc_finish.  Now, if other manager(s)
        # fail the vote, it's up to the task to figure out it's aborted.
        self.tpc_result = self.task.apply_async(
            task_id=self.tracker.task_id, **self.options)

    def tpc_finish(self, transaction):
        pass

    def tpc_abort(self, transaction):
        try:
            self.tpc_result.revoke()
        except Exception, e:
            print >> sys.stderr, 'Failed to revoke task %s with exception %r' % (
                self.tpc_result, e)

    def sortKey(self):
        return '~schooltool:%s:%s' % (
            self.__class__.__name__, id(self))


class RemoteTask(Persistent, Contained):
    implements(IRemoteTask)

    task_id = None
    celery_task = DBTask
    scheduled = None
    creator_username = None
    routing_key = None

    _traceback = None
    _result = None

    def __init__(self):
        Persistent.__init__(self)
        Contained.__init__(self)
        self.task_id = celery.utils.uuid()

    def update(self, request):
        self.creator = IPerson(getattr(request, 'principal', None), None)

    def getRoutingOptions(self, task, **options):
        routing = {
            'routing_key': options.get('routing_key',
                                       getattr(self, 'routing_key',
                                               None)),
            }
        return routing

    def schedule(self, request, celery_task=None, args=(), kwargs=None, **options):
        if request is not None:
            self.update(request)

        if celery_task is None:
            celery_task = self.celery_task
        else:
            self.celery_task = celery_task
        assert celery_task is not None
        assert self.task_id is not None
        if kwargs is None:
            kwargs = {}
        current_transaction = transaction.get()

        if (options.get('eta') is None and
            options.get('countdown') is None):
            options['countdown'] = 1

        options.update(self.getRoutingOptions(celery_task, **options))

        resource = TaskTransactionManager(
                self, task=celery_task, args=args, kwargs=kwargs, **options
                )
        current_transaction.join(resource)
        app = ISchoolToolApplication(None)
        tasks = ITaskContainer(app)
        self.scheduled = self.utcnow
        tasks[self.task_id] = self
        return self

    def execute(self, request):
        pass

    def complete(self, request, result):
        app = ISchoolToolApplication(None)
        tasks = ITaskContainer(app)
        self.notifyComplete(request, result)
        if self.task_id in tasks:
            del tasks[self.task_id]

    def fail(self, request, result, traceback):
        self.result = result
        self.traceback = str(traceback) or 'N/A'

    def notifyComplete(self, request, result):
        subscribers = getAdapters((self, request, result), ITaskCompletedMessage)
        for name, subscriber in subscribers:
            try:
                subscriber()
            except Exception, exception:
                self.notifyFailed(self, request, result, exception)

    def notifyFailed(self, request, result, traceback):
        subscribers = getAdapters((self, request, result, traceback), ITaskFailedMessage)
        for name, subscriber in subscribers:
            try:
                subscriber()
            except:
                pass # not much more we can do

    @property
    def async_result(self):
        return celery.task.Task.AsyncResult(self.task_id)

    @property
    def internal_state(self):
        return self.async_result.state

    @property
    def working(self):
        # Note: only works if celery task has track_started set
        return self.async_result.state == celery.states.STARTED

    @property
    def finished(self):
        if (self._result is not None or
            self._traceback is not None):
            return True
        # Note: non-existing tasks will be permanently pending on
        #       at least some celery backends
        return self.async_result.ready()

    @property
    def succeeded(self):
        if (self._result is not None and
            self._traceback is None):
            return True
        return self.async_result.successful()

    @property
    def failed(self):
        if self._traceback is not None:
            return True
        return self.async_result.failed()

    @property
    def result(self):
        if self._result is not None:
            return self._result
        return self.async_result.result

    @property
    def traceback(self):
        return self.async_result.traceback

    @property
    def utcnow(self):
        return pytz.UTC.localize(datetime.datetime.utcnow())

    @property
    def creator(self):
        if self.creator_username is None:
            return None
        app = ISchoolToolApplication(None)
        person = app['persons'].get(self.creator_username)
        return person

    @creator.setter
    def creator(self, person):
        if person is None:
            self.creator_username = None
        else:
            self.creator_username = person.__name__

    @property
    def signature(self):
        return '%s:%s' % (self.__class__.__module__, self.__class__.__name__)


class TaskContainer(BTreeContainer):
    implements(ITaskContainer)


@adapter(ISchoolToolApplication)
@implementer(ITaskContainer)
def getTaskContainerForApp(app):
    return app['schooltool.tasks']


class TasksStartUp(StartUpBase):

    def __call__(self):
        if 'schooltool.tasks' not in self.app:
            self.app['schooltool.tasks'] = TaskContainer()


class TaskReadStatus(object):

    task_id = None
    _meta = None
    _progress_states = (celery.states.STARTED, IN_PROGRESS)

    def __init__(self, task_id):
        self.task_id = task_id
        self._meta = None, None, None
        self.reload()

    def reload(self):
        result = celery.task.Task.AsyncResult(self.task_id)
        self._meta = result.state, result.result, result.traceback

    @property
    def state(self):
        return self._meta[0]

    @property
    def in_progress(self):
        return (self.state in self._progress_states or self.committing)

    @property
    def committing(self):
        return self.state == COMMITTING

    @property
    def pending(self):
        return self.state in celery.states.UNREADY_STATES

    @property
    def finished(self):
        return self.state in celery.states.READY_STATES

    @property
    def failed(self):
        return self.state in celery.states.PROPAGATE_STATES

    @property
    def succeeded(self):
        return self.state == celery.states.SUCCESS

    @property
    def progress(self):
        if self.in_progress:
            return self._meta[1]

    @property
    def result(self):
        if self.succeeded:
            return self._meta[1]

    @property
    def failure(self):
        if self.failed:
            return self._meta[1]

    @property
    def info(self):
        return self._meta[1]

    @property
    def traceback(self):
        return self._meta[2]


class NotInProgress(Exception):
    pass


undefined = object()

class TaskWriteStatus(TaskReadStatus):

    def set_progress(self, progress=None):
        result = celery.task.Task.AsyncResult(self.task_id)
        # XXX: only check this if task.track_started
        if result.state not in self._progress_states:
            raise NotInProgress(result.state, self._progress_states)
        result.backend.store_result(result.task_id, progress, IN_PROGRESS)
        self.reload()

    def set_committing(self):
        result = celery.task.Task.AsyncResult(self.task_id)
        # XXX: only check this if task.track_started
        if result.state not in self._progress_states:
            raise NotInProgress(result.state, self._progress_states)
        result.backend.store_result(result.task_id, self.info, COMMITTING)
        self.reload()


class RemoteTaskCatalog(AttributeCatalog):
    version = '1 - initial'
    interface = IRemoteTask
    attributes = ('task_id', 'internal_state', 'scheduled', 'creator_username')

    def setIndexes(self, catalog):
        super(RemoteTaskCatalog, self).setIndexes(catalog)
        catalog['signature'] = TextIndex('signature')


getRemoteTaskCatalog = RemoteTaskCatalog.get


class MessageContainer(BTreeContainer):
    implements(IMessageContainer)


@adapter(ISchoolToolApplication)
@implementer(IMessageContainer)
def getMessageContainerForApp(app):
    return app['schooltool.task.messages']


class MessagesStartUp(StartUpBase):

    def __call__(self):
        if 'schooltool.task.messages' not in self.app:
            self.app['schooltool.task.messages'] = MessageContainer()


class Message(Persistent, Contained):
    implements(IMessage)

    expires_on = None
    sender_id = None
    recipient_ids = None
    title = u''
    group = u''

    def __init__(self, title, sender=None, recipients=None):
        self.title = title
        if recipients is not None:
            self.recipients = recipients

    def send(self, *args):
        app = ISchoolToolApplication(None)
        messages = IMessageContainer(app)
        name_chooser = INameChooser(messages)
        name = name_chooser.chooseName('', self)
        messages[name] = self

    @property
    def sender(self):
        if self.sender_id is None:
            return None
        int_ids = getUtility(IIntIds)
        return int_ids.queryObject(self.sender_id)

    @sender.setter
    def sender(self, value):
        if value is None:
            self.sender = None
        else:
            int_ids = getUtility(IIntIds)
            self.sender = int_ids.queryId(value)

    @property
    def recipients(self):
        if self.recipient_ids is None:
            return None
        int_ids = getUtility(IIntIds)
        result = set([int_ids.queryObject(iid) for iid in self.recipient_ids])
        if None in result:
            result.remove(None)
        return result

    @recipients.setter
    def recipients(self, value):
        if value is None:
            self.recipient_ids = None
        else:
            int_ids = getUtility(IIntIds)
            ids = set([int_ids.queryId(obj) for obj in value])
            if None in ids:
                ids.remove(None)
            self.recipient_ids = ids


class TaskCompletedMessage(Message):

    def __init__(self, remote_task, request, result):
        Message.__init__(self.title)
        self(remote_task, request, result)

    def update(self, remote_task, request, result):
        pass

    def __call__(self, remote_task, request, result):
        self.update(remote_task, request, result)
        self.send()


class TaskFailedMessage(Message):

    def __init__(self, remote_task, request, result, traceback):
        Message.__init__(self.title)
        self(remote_task, request, result, traceback)

    def update(self, remote_task, request, result, traceback):
        pass

    def __call__(self, remote_task, request, result, traceback):
        self.update(remote_task, request, result, traceback)
        self.send()


class MessageCatalog(AttributeCatalog):
    version = '1 - initial'
    interface = IMessage
    attributes = ('sender_id', 'title', 'group')

    def setIndexes(self, catalog):
        super(MessageCatalog, self).setIndexes(catalog)
        catalog['recipient_ids'] = SetIndex('recipients')


getMessageCatalog = MessageCatalog.get


def load_plugin_tasks():
    task_entries = list(pkg_resources.iter_entry_points('schooltool.tasks'))
    for entry in task_entries:
        entry.load()

load_plugin_tasks()
